# app/nori/Stocks.py
# 在庫管理機能（一覧表示・補充）

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import modelDB
from db_setting import SessionLocal 

# ★ここがポイント: URLを "products" とは別の "stocks" にします
router = APIRouter(prefix="/api/admin/stocks", tags=["admin_Stocks"])

# --- DB接続用 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- データ型定義 ---

# 在庫一覧表示用（商品情報の簡易版）
class StockListResponse(BaseModel):
    id: str
    name: str
    points: int
    stock: int

# 補充リクエスト用
class ReplenishRequest(BaseModel):
    amount: int

# --- API実装 ---

# 1. 在庫一覧取得
# URL: GET /api/admin/stocks
@router.get("")
def get_stock_list(db: Session = Depends(get_db)):
    # 在庫管理に必要な情報だけを取得
    products = db.query(modelDB.Product).order_by(modelDB.Product.product_id).all()
    
    results = []
    for p in products:
        results.append({
            "id": str(p.product_id),
            "name": p.name,
            "points": p.points,
            "stock": p.stock
        })
    return {"products": results}

# 2. 在庫補充
# URL: POST /api/admin/stocks/{product_id}/replenish
@router.post("/{product_id}/replenish")
def replenish_stock(product_id: int, req: ReplenishRequest, db: Session = Depends(get_db)):
    product = db.query(modelDB.Product).filter(modelDB.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # 在庫を加算
    product.stock += req.amount
    
    db.commit()
    db.refresh(product)
    
    return {
        "message": "Stock replenished", 
        "current_stock": product.stock,
        "added": req.amount
    }