from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sys
import time
import numpy as np
from geopy.geocoders import Nominatim

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

# ルーター定義
router = APIRouter(prefix="/api/driver", tags=["driver"])

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def get_location_name(lat, lon) -> str:
    if lat is None or lon is None:
        return "場所情報なし"
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        geolocator = Nominatim(user_agent="my_ride_share_app_requests_v3", timeout=5)
        location = geolocator.reverse((lat_f, lon_f), language='ja')
        
        if location:
            addr = location.raw.get('address', {})
            city = addr.get('city', addr.get('town', addr.get('village', '')))
            road = addr.get('road', '')
            suburb = addr.get('suburb', addr.get('neighbourhood', ''))
            state = addr.get('province', addr.get('state', ''))
            
            if city and road: return f"{city} {road}"
            if city and suburb: return f"{city} {suburb}"
            return state if state else location.address.split(',')[0]
    except Exception as e:
        print(f"GeoError: {e}")
        pass
    return f"地点({lat}, {lon})"

def calculate_similarity(vec1: List[float], vec2: List[float]) -> int:
    if vec1 is None or vec2 is None: return 0
    try:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0: return 0
        cos_sim = np.dot(v1, v2) / (norm1 * norm2)
        return int(max(0, cos_sim) * 100)
    except Exception:
        return 0

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
    """
    # クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)

    # セッションIDが有効かどうかを確認
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_driver_id = int(res)

    # ドライバーのベクトル取得
    driver_profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == current_driver_id
    ).first()
    driver_embedding = driver_profile.embedding if driver_profile else None

    # データ取得 (status=0: pending)
    target_status = 0
    results = db.query(
        modelDB.Application,
        modelDB.Recruitment,
        modelDB.User,
        modelDB.PassengerProfile,
        modelDB.Route
    ).join(
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
        modelDB.Recruitment.recruiter_user_id == current_driver_id,
        modelDB.Application.status == target_status
    ).all()

    # 整形
    response_list = []
    for app, recruit, user, profile, route in results:
        try:
            rating_val = float(profile.rating) if profile else 0.0
            review_count_val = profile.ride_count if profile else 0
            
            # マッチング率計算
            passenger_embedding = profile.embedding if profile else None
            match_rate = calculate_similarity(driver_embedding, passenger_embedding)

            # 住所変換（API制限回避のため待機）
            time.sleep(1.0) 
            dep_str = get_location_name(route.dep_latitude, route.dep_longitude)
            des_str = get_location_name(route.arr_latitude, route.arr_longitude)
            
            dep_time_str = route.dep_time.strftime('%Y/%m/%d %H:%M')
            created_at_str = datetime.now().strftime('%Y/%m/%d')

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