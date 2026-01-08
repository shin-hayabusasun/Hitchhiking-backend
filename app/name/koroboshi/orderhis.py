from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
import modelDB  # あなたのモデル定義ファイル
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user  # セッション検証関数

# フロントエンドの fetch('/api/points/orders') に合わせる
router = APIRouter(prefix="/api/points", tags=["points"])

# --- DBセッションの取得 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- レスポンスモデルの定義 ---
class OrderItemResponse(BaseModel):
    id: str
    productName: str
    points: int
    status: str
    orderDate: str

class OrderListResponse(BaseModel):
    orders: List[OrderItemResponse]

# --- APIの実装 ---
@router.get("/orders", response_model=OrderListResponse)
async def get_order_history(request: Request, db: Session = Depends(get_db)):
    """
    ポイント交換注文履歴取得API
    
    処理:
    1. クッキーからセッションIDを取得し、ユーザーを特定
    2. ordersテーブルとproductsテーブルを結合して、ログインユーザーの履歴を取得
    3. フロントエンドの型に合わせて返却
    """

    # 1. セッションチェック
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")

    user_id = int(res) # セッションから取得したユーザーID

    # 2. DBクエリ (Order と Product を結合)
    # 注文履歴を取得し、商品名(name)と消費ポイント(points)を合わせて取得
    history_data = (
        db.query(modelDB.Order, modelDB.Product)
        .join(modelDB.Product, modelDB.Order.product_id == modelDB.Product.product_id)
        .filter(modelDB.Order.user_id == user_id)
        .order_by(modelDB.Order.order_date.desc()) # 新しい順
        .all()
    )

    # 3. フロントエンドの型に変換
    results = []
    for order, product in history_data:
        results.append(OrderItemResponse(
            id=str(order.order_id),
            productName=product.name,
            points=product.points,
            status=order.status, # pending, shipped, delivered
            orderDate=order.order_date.strftime("%Y-%m-%d") # 文字列フォーマット
        ))

    return OrderListResponse(orders=results)