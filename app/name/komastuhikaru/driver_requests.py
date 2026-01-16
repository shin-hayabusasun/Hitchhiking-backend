from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import cast, Numeric
from pydantic import BaseModel
from typing import List
from datetime import datetime
import sys

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/driver", tags=["driver"])

# ---------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------
class ApplicationRequestItem(BaseModel):
    id: int
    passengerName: str
    matchingRate: int
    rating: float
    reviewCount: int
    departure: str
    destination: str
    departureTime: str
    createdAt: str

class ApplicationListResponse(BaseModel):
    requests: List[ApplicationRequestItem]

# ---------------------------------------------------------
# Dependency
# ---------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# API Endpoint
# ---------------------------------------------------------
@router.get("/requests", response_model=ApplicationListResponse)
async def get_driver_requests(request: Request, status: str = "pending", db: Session = Depends(get_db)):
    """
    申請一覧取得
    自分が「運転者として」作成した募集への申請のみを表示
    """
    # 1. 認証
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no": raise HTTPException(status_code=401, detail="Invalid session")
    
    current_driver_id = int(res)

    # 2. ベクトル取得
    driver_profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == current_driver_id
    ).first()
    driver_embedding = driver_profile.embedding if driver_profile else None

    # 3. クエリ構築
    # 申請者のPassengerProfileとの距離を計算
    if driver_embedding is not None:
        dist_col = modelDB.PassengerProfile.embedding.cosine_distance(driver_embedding).label("v_dist")
        query = db.query(
            modelDB.Application,
            modelDB.Recruitment,
            modelDB.User,
            modelDB.PassengerProfile,
            modelDB.Route,
            dist_col
        )
    else:
        query = db.query(
            modelDB.Application,
            modelDB.Recruitment,
            modelDB.User,
            modelDB.PassengerProfile,
            modelDB.Route,
            cast(None, Numeric).label("v_dist")
        )

    # 現在時刻
    now = datetime.now()
    target_status = 0 # 0: 申請中(pending)

    results = query.join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).join(
        modelDB.User,
        modelDB.Application.applicant_user_id == modelDB.User.user_id
    ).outerjoin(
        modelDB.PassengerProfile,
        modelDB.User.user_id == modelDB.PassengerProfile.user_id
    ).join(
        modelDB.Route,
        modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).filter(
        # ★重要: 自分が作成した募集であること
        modelDB.Recruitment.recruiter_user_id == current_driver_id,
        
        # ★追加: 「運転者としての募集」に限定する (type=0)
        # これにより、自分が同乗者として出した募集へのアクションが混ざるのを防ぐ
        modelDB.Recruitment.type == 0,

        # ステータスと日時のフィルタ
        modelDB.Application.status == target_status,
        modelDB.Route.dep_time >= now
    ).all()

    # 4. 整形
    response_list = []
    for app, recruit, user, profile, route, v_dist in results:
        try:
            rating_val = float(profile.rating) if profile else 0.0
            review_count_val = profile.ride_count if profile else 0
            
            # マッチング率
            current_dist = float(v_dist) if v_dist is not None else None
            if current_dist is not None:
                match_rate = int(max(0, min(100, (1 - current_dist) * 100)))
            else:
                match_rate = 50

            dep_str = route.depname if route.depname else "出発地情報なし"
            des_str = route.arrname if route.arrname else "目的地情報なし"
            
            dep_time_str = route.dep_time.strftime('%Y/%m/%d %H:%M')
            created_at_str = datetime.now().strftime('%Y/%m/%d') # 本来は app.created_at があればそれを使う

            response_list.append(ApplicationRequestItem(
                id=app.application_id,
                passengerName=user.name,
                matchingRate=match_rate,
                rating=rating_val,
                reviewCount=review_count_val,
                departure=dep_str,
                destination=des_str,
                departureTime=dep_time_str,
                createdAt=created_at_str
            ))
        except Exception as e:
            print(f"Error processing item: {e}")
            continue

    return ApplicationListResponse(requests=response_list)