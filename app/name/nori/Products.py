from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# チームのDB設定をインポート
# ※ パスが違う場合は修正してください (例: from db_setting import SessionLocal)
import modelDB
from db_setting import SessionLocal 

# router = APIRouter()
router = APIRouter(prefix="/api/admin/products", tags=["admin_Products"])

# --- DB接続用 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- データ型定義 (Pydantic) ---
# フロントエンドから送られてくるデータのチェックに使います
class ProductCreate(BaseModel):
    name: str
    points: int
    stock: int
    description: Optional[str] = None

# --- API実装 ---

# 1. 商品一覧取得 (GET)
# @router.get("/api/points/products")
@router.get("")
def get_products(db: Session = Depends(get_db)):
    # 登録日が新しい順に取得
    products = db.query(modelDB.Product).order_by(modelDB.Product.reg_date.desc()).all()
    
    # フロントエンドの形式に合わせて変換 (product_id -> id)
    results = []
    for p in products:
        results.append({
            "id": str(p.product_id),
            "name": p.name,
            "points": p.points,
            "stock": p.stock,
            "description": p.description,
        })
    return {"products": results}

# 2. 商品新規登録 (POST)
@router.post("")
def create_product(item: ProductCreate, db: Session = Depends(get_db)):
    new_product = modelDB.Product(
        name=item.name,
        points=item.points,
        stock=item.stock,
        description=item.description,
        reg_date=datetime.now()
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"message": "Created", "id": str(new_product.product_id)}

# 3. 商品編集 (PUT)
@router.put("/{product_id}")
def update_product(product_id: int, item: ProductCreate, db: Session = Depends(get_db)):
    product = db.query(modelDB.Product).filter(modelDB.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # データを書き換え
    product.name = item.name
    product.points = item.points
    product.stock = item.stock
    product.description = item.description
    
    db.commit()
    return {"message": "Updated"}

# 4. 商品削除 (DELETE)
@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(modelDB.Product).filter(modelDB.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"message": "Deleted"}