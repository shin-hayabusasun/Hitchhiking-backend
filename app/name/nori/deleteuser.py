from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sys

# パス設定（環境に合わせて調整してください）
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

# ルーターの設定 (フロントの fetch パスに合わせて /api/admin に設定)
router = APIRouter(prefix="/api/admin", tags=["admin"])

# DBセッション
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# レスポンスモデル
class DeleteResponse(BaseModel):
    ok: bool

# --- 削除APIの実装 ---

@router.delete("/customers/{id}", response_model=DeleteResponse)
async def delete_customer(id: int, request: Request, db: Session = Depends(get_db)):
    # 1. セッション・権限確認 (既存通り)
    session_id = request.cookies.get("session_id")
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="権限がありません")

    # 2. ユーザーの存在確認
    user_to_delete = db.query(modelDB.User).filter(modelDB.User.user_id == id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    try:
        # 3. 【重要】子テーブルを依存関係の深い順に削除
        # まず、募集(Recruitment)を削除（ルートやユーザーに依存しているため）
        db.query(modelDB.Recruitment).filter(modelDB.Recruitment.recruiter_user_id == id).delete()
        
        # 次に、ルート(Route)を削除（ユーザーに依存しているため。今回のエラーの直接の原因）
        # ※ modelDB.Route が定義されていることを確認してください
        db.query(modelDB.Route).filter(modelDB.Route.recruiter_user_id == id).delete()

        # その他のプロフィール・残高・注文履歴などを削除
        db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == id).delete()
        db.query(modelDB.PassengerProfile).filter(modelDB.PassengerProfile.user_id == id).delete()
        db.query(modelDB.UserBalance).filter(modelDB.UserBalance.user_id == id).delete()
        db.query(modelDB.Order).filter(modelDB.Order.user_id == id).delete()

        # 4. 最後に親である User を削除
        db.delete(user_to_delete)
        
        db.commit()
        return DeleteResponse(ok=True)

    except Exception as e:
        db.rollback()
        print(f"Delete Error Detail: {e}") # ログに詳細を表示
        raise HTTPException(status_code=500, detail="関連データの削除中にエラーが発生しました")