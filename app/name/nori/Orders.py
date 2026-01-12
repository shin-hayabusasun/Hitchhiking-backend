# app/nori/Orders.py
# 注文管理機能（一覧表示・ステータス更新）

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
import modelDB
from db_setting import SessionLocal 

# URLプレフィックスは "orders"
router = APIRouter(prefix="/api/admin/orders", tags=["admin_Orders"])

# --- DB接続用 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- データ型定義 ---

# ステータス更新用リクエスト
class OrderStatusUpdate(BaseModel):
    status: str  # "pending", "shipped", "completed", "cancelled" など

# --- API実装 ---

# 1. 注文一覧取得
# URL: GET /api/admin/orders
@router.get("")
def get_orders(db: Session = Depends(get_db)):
    # 日付が新しい順に取得
    orders = db.query(modelDB.Order).order_by(modelDB.Order.order_date.desc()).all()
    
    results = []
    for o in orders:
        # 関連データの取得 (IDを使って商品名とユーザー名を引く)
        product = db.query(modelDB.Product).filter(modelDB.Product.product_id == o.product_id).first()
        user = db.query(modelDB.User).filter(modelDB.User.user_id == o.user_id).first()
        
        results.append({
            "id": str(o.order_id),
            "orderNumber": f"ORD-{str(o.order_id).zfill(6)}", # 例: ORD-000001
            "productName": product.name if product else "削除された商品",
            "points": product.points if product else 0,
            "status": o.status, # pending, shipped, etc.
            "orderDate": o.order_date.strftime("%Y-%m-%d %H:%M") if o.order_date else "",
            "customerName": user.name if user else "不明なユーザー",
        })
    
    return {"orders": results}

# 2. 注文ステータス更新
# URL: PUT /api/admin/orders/{order_id}/status
@router.put("/{order_id}/status")
def update_order_status(order_id: int, req: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(modelDB.Order).filter(modelDB.Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # ステータスを更新 (例: pending -> shipped)
    order.status = req.status
    db.commit()
    
    return {"message": "Status updated", "new_status": order.status}