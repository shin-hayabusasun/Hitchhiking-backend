from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
import sys

# パス設定（環境に合わせて調整してください）
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

# DBセッション
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- レスポンスモデルの定義 ---
class CustomerDetail(BaseModel):
    id: str
    name: str
    email: str
    points: int
    orderCount: int
    rideCount: int
    registeredAt: str

class CustomerListResponse(BaseModel):
    customers: List[CustomerDetail]

# --- API処理 ---

@router.get("/customers", response_model=CustomerListResponse)
async def get_admin_customers(request: Request, db: Session = Depends(get_db)):
    """
    管理者用：顧客一覧取得API
    
    処理：
    1. セッションIDの確認
    2. Usersテーブルを主軸に、各プロフィール・残高・注文数を結合して取得
    """
    
    # 1. セッション確認
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    # 管理者チェック（get_current_user内で管理者判定を行う想定）
    admin_user_id = get_current_user(session_id=session_id, db=db)
    if admin_user_id == "no":
        raise HTTPException(status_code=401, detail="Invalid session or unauthorized")

    # 2. データベースクエリ
    # サブクエリ：ユーザーごとの注文数をカウント
    order_counts = db.query(
        modelDB.Order.user_id,
        func.count(modelDB.Order.order_id).label("total_orders")
    ).group_by(modelDB.Order.user_id).subquery()

    # メインクエリ：Userを起点に外部結合
    # drive_count と ride_count を足して「相乗り回数」とする
    query = db.query(
        modelDB.User.user_id,
        modelDB.User.name,
        modelDB.User.email,
        func.coalesce(modelDB.UserBalance.point_balance, 0).label("points"),
        func.coalesce(order_counts.c.total_orders, 0).label("order_count"),
        (func.coalesce(modelDB.DriverProfile.drive_count, 0) + 
         func.coalesce(modelDB.PassengerProfile.ride_count, 0)).label("ride_count"),
        # Userテーブルに登録日がないため、プロフィールの登録日を代用（なければ現在日付）
        func.coalesce(modelDB.DriverProfile.reg_date, modelDB.PassengerProfile.reg_date).label("reg_date")
    ).outerjoin(modelDB.UserBalance, modelDB.User.user_id == modelDB.UserBalance.user_id)\
     .outerjoin(modelDB.DriverProfile, modelDB.User.user_id == modelDB.DriverProfile.user_id)\
     .outerjoin(modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id)\
     .outerjoin(order_counts, modelDB.User.user_id == order_counts.c.user_id)

    results = query.all()

    # 3. レスポンス形式に整形
    customers_data = []
    for row in results:
        customers_data.append(
            CustomerDetail(
                id=str(row.user_id),
                name=row.name,
                email=row.email,
                points=row.points,
                orderCount=row.order_count,
                rideCount=row.ride_count,
                registeredAt=str(row.reg_date) if row.reg_date else "2024-01-01"
            )
        )

    return CustomerListResponse(customers=customers_data)