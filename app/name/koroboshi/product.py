from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import modelDB  # DBモデル定義
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user  # セッション検証関数

# フロントエンドのfetchパスに合わせて設定
router = APIRouter(prefix="/api/points", tags=["points"])

# --- DBセッションの取得 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- レスポンスモデルの定義 ---
class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    points: int
    stock: int
    image: Optional[str] = None # DBに画像パスがある場合はここに入れる

class ProductListResponse(BaseModel):
    products: List[ProductResponse]

# --- APIの実装 ---
@router.get("/products", response_model=ProductListResponse)
async def get_products(request: Request, db: Session = Depends(get_db)):
    """
    ポイント交換商品一覧取得
    
    処理:
    1. セッションIDを確認（ログインチェック）
    2. productsテーブルから全商品を取得
    3. フロントエンドの型に合わせて返却
    """
    
    # 1. セッションチェック（クッキーから取得）
    session_id = request.cookies.get("session_id")
    if not session_id:
        # ログインしていない場合でも閲覧は許可するならここはパス、
        # 制限するならHTTPExceptionを出す
        raise HTTPException(status_code=401, detail="セッションが見つかりません")

    user_res = get_current_user(session_id=session_id, db=db)
    if user_res == "no":
        raise HTTPException(status_code=401, detail="有効なセッションではありません")

    # 2. DBアクセス: 商品一覧を取得
    # 最新の登録順に取得
    db_products = db.query(modelDB.Product).order_by(modelDB.Product.reg_date.desc()).all()

    # 3. フロントエンドの型 (ProductResponse) に変換してリストを作成
    product_list = []
    for p in db_products:
        product_list.append(
            ProductResponse(
                id=str(p.product_id),  # DBはint、フロントはstring
                name=p.name,
                description=p.description,
                points=p.points,
                stock=p.stock,
                image=None # DBモデルにimageカラムが追加されたら p.image を指定
            )
        )

    return ProductListResponse(products=product_list)