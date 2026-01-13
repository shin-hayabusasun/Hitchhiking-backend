from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/driver", tags=["schedules"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.delete("/schedules/{recruitment_id}")
async def delete_all_related_schedule(
    recruitment_id: int, 
    request: Request, 
    db: Session = Depends(get_db)
):
    # 1. ユーザー認証
    session_id = request.cookies.get("session_id")
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Unauthorized")
    my_id = int(user_id_str)

    # 2. 募集が存在するか、自分が所有者かを確認
    # 同時に route_id を取得しておく
    recruitment = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == recruitment_id,
        modelDB.Recruitment.recruiter_user_id == my_id
    ).first()

    if not recruitment:
        raise HTTPException(status_code=404, detail="募集が見つからないか権限がありません")

    target_route_id = recruitment.route_id

    try:
        # 3. 削除実行（外部キーの依存関係に従って順番に消す）
        
        # ① 取引テーブル (Applications) の削除
        db.query(modelDB.Application).filter(
            modelDB.Application.recruitment_id == recruitment_id
        ).delete()

        # ② 募集テーブル (Recruitments) の削除
        db.delete(recruitment)
        db.flush() # IDの依存関係を一時的に解消

        # ③ 経路テーブル (Routes) の削除
        db.query(modelDB.Route).filter(
            modelDB.Route.route_id == target_route_id
        ).delete()

        # すべて成功したら確定
        db.commit()
        return {"ok": True, "message": "関連するすべてのデータを削除しました"}

    except Exception as e:
        db.rollback() # どこかで失敗したらすべて元に戻す
        print(f"削除エラー詳細: {str(e)}")
        raise HTTPException(status_code=500, detail="サーバーエラーにより削除に失敗しました")