# app/nori/routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

# 既存のDB設定をインポート（パスは環境に合わせて調整してください）
from db_setting import SessionLocal
import modelDB

router = APIRouter()

# --- データベース接続用関数 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydanticモデル (リクエスト/レスポンスの型定義) ---

class ProductBase(BaseModel):
    name: str
    points: int
    stock: int
    description: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: str  # フロントエンドに合わせてStringで返す
    reg_date: str

    class Config:
        from_attributes = True

class ReplenishRequest(BaseModel):
    amount: int

class OrderStatusUpdate(BaseModel):
    status: str

# --- API エンドポイント ---

# 1. 商品一覧取得 (商品管理・在庫管理)
@router.get("/api/points/products", tags=["Nori_Admin"])
def get_products(db: Session = Depends(get_db)):
    products = db.query(modelDB.Product).order_by(modelDB.Product.reg_date.desc()).all()
    
    # フロントエンドの形式に合わせて変換
    results = []
    for p in products:
        results.append({
            "id": str(p.product_id),
            "name": p.name,
            "points": p.points,
            "stock": p.stock,
            "description": p.description,
            "reg_date": p.reg_date.strftime("%Y-%m-%d") if p.reg_date else ""
        })
    
    return {"products": results}

# 2. 商品新規登録 (商品管理)
@router.post("/api/points/products", tags=["Nori_Admin"])
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    new_product = modelDB.Product(
        name=product.name,
        points=product.points,
        stock=product.stock,
        description=product.description,
        reg_date=datetime.now()
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"message": "Created successfully", "id": str(new_product.product_id)}

# 3. 商品削除 (商品管理)
@router.delete("/api/points/products/{product_id}", tags=["Nori_Admin"])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(modelDB.Product).filter(modelDB.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"message": "Deleted successfully"}

# 4. 商品編集 (商品管理)
@router.put("/api/points/products/{product_id}", tags=["Nori_Admin"])
def update_product(product_id: int, product_data: ProductCreate, db: Session = Depends(get_db)):
    product = db.query(modelDB.Product).filter(modelDB.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.name = product_data.name
    product.points = product_data.points
    product.stock = product_data.stock
    product.description = product_data.description
    
    db.commit()
    return {"message": "Updated successfully"}

# 5. 在庫補充 (在庫管理)
@router.post("/api/admin/products/{product_id}/replenish", tags=["Nori_Admin"])
def replenish_stock(product_id: int, req: ReplenishRequest, db: Session = Depends(get_db)):
    product = db.query(modelDB.Product).filter(modelDB.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.stock += req.amount
    db.commit()
    db.refresh(product)
    return {"message": "Stock replenished", "current_stock": product.stock}

# 6. 注文一覧取得 (注文管理)
@router.get("/api/points/orders", tags=["Nori_Admin"])
def get_orders(db: Session = Depends(get_db)):
    # UserとProductを結合して取得
    # ※ modelDB側で relationship が定義されていない場合、joinを使って手動で結合する必要があります
    # ここでは単純化のため、ordersを取得後にIDから名前を引く簡易実装にします
    
    orders = db.query(modelDB.Order).order_by(modelDB.Order.order_date.desc()).all()
    
    results = []
    for o in orders:
        # 関連データの取得 (N+1問題になりますが、まずは動くことを優先)
        product = db.query(modelDB.Product).filter(modelDB.Product.product_id == o.product_id).first()
        user = db.query(modelDB.User).filter(modelDB.User.user_id == o.user_id).first()
        
        results.append({
            "id": str(o.order_id),
            "orderNumber": f"ORD-{str(o.order_id).zfill(6)}",
            "productName": product.name if product else "Unknown Product",
            "points": product.points if product else 0,
            "status": o.status,
            "orderDate": o.order_date.strftime("%Y-%m-%d"),
            "customerName": user.name if user else "Unknown User",
            "quantity": 1 # 現状のテーブル定義に個数がないため1固定
        })
    
    return {"orders": results}

# 7. 注文ステータス更新 (注文管理)
@router.put("/api/admin/orders/{order_id}/status", tags=["Nori_Admin"])
def update_order_status(order_id: int, req: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(modelDB.Order).filter(modelDB.Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = req.status
    db.commit()
    return {"message": "Status updated"}

# 8. 注文統計情報 (注文管理)
@router.get("/api/admin/orders/stats", tags=["Nori_Admin"])
def get_order_stats(db: Session = Depends(get_db)):
    total = db.query(modelDB.Order).count()
    # statusカラムはStep1で追加済み前提
    ready = db.query(modelDB.Order).filter(modelDB.Order.status == "pending").count()
    shipped = db.query(modelDB.Order).filter(modelDB.Order.status == "shipped").count()
    
    return {
        "total_orders": total,
        "ready_count": ready,
        "shipped_count": shipped
    }