# app/nori/Stock.py
# 在庫管理機能（一覧表示・補充・統計）

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import modelDB
from db_setting import SessionLocal 

router = APIRouter(prefix="/api/admin/stocks", tags=["admin_Stocks"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ReplenishRequest(BaseModel):
    amount: int

# --- API実装 ---

# 1. 在庫一覧取得
# URL: GET /api/admin/stocks
@router.get("")
def get_stock_list(db: Session = Depends(get_db)):
    products = db.query(modelDB.Product).order_by(modelDB.Product.product_id).all()
    
    results = []
    for p in products:
        results.append({
            "id": str(p.product_id),
            "name": p.name,
            "points": p.points,
            "stock": p.stock
        })
    
    # ここでは "products" だけを返します
    return {"products": results}

# 2. ★追加: 総販売数取得
# URL: GET /api/admin/stocks/sales
@router.get("/sales")
def get_total_sales(db: Session = Depends(get_db)):
    # 注文テーブル(Order)の全レコード数をカウント（キャンセル除外）
    total_sales = db.query(modelDB.Order).filter(modelDB.Order.status != "cancelled").count()
    
    return {"total_sales": total_sales}

# 3. 在庫補充
@router.post("/{product_id}/replenish")
def replenish_stock(product_id: int, req: ReplenishRequest, db: Session = Depends(get_db)):
    product = db.query(modelDB.Product).filter(modelDB.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.stock += req.amount
    db.commit()
    db.refresh(product)
    
    return {
        "message": "Stock replenished", 
        "current_stock": product.stock,
        "added": req.amount
    }