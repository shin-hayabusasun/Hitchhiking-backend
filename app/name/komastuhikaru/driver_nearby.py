from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import math
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
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2点間の距離を計算 (Haversine formula) -> km
def calculate_distance(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]:
        return 9999.0
    
    R = 6371  # 地球の半径 (km)
    d_lat = math.radians(float(lat2) - float(lat1))
    d_lon = math.radians(float(lon2) - float(lon1))
    a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + \
        math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * \
        math.sin(d_lon / 2) * math.sin(d_lon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 住所変換
def get_location_name(lat, lon) -> str:
    if lat is None or lon is None: return "場所情報なし"
    try:
        geolocator = Nominatim(user_agent="drive_app_nearby_v1", timeout=3)
        location = geolocator.reverse((float(lat), float(lon)), language='ja')
        if location:
            addr = location.raw.get('address', {})
            city = addr.get('city', addr.get('town', addr.get('village', '')))
            road = addr.get('road', '')
            if city and road: return f"{city} {road}"
            return location.address.split(',')[0]
    except Exception:
        pass
    return f"地点({lat:.4f}, {lon:.4f})"

# ベクトルマッチング度計算
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
class NearbyRecruitmentItem(BaseModel):
    id: int
    passengerName: str
    departure: str
    destination: str
    date: str
    time: str
    budget: int
    distance: float
    matchingScore: int
    rating: float
    reviewCount: int
    startsIn: int # 何分後に出発か

class NearbyListResponse(BaseModel):
    requests: List[NearbyRecruitmentItem]

# ---------------------------------------------------------
# API Endpoint
# ---------------------------------------------------------
@router.get("/nearby", response_model=NearbyListResponse)
async def get_nearby_recruitments(
    request: Request,
    lat: float = Query(..., description="現在地の緯度"),
    lng: float = Query(..., description="現在地の経度"),
    radius: float = Query(10.0, description="検索半径(km)"),
    db: Session = Depends(get_db)
):
    """
    近くの同乗者募集を取得
    条件: 半径10km以内 & 出発まで2時間以内
    """
    # 1. 認証
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_driver_id = int(res)

    # 2. ドライバー情報の取得 (ベクトル用)
    driver_profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == current_driver_id
    ).first()
    driver_embedding = driver_profile.embedding if driver_profile else None

    # 3. 日時フィルタの準備
    now = datetime.now()
    limit_time = now + timedelta(hours=2) # 2時間後

    # 4. DBクエリ (同乗者募集, 募集中, 2時間以内)
    # type=1: 同乗者からの募集 (想定)
    # status=0: 募集中 (想定)
    query = db.query(
        modelDB.Recruitment,
        modelDB.Route,
        modelDB.User,
        modelDB.PassengerProfile
    ).join(
        modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).join(
        modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id
    ).outerjoin(
        modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id
    ).filter(
        modelDB.Recruitment.type == 1,      # 同乗者募集
        modelDB.Recruitment.status == 0,    # 募集中
        modelDB.Route.dep_time >= now,      # 過去ではない
        modelDB.Route.dep_time <= limit_time # 2時間以内
    )

    candidates = query.all()

    # 5. 距離フィルタ & データ整形
    response_list = []

    for recruit, route, user, profile in candidates:
        # 距離計算
        dist = calculate_distance(lat, lng, route.dep_latitude, route.dep_longitude)
        
        # 指定半径以内 (デフォルト10km) かつ、まだリストに追加していない場合
        if dist <= radius:
            try:
                # マッチング度
                passenger_embedding = profile.embedding if profile else None
                score = calculate_similarity(driver_embedding, passenger_embedding)

                # 地名変換 (APIレート制限対策)
                time.sleep(1.0) 
                dep_name = get_location_name(route.dep_latitude, route.dep_longitude)
                des_name = get_location_name(route.arr_latitude, route.arr_longitude)

                # 出発までの時間 (分)
                delta = route.dep_time - now
                starts_in_minutes = int(delta.total_seconds() / 60)

                item = NearbyRecruitmentItem(
                    id=recruit.recruitment_id,
                    passengerName=user.name,
                    departure=dep_name,
                    destination=des_name,
                    date=route.dep_time.strftime('%Y-%m-%d'),
                    time=route.dep_time.strftime('%H:%M'),
                    budget=recruit.fare,
                    distance=round(dist, 1),
                    matchingScore=score,
                    rating=float(profile.rating) if profile else 0.0,
                    reviewCount=profile.ride_count if profile else 0,
                    startsIn=starts_in_minutes
                )
                response_list.append(item)

            except Exception as e:
                print(f"Error processing recruitment {recruit.recruitment_id}: {e}")
                continue

    # 距離が近い順にソート
    response_list.sort(key=lambda x: x.distance)

    return NearbyListResponse(requests=response_list)