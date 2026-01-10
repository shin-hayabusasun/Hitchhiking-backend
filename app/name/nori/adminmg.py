from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List
import sys

# パス設定やDB設定のインポート（環境に合わせて調整してください）
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

# DBセッション取得用
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- レスポンスモデルの定義 ---
class AdminStatsResponse(BaseModel):
    totalUsers: int
    totalOrders: int
    totalProductsnumber: int
    issuedPoints: int  # 小数点以下を切り捨てる場合はint、保持する場合はfloat

# --- APIの実装 ---

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(request: Request, db: Session = Depends(get_db)):
    """
    管理者用統計情報取得API
    
    処理:
    1. セッションチェック（管理者権限の確認はget_current_userの仕様に準ずる）
    2. 各テーブルのカウント取得
    3. 運転完了(status=2想定)のRecruitmentからポイント計算
    """
    
    # 1. ログイン/セッション確認
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")

    # 2. 統計データの取得
    # ユーザー総数
    total_users = db.query(modelDB.User).count()
    
    # 注文総数
    total_orders = db.query(modelDB.Order).count()
    
    # 商品総数
    total_products = db.query(modelDB.Product).count()

    # 3. 発行済みポイントの計算 (Recruitmentテーブル)
    # ステータス定義の想定: 0:募集中, 1:募集終了, 2:運転完了
    # ※もしDB上の数値が異なる場合は、この filter の値を変更してください。
    DRIVE_COMPLETED_STATUS = 2
    
    # 運転完了した募集の運賃（fare）の合計を取得
    total_fare_sum = db.query(func.sum(modelDB.Recruitment.fare))\
        .filter(modelDB.Recruitment.status == DRIVE_COMPLETED_STATUS)\
        .scalar() or 0 # レコードがない場合はNoneが返るため0にする
    
    # 運賃合計の 1/6 をポイントとする（整数値にキャスト）
    calculated_points = int(total_fare_sum * (1/6))

    return AdminStatsResponse(
        totalUsers=total_users,
        totalOrders=total_orders,
        totalProductsnumber=total_products,
        issuedPoints=calculated_points
    )