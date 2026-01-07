from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import modelDB
from db_setting import SessionLocal

router = APIRouter(prefix="/api/test", tags=["test"])

# DBセッション取得
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# リクエストボディの定義
class ProductTestCreate(BaseModel):
    name: str
    stock: int
    points: int
    description: Optional[str] = "テスト用商品"

@router.post("/products/add")
async def add_product_test(product: ProductTestCreate, db: Session = Depends(get_db)):
    """
    テスト用：無条件で商品を追加するAPI
    """
    try:
        new_product = modelDB.Product(
            name=product.name,
            stock=product.stock,
            points=product.points,
            description=product.description,
            reg_date=datetime.now()
        )
        
        db.add(new_product)
        db.commit()
        db.refresh(new_product)

        return {
            "status": "success",
            "added_product": {
                "id": new_product.product_id,
                "name": new_product.name
            }
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}