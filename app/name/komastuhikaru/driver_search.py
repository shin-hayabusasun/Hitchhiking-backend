import logging
import json
import math
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import extract, cast, Date, Numeric, asc
from pydantic import BaseModel
from geopy.geocoders import Nominatim
from pgvector.sqlalchemy import Vector

# パス設定
import sys
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

# --- ログの設定 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/driver", tags=["driver_search"])

# --- データベースセッション設定 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydanticモデル定義 ---

class PassengerSearchItem(BaseModel):
    id: str
    passengerName: str
    start: str
    end: str
    date: str
    money: int      # 予算
    people: int     # 希望人数
    match: Optional[int] = None
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
    # conditions は削除しました
    isVerifiedOnly: Optional[bool] = None

class SearchRequest(BaseModel):
    filter: SearchFilters

# --- ヘルパー関数 (boshukensakuから流用) ---

def get_coordinates(address: str):
    """地名から座標を取得"""
    if not address or not address.strip():
        return None, None
    geocoder = Nominatim(user_agent="driver_search_app_v2026", timeout=10)
    try:
        location = geocoder.geocode(f"{address}, Japan")
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        logger.error(f"ジオコーディングエラー ({address}): {e}")
    return None, None

def get_min_distance_to_path(point_p, path_points):
    """
    ある地点(point_p)が、経路(path_points)の中で一番近い点のインデックスと距離を返す。
    これにより「出発地」が「目的地」より先にあるか（進行方向）を判定する。
    """
    min_dist_sq = float('inf')
    closest_index = -1
    
    if not path_points or point_p[0] is None:
        return min_dist_sq, closest_index
        
    for i, pt in enumerate(path_points):
        # 緯度経度の差の二乗和（簡易距離）
        dist_sq = (point_p[0] - pt[0])**2 + (point_p[1] - pt[1])**2
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            closest_index = i
            
    return min_dist_sq, closest_index

# --- APIエンドポイント ---
@router.post("/search", response_model=SearchResponse)
async def search_passengers(req: SearchRequest, request: Request, db: Session = Depends(get_db)):
    logger.info("=== 運転者による同乗者募集検索開始 ===")
    
    # 1. 認証チェック
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    driver_id = int(user_id_str)

    # 2. ドライバー自身のベクトルを取得 (マッチング計算用)
    driver_profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == driver_id).first()
    driver_embedding = driver_profile.embedding if driver_profile else None

    # 3. 検索条件の座標取得
    f = req.filter
    p_start = get_coordinates(f.departure)
    p_end = get_coordinates(f.destination)

    # 4. クエリ構築
    # PassengerProfileとの距離を計算 (pgvector cosine_distance)
    if driver_embedding is not None:
        dist_col = modelDB.PassengerProfile.embedding.cosine_distance(driver_embedding).label("v_dist")
        query = db.query(modelDB.Recruitment, dist_col)
    else:
        query = db.query(modelDB.Recruitment, cast(0, Numeric).label("v_dist"))

    # テーブル結合
    query = query.join(
        modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).join(
        modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id
    ).outerjoin(
        modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id
    )

    # --- SQLフィルタリング ---
    
    # (A) 基本条件: 同乗者からの募集(type=1) かつ 募集中(status=0) かつ 未来
    query = query.filter(
        modelDB.Recruitment.type == 1,
        modelDB.Recruitment.status == 0,
        modelDB.Route.dep_time >= datetime.now()
    )

    # (B) 予算フィルタ
    # 同乗者の提示額(fare)が、ドライバーの希望下限以上であること
    if f.priceRange.min is not None:
        query = query.filter(modelDB.Recruitment.fare >= f.priceRange.min)
    if f.priceRange.max is not None:
        query = query.filter(modelDB.Recruitment.fare <= f.priceRange.max)
    
    # (C) 人数フィルタ
    # 同乗希望人数(capacity)が、ドライバーの座席数以下であること
    if f.seats > 0:
        query = query.filter(modelDB.Recruitment.capacity <= f.seats)

    # (D) 日付フィルタ
    if f.date:
        try:
            target_date = datetime.strptime(f.date, '%Y-%m-%d').date()
            query = query.filter(cast(modelDB.Route.dep_time, Date) == target_date)
        except ValueError:
            pass

    # (E) 時間帯フィルタ
    if f.timeRange and (f.timeRange.start != "00:00" or f.timeRange.end != "23:59"):
        try:
            start_h = int(f.timeRange.start.split(":")[0])
            end_h = int(f.timeRange.end.split(":")[0])
            query = query.filter(extract('hour', modelDB.Route.dep_time).between(start_h, end_h))
        except:
            pass

    # ベクトル距離順にソート（マッチしやすい順）
    if driver_embedding is not None:
        query = query.order_by(asc("v_dist"))

    sql_results = query.all()
    response_cards = []

    # --- Python側での詳細解析 (経路判定 & スコアリング) ---
    for r, v_dist in sql_results:
        route_info = db.query(modelDB.Route).filter(modelDB.Route.route_id == r.route_id).first()
        user_info = db.query(modelDB.User).filter(modelDB.User.user_id == r.recruiter_user_id).first()
        passenger_profile = db.query(modelDB.PassengerProfile).filter(modelDB.PassengerProfile.user_id == r.recruiter_user_id).first()

        # 経路データのパース
        try:
            path_points = json.loads(route_info.path_data) if route_info and route_info.path_data else []
        except:
            path_points = []

        if not path_points and route_info:
            # データがない場合は始点・終点のみで作る
            path_points = [
                [float(route_info.dep_latitude), float(route_info.dep_longitude)],
                [float(route_info.arr_latitude), float(route_info.arr_longitude)]
            ]

        # ★★★ 経路の方向チェック (boshukensakuロジック) ★★★
        # ドライバーが入力した出発地(p_start)と目的地(p_end)が、
        # 同乗者のルート(path_points)上で「順序通り」に存在するかチェック
        is_order_ok = True
        if p_start[0] is not None and p_end[0] is not None:
            _, idx_start = get_min_distance_to_path(p_start, path_points)
            _, idx_end = get_min_distance_to_path(p_end, path_points)
            
            # 入力された出発地が、入力された目的地よりも「手前」にあるか
            # (かつ、検索地点がルートから離れすぎていないかは min_dist_sq で判定可能だが今回は順序優先)
            is_order_ok = (idx_start < idx_end)

        if not is_order_ok:
            continue # 方向が逆、もしくは一致しないので除外

        # マッチスコア計算
        current_dist = float(v_dist) if v_dist is not None else None
        if current_dist is not None:
            match_score = int(max(0, min(100, (1 - current_dist) * 100)))
        else:
            match_score = 50

        # 地名取得
        dep_name = getattr(route_info, 'depname', "出発地不明")
        arr_name = getattr(route_info, 'arrname', "目的地不明")

        response_cards.append(PassengerSearchItem(
            id=str(r.recruitment_id),
            passengerName=user_info.name if user_info else "不明",
            start=dep_name,
            end=arr_name,
            date=route_info.dep_time.strftime('%Y-%m-%d %H:%M') if route_info else "",
            money=r.fare,
            people=r.capacity,
            match=match_score,
            rating=float(passenger_profile.rating) if passenger_profile else 0.0,
            reviewCount=int(passenger_profile.ride_count) if passenger_profile else 0
        ))

    logger.info(f"検索結果: {len(response_cards)} 件")
    return SearchResponse(card=response_cards)