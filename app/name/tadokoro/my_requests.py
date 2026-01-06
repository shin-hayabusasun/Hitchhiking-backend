from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any
import sys

# --- 共通インポート ---
sys.path.append('..')
from db_setting import SessionLocal
import modelDB

router = APIRouter(prefix="/api/hitchhiker", tags=["MyRequest"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- レスポンス型定義 ---
class RequestItem(BaseModel):
    id: int
    name: str
    rating: float
    reviews: int
    from_location: str  # JSONでは 'from' ですがPython予約語回避のため
    to: str
    date: str
    time: str
    price: int
    status: str

class MyRequestsResponse(BaseModel):
    success: bool
    data: Dict[str, List[Dict[str, Any]]]

@router.get("/my-requests", response_model=MyRequestsResponse)
async def get_my_requests(user_id: int = 1, db: Session = Depends(get_db)):
    """
    自分が「同乗者」として申請したリクエスト一覧を取得する
    user_id は本来ログインセッションから取得しますが、一旦 1 固定にしています
    """
    
    # 1. 自分が申請した application を取得
    # applications -> recruitments -> routes / users (driver) / driver_profiles
    applications = db.query(modelDB.Application).filter(modelDB.Application.applicant_user_id == user_id).all()

    all_list = []

    for app in applications:
        # 募集データ取得
        drive = db.query(modelDB.Recruitment).filter(modelDB.Recruitment.recruitment_id == app.recruitment_id).first()
        if not drive: continue
        
        # ドライバー、経路、プロフィールの取得 (getattrで安全に)
        driver = db.query(modelDB.User).filter(modelDB.User.user_id == drive.recruiter_user_id).first()
        route = db.query(modelDB.Route).filter(modelDB.Route.route_id == drive.route_id).first()
        profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == drive.recruiter_user_id).first()

        # フロントのモックデータ形式に変換
        item = {
            "id": app.application_id,
            "name": getattr(driver, 'name', "不明"),
            "rating": float(getattr(profile, 'rating', 0.0)),
            "reviews": int(getattr(profile, 'drive_count', 0)),
            "from": str(getattr(route, 'dep_point', "未設定")), # UIの'from'に対応
            "to": str(getattr(route, 'arr_point', "未設定")),
            "date": str(getattr(app, 'applied_at', "2025-01-01"))[:10], # 申請日
            "time": str(getattr(route, 'dep_time', "不明")),
            "price": getattr(drive, 'fare', 0),
            "status": getattr(app, 'status', "pending") # 'pending', 'approved', 'completed'
        }
        all_list.append(item)

    # 2. フロントエンドの期待通り、ステータスごとに振り分ける
    response_data = {
        "requesting": [i for i in all_list if i["status"] == "pending"],
        "approved": [i for i in all_list if i["status"] == "approved"],
        "completed": [i for i in all_list if i["status"] == "completed"]
    }

    # データが空の場合の「予備モックデータ」挿入 (テスト用)
    if not all_list:
        response_data["requesting"] = [{
            "id": 0, "name": "田中 太郎(Mock)", "rating": 4.8, "reviews": 45,
            "from": "東京駅", "to": "横浜駅", "date": "2025-11-03",
            "time": "2025-11-05 09:00", "price": 800, "status": "pending"
        }]

    return MyRequestsResponse(success=True, data=response_data)