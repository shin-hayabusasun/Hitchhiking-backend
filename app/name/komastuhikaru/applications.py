from fastapi import APIRouter, Depends, HTTPException, Response, Request, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sys

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user
from app.name.tadokoro.notific import create_notification

# ルーター定義
router = APIRouter(prefix="/api/applications", tags=["applications"])

# ---------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------
class ActionResponse(BaseModel):
    message: str

# ---------------------------------------------------------
# Dependency
# ---------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# 承認 API
# ---------------------------------------------------------
@router.post("/{id}/approve", response_model=ActionResponse)
async def approve_application(request: Request, id: int = Path(..., title="Application ID"), db: Session = Depends(get_db)):
    """
    申請承認
    1. 申請ステータスを承認(1)に変更
    2. チャットルームを作成し、Applicationと紐付ける
    3. 募集ステータスをマッチ済み(1)に変更
    """
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no": raise HTTPException(status_code=401, detail="Invalid session")
    
    current_user_id = int(res)

    # 1. 対象の申請を検索 (自分が募集主であるか確認)
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Application.application_id == id,
        modelDB.Recruitment.recruiter_user_id == current_user_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized")

    # 二重承認防止
    if application.status != 0:
        raise HTTPException(status_code=400, detail="This application has already been processed")

    try:
        # 2. 申請ステータスを承認(1)に変更
        application.status = 1 
        
        # チャットルームの作成
        # 既存のチャットがあるかチェック
        existing_chat = db.query(modelDB.Chat).filter(
            modelDB.Chat.application_id == application.application_id
        ).first()
        
        if not existing_chat:
            new_chat = modelDB.Chat(
                user_id=current_user_id,
                message="マッチングが成立しました！チャットを開始してください。",
                application_id=application.application_id
            )
            db.add(new_chat)

        # 3. 募集自体のステータスも「マッチ済み」にする
        recruitment = db.query(modelDB.Recruitment).filter(
            modelDB.Recruitment.recruitment_id == application.recruitment_id
        ).first()
        
        if recruitment:
            recruitment.status = 1  # 0:募集中 -> 1:マッチ済み

        db.commit()
        
        # 申請者に承認通知を送る
        create_notification(
            db=db,
            user_id=application.applicant_user_id,
            message="あなたの申請が承認されました！マッチングが成立しました。"
        )
        
        return ActionResponse(message="承認しました")

    except Exception as e:
        db.rollback()
        print(f"Error approving application: {e}")
        raise HTTPException(status_code=500, detail="承認処理に失敗しました")

# ---------------------------------------------------------
# 拒否 API
# ---------------------------------------------------------
@router.post("/{id}/reject", response_model=ActionResponse)
async def reject_application(request: Request, id: int = Path(..., title="Application ID"), db: Session = Depends(get_db)):
    """
    申請拒否
    """
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no": raise HTTPException(status_code=401, detail="Invalid session")
    
    current_user_id = int(res)

    # 対象の申請を検索
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Application.application_id == id,
        modelDB.Recruitment.recruiter_user_id == current_user_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized")

    # 既に処理済みかチェック
    if application.status != 0:
        raise HTTPException(status_code=400, detail="This application has already been processed")

    application.status = 2  # 拒否
    db.commit()
    
    # 申請者に拒否通知を送る
    create_notification(
        db=db,
        user_id=application.applicant_user_id,
        message="申請が拒否されました。他の募集をご検討ください。"
    )
    
    return ActionResponse(message="拒否しました")