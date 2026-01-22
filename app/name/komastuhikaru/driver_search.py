import logging
import json
import math
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import extract, cast, Date, Numeric, asc
from pydantic import BaseModel
from pgvector.sqlalchemy import Vector

import sys
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/driver", tags=["driver_search"])

# --- Database ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Schemas ---
class PassengerSearchItem(BaseModel):
    id: str
    passengerName: str
    start: str
    end: str
    date: str
    money: int
    people: int
    match: int
    rating: float
    reviewCount: int

class SearchResponse(BaseModel):
    card: List[PassengerSearchItem]

class TimeRange(BaseModel):
    start: str
    end: str

class PriceRange(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None

class SearchFilters(BaseModel):
    departure: str
    destination: str
    date: Optional[str] = None
    timeRange: Optional[TimeRange] = None
    priceRange: PriceRange
    seats: int
    isVerifiedOnly: Optional[bool] = None

class SearchRequest(BaseModel):
    filter: SearchFilters

# --- Helpers ---
async def get_coordinates(address: str):
    """LocationIQ APIを使用して座標を取得（非同期版）"""
    import os
    
    if not address or not address.strip():
        return None, None
    
    api_key = os.getenv("LOCATIONIQ_API_KEY", "pk.4c89f676c0053659bd58a6708715b00e")
    
    max_retries = 3
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                url = "https://us1.locationiq.com/v1/search.php"
                params = {
                    "key": api_key,
                    "q": f"{address}, Japan",
                    "format": "json",
                    "limit": 1
                }
                
                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                if data and len(data) > 0:
                    return float(data[0]['lat']), float(data[0]['lon'])
                    
            except:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
    
    return None, None

def get_min_distance_to_path(point_p, path_points):
    min_dist_sq = float('inf')
    closest_index = -1
    
    if not path_points or point_p[0] is None:
        return min_dist_sq, closest_index
        
    for i, pt in enumerate(path_points):
        dist_sq = (point_p[0] - pt[0])**2 + (point_p[1] - pt[1])**2
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            closest_index = i
            
    return min_dist_sq, closest_index

# --- Endpoint ---
@router.post("/search", response_model=SearchResponse)
async def search_passengers(req: SearchRequest, request: Request, db: Session = Depends(get_db)):
    logger.info("=== 運転者検索開始 ===")

    # 1. Auth
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no": raise HTTPException(status_code=401, detail="Invalid session")
    current_driver_id = int(user_id_str)

    # 2. Driver Info
    driver_profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == current_driver_id).first()
    driver_embedding = driver_profile.embedding if driver_profile else None

    # 3. Input Coordinates (並列実行)
    f = req.filter
    p_start, p_end = await asyncio.gather(
        get_coordinates(f.departure),
        get_coordinates(f.destination)
    )
    
    # 4. Base Query
    if driver_embedding is not None:
        dist_col = modelDB.PassengerProfile.embedding.cosine_distance(driver_embedding).label("v_dist")
        query = db.query(modelDB.Recruitment, dist_col)
    else:
        # ★修正ポイント1: ベクトルが無い場合は 0 ではなく None (Null) として扱う
        query = db.query(modelDB.Recruitment, cast(None, Numeric).label("v_dist"))

    query = query.join(
        modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).join(
        modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id
    ).outerjoin(
        modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id
    )

    # 5. Filtering
    
    # 現在時刻 (JST補正を入れるのが安全ですが、元のコードに準拠してdatetime.now()としています)
    now = datetime.now()

    query = query.filter(
        modelDB.Recruitment.type == 1,       # 同乗者募集
        modelDB.Recruitment.status == 0,     # 募集中
        modelDB.Route.dep_time > now,
        modelDB.Recruitment.recruiter_user_id != current_driver_id
    )

    # 条件: 予算・人数
    if f.priceRange.min is not None:
        query = query.filter(modelDB.Recruitment.fare >= f.priceRange.min)
    if f.priceRange.max is not None:
        query = query.filter(modelDB.Recruitment.fare <= f.priceRange.max)
    if f.seats > 0:
        query = query.filter(modelDB.Recruitment.capacity <= f.seats)

    # 日付指定
    if f.date:
        try:
            target_date = datetime.strptime(f.date, '%Y-%m-%d')
            search_start = target_date - timedelta(hours=12)
            search_end = target_date + timedelta(days=1, hours=12)
            query = query.filter(modelDB.Route.dep_time.between(search_start, search_end))
        except ValueError:
            pass

    # 時間帯フィルタ
    if f.timeRange and (f.timeRange.start != "00:00" or f.timeRange.end != "23:59"):
        try:
            start_h = int(f.timeRange.start.split(":")[0])
            end_h = int(f.timeRange.end.split(":")[0])
            query = query.filter(extract('hour', modelDB.Route.dep_time).between(start_h, end_h))
        except:
            pass

    # Execute SQL
    sql_results = query.all()
    logger.info(f"SQL Hit: {len(sql_results)}")

    response_cards = []

    # 6. Python Logic
    for r, v_dist in sql_results:
        route_info = db.query(modelDB.Route).filter(modelDB.Route.route_id == r.route_id).first()
        user_info = db.query(modelDB.User).filter(modelDB.User.user_id == r.recruiter_user_id).first()
        passenger_profile = db.query(modelDB.PassengerProfile).filter(modelDB.PassengerProfile.user_id == r.recruiter_user_id).first()

        try:
            path_points = json.loads(route_info.path_data) if route_info and route_info.path_data else []
        except:
            path_points = []
        
        if not path_points and route_info:
            path_points = [
                [float(route_info.dep_latitude), float(route_info.dep_longitude)],
                [float(route_info.arr_latitude), float(route_info.arr_longitude)]
            ]

        match_score = 50 # デフォルト値

        # 経路チェック
        if p_start[0] is not None and p_end[0] is not None:
            dist_start_sq, idx_start = get_min_distance_to_path(p_start, path_points)
            dist_end_sq, idx_end = get_min_distance_to_path(p_end, path_points)

            dist_val = math.sqrt(dist_start_sq) + math.sqrt(dist_end_sq)
            geo_score = 100 - (dist_val * 500)

            if idx_start >= idx_end or geo_score < 0:
                continue 
            
            match_score = int(max(0, min(100, geo_score)))

        else:
            # ★修正ポイント2: ベクトル計算ロジックの統一
            # v_distがNoneなら、スコアは50%とする
            current_dist = float(v_dist) if v_dist is not None else None
            
            if current_dist is not None:
                match_score = int(max(0, min(100, (1 - current_dist) * 100)))
            else:
                match_score = 50  # データなしの場合のデフォルト

        response_cards.append(PassengerSearchItem(
            id=str(r.recruitment_id),
            passengerName=user_info.name if user_info else "Unknown",
            start=route_info.depname or "不明",
            end=route_info.arrname or "不明",
            date=route_info.dep_time.strftime('%Y-%m-%d %H:%M') if route_info else "",
            money=r.fare,
            people=r.capacity,
            match=match_score,
            rating=float(passenger_profile.rating) if passenger_profile else 0.0,
            reviewCount=int(passenger_profile.ride_count) if passenger_profile else 0
        ))

    # マッチ度順にソート
    response_cards.sort(key=lambda x: x.match, reverse=True)

    return SearchResponse(card=response_cards)