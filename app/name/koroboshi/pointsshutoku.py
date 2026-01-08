from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import modelDB # あなたのモデル定義ファイル
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user # セッション検証関数

router = APIRouter(prefix="/api/point", tags=["point"])

# --- DBセッションの取得 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- レスポンスモデルの定義 ---
# フロントエンドが期待している型 (totalBalance, sales) に合わせます
class PointRemainResponse(BaseModel):
    totalBalance: int
    sales: int

# --- APIエンドポイント ---
@router.post("/remain", response_model=PointRemainResponse)
async def get_point_remain(request: Request, db: Session = Depends(get_db)):
    """
    ログイン中のユーザーの売上・ポイント残高を取得する
    """
    
    # 1. クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="セッションが見つかりません。ログインしてください。")

    # 2. セッションが有効か確認し、ユーザーIDを取得
    user_id_res = get_current_user(session_id=session_id, db=db)
    if user_id_res == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です。")

    # 3. DB（user_balancesテーブル）から残高情報を取得
    # user_id_res は文字列で返ってくる想定なので int にキャスト（必要に応じて）
    user_balance = db.query(modelDB.UserBalance).filter(
        modelDB.UserBalance.user_id == int(user_id_res)
    ).first()

    # レコードが存在しない場合のデフォルト値設定
    if not user_balance:
        return PointRemainResponse(totalBalance=0, sales=0)

    # 4. フロントエンドの期待するフィールド名にマッピングして返す
    return PointRemainResponse(
        totalBalance=user_balance.point_balance, # DB: point_balance -> フロント: totalBalance
        sales=user_balance.sales_history         # DB: sales_history -> フロント: sales
    )