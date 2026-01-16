from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

# 自作モジュールのインポート（パスは環境に合わせて調整してください）
import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user
from app.name.tadokoro.notific import create_notification

# ★ これが足りなかったためにエラーになっていました
router = APIRouter(prefix="/api/driver", tags=["completion"])

# --- スキーマ定義 (ProgressResponseなどが使われている場合) ---
class DriverInfo(BaseModel):
    name: str
    rating: float
    driveCount: int

class ProgressDriveItem(BaseModel):
    id: str
    from_loc: str
    to_loc: str
    datetime: str
    price: int
    driver: DriverInfo

class ProgressResponse(BaseModel):
    drives: List[ProgressDriveItem]

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()


@router.get("/completion", response_model=ProgressResponse)
async def get_completion_drives(request: Request, db: Session = Depends(get_db)):
    # 1. 認証
    session_id = request.cookies.get("session_id")
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401)
    my_id = int(res)

    final_list = []

    # --- パターンA: 自分が「運転者募集(Type:0)」のホストだった場合 ---
    # 相手は「申請してきた同乗者(Applicant)」
    driver_host = db.query(
        modelDB.Recruitment, modelDB.Route, modelDB.User, modelDB.PassengerProfile
    ).join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
     .join(modelDB.Application, modelDB.Recruitment.recruitment_id == modelDB.Application.recruitment_id)\
     .join(modelDB.User, modelDB.Application.applicant_user_id == modelDB.User.user_id)\
     .join(modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id)\
     .filter(
         modelDB.Recruitment.recruiter_user_id == my_id,
         modelDB.Recruitment.status == 2,      # 完了済み
         modelDB.Application.status >= 1       # 承認(1)または完了(2)
     ).all()

    for rec, route, user, prof in driver_host:
        final_list.append(ProgressDriveItem(
            id=str(rec.recruitment_id),
            from_loc=route.depname,
            to_loc=route.arrname,
            datetime=route.dep_time.strftime('%Y-%m-%d %H:%M'),
            price=rec.fare,
            driver=DriverInfo(
                name=user.name, # 相手(同乗者)の名前
                rating=float(prof.rating),
                driveCount=prof.ride_count
            )
        ))

    # --- パターンB: 自分が「同乗者募集(Type:1)」に対しドライバーとして応募した場合 ---
    # 相手は「募集を出した同乗者(Recruiter)」
    driver_guest = db.query(
        modelDB.Recruitment, modelDB.Route, modelDB.User, modelDB.PassengerProfile
    ).join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
     .join(modelDB.Application, modelDB.Recruitment.recruitment_id == modelDB.Application.recruitment_id)\
     .join(modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id)\
     .join(modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id)\
     .filter(
         modelDB.Application.applicant_user_id == my_id, # 自分が応募側
         modelDB.Recruitment.status == 2,
         modelDB.Application.status >= 1
     ).all()

    for rec, route, user, prof in driver_guest:
        final_list.append(ProgressDriveItem(
            id=str(rec.recruitment_id),
            from_loc=route.depname,
            to_loc=route.arrname,
            datetime=route.dep_time.strftime('%Y-%m-%d %H:%M'),
            price=rec.fare,
            driver=DriverInfo(
                name=user.name, # 相手(同乗者)の名前
                rating=float(prof.rating),
                driveCount=prof.ride_count
            )
        ))

    return ProgressResponse(drives=final_list)


# --- ドライブ完了実行エンドポイント ---
from fastapi import Request # 追加が必要

# --- スキーマ定義 ---
# (既存の DriverInfo, ProgressDriveItem, ProgressResponse はそのまま)

class CompleteRequest(BaseModel):
    driveId: int  # または str。DBの recruitment_id の型に合わせてください

class CompleteResponse(BaseModel):
    ok: bool
    message: str

@router.post("/complete", response_model=CompleteResponse)
async def complete_drive(
    req: CompleteRequest,
    request: Request,  # セッション取得のために追加
    db: Session = Depends(get_db)
):
    """
    ドライブを完了状態(status=2)に更新
    """
    # 1. セッションから実行ユーザーのIDを取得
    session_id = request.cookies.get("session_id")
    user_id_str = get_current_user(session_id=session_id, db=db)
    
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です。再ログインしてください。")
    
    my_id = int(user_id_str)

    # 2. 対象の募集を取得
    # 条件：指定されたIDであること ＋ 自分がその募集の作成者(運転者)であること
    recruitment = (
        db.query(modelDB.Recruitment)
        .filter(
            modelDB.Recruitment.recruitment_id == req.driveId,
            modelDB.Recruitment.recruiter_user_id == my_id
        )
        .first()
    )

    if not recruitment:
        # 他人の募集を操作しようとした場合や存在しない場合は404
        raise HTTPException(status_code=404, detail="対象のドライブが見つからないか、権限がありません。")

    # 3. すでに完了している場合の二重処理防止
    if recruitment.status == 2:
        return CompleteResponse(
            ok=True,
            message="このドライブは既に完了しています。"
        )

    try:
        # 4. ステータスを「運転完了(2)」に更新
        recruitment.status = 2
        
        # 関連する申請(Application)を取得して、相手に通知を送る
        application = db.query(modelDB.Application).filter(
            modelDB.Application.recruitment_id == req.driveId,
            modelDB.Application.status == 1  # 承認済み
        ).first()
        
        if application:
            # 相手（同乗者）に通知を送る
            create_notification(
                db=db,
                user_id=application.applicant_user_id,
                message="ドライブが完了しました。レビューの投稿をお願いします。"
            )

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Update Error: {e}")
        raise HTTPException(status_code=500, detail="データベースの更新に失敗しました。")

    return CompleteResponse(
        ok=True,
        message="ドライブを完了しました。お疲れ様でした！"
    )