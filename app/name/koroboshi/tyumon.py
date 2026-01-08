from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import modelDB
from db_setting import SessionLocal
# 以前の修正に基づき、正しいパスを指定
from app.name.hieda.user import get_current_user 

router = APIRouter(prefix="/api/points", tags=["points"])

# --- DBセッション ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- リクエストモデル ---
class ExchangeRequest(BaseModel):
    product_id: int # Next.jsから送られてくるID

# --- レスポンスモデル ---
class ExchangeResponse(BaseModel):
    ok: bool
    detail: str

# --- APIの実装 ---
@router.post("/exchange", response_model=ExchangeResponse)
async def exchange_product(
    req_data: ExchangeRequest, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    商品交換処理API
    """
    
    # 1. ログインチェック
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="ログインが必要です")

    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です")
    
    user_id = int(user_id_str)

    # トランザクション開始
    try:
        # 2. 商品情報の取得と在庫チェック
        # SELECT ... FOR UPDATE を使うと、同時に他の人が交換して在庫がマイナスになるのを防げます
        product = db.query(modelDB.Product).filter(
            modelDB.Product.product_id == req_data.product_id
        ).with_for_update().first()

        if not product:
            raise HTTPException(status_code=404, detail="商品が見つかりません")
        
        if product.stock <= 0:
            raise HTTPException(status_code=400, detail="在庫がありません")

        # 3. ユーザーのポイント残高チェック
        user_balance = db.query(modelDB.UserBalance).filter(
            modelDB.UserBalance.user_id == user_id
        ).with_for_update().first()

        if not user_balance or user_balance.point_balance < product.points:
            raise HTTPException(status_code=400, detail="ポイントが不足しています")

        # 4. DB更新処理
        # (a) ポイントを減らす
        user_balance.point_balance -= product.points
        
        # (b) 商品の在庫を減らす
        product.stock -= 1
        
        # (c) 注文履歴（Order）を作成
        new_order = modelDB.Order(
            product_id=product.product_id,
            user_id=user_id,
            order_date=datetime.now(),
            status="pending" # 準備中
        )
        db.add(new_order)

        # 全ての処理を確定
        db.commit()
        return ExchangeResponse(ok=True, detail="交換が完了しました")

    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        print(f"Internal Error: {e}")
        raise HTTPException(status_code=500, detail="内部サーバーエラーが発生しました")