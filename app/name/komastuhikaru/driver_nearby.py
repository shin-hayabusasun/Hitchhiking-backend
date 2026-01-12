from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
# ★追加: DB側での型キャスト用
from sqlalchemy import cast, Numeric 
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import math
# import numpy as np # numpyは不要になります
# from geopy.geocoders import Nominatim # geopyも不要になります

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

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
    startsIn: int

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
    now = datetime.utcnow() + timedelta(hours=9)
    limit_time = now + timedelta(hours=2) # テスト用に24時間

    # 4. DBクエリ構築 (ベクトル距離計算を含む)
    # ドライバー(自分)と、募集者のパッセンジャープロフィールの距離を計算
    if driver_embedding is not None:
        # pgvectorのcosine_distanceを利用
        dist_col = modelDB.PassengerProfile.embedding.cosine_distance(driver_embedding).label("v_dist")
        query = db.query(
            modelDB.Recruitment,
            modelDB.Route,
            modelDB.User,
            modelDB.PassengerProfile,
            dist_col
        )
    else:
        # ベクトルがない場合は距離0(or Null)として扱う
        query = db.query(
            modelDB.Recruitment,
            modelDB.Route,
            modelDB.User,
            modelDB.PassengerProfile,
            cast(None, Numeric).label("v_dist")
        )

    # 結合条件
    query = query.join(
        modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).join(
        modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id
    ).outerjoin(
        modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id
    ).filter(
        modelDB.Recruitment.type == 1,      # 同乗者募集
        modelDB.Recruitment.status == 0,    # 募集中
        modelDB.Route.dep_time >= now,      # 過去ではない
        modelDB.Route.dep_time <= limit_time 
    )

    candidates = query.all()

    # 5. 距離フィルタ & データ整形
    response_list = []

    for recruit, route, user, profile, v_dist in candidates:
        # 物理的な距離計算 (km)
        dist = calculate_distance(lat, lng, route.dep_latitude, route.dep_longitude)
        
        # 指定半径以内
        if dist <= radius:
            try:
                # ★修正: マッチングスコア計算 (boshukensakuと同じロジック)
                # v_dist はコサイン距離 (0~2)。 0に近いほど似ている。
                current_dist = float(v_dist) if v_dist is not None else None
                
                if current_dist is not None:
                    # 距離をスコア(0-100)に変換
                    score = int(max(0, min(100, (1 - current_dist) * 100)))
                else:
                    score = 50 # ベクトルがない場合のデフォルト

                # ★修正: DBから地名を直接取得
                dep_name = route.depname if route.depname else "出発地不明"
                des_name = route.arrname if route.arrname else "目的地不明"

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