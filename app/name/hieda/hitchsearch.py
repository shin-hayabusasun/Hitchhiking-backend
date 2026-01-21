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

# 自作モジュール
import modelDB
from db_setting import SessionLocal
from .user import get_current_user

# --- ログの設定 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hitchhiker", tags=["hitchhikersearch"])

# --- データベースセッション設定 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydanticモデル定義 ---
class CarCondition(BaseModel):
    jouken_name: str

class DriveItem(BaseModel):
    id: str
    name: str
    start: str
    end: str
    date: str
    money: int
    people: int
    match: Optional[int] = None
    carinfo: str
    state: str
    car_jouken: List[CarCondition]

class cardresponse(BaseModel):
    card: List[DriveItem]

class TimeRange(BaseModel):
    start: str
    end: str

class Conditions(BaseModel):
    nonSmoking: Optional[bool] = None
    petsAllowed: Optional[bool] = None
    foodAllowed: Optional[bool] = None
    musicAllowed: Optional[bool] = None

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
    conditions: Conditions
    isVerifiedOnly: Optional[bool] = None

class Req(BaseModel):
    filter: SearchFilters

# --- ヘルパー関数 ---
def get_coordinates(address: str):
    """LocationIQ APIを使用して座標を取得"""
    import requests
    import time
    import os
    
    if not address or not address.strip():
        return None, None
    
    api_key = os.getenv("LOCATIONIQ_API_KEY", "pk.4c89f676c0053659bd58a6708715b00e")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            url = "https://us1.locationiq.com/v1/search.php"
            params = {
                "key": api_key,
                "q": f"{address}, Japan",
                "format": "json",
                "limit": 1
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                return float(data[0]['lat']), float(data[0]['lon'])
                
        except Exception as e:
            logger.error(f"ジオコーディングエラー ({address}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
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

# --- APIエンドポイント ---
@router.post("/boshukensaku", response_model=cardresponse)
async def search_recruitments(req: Req, request: Request, db: Session = Depends(get_db)):
    logger.info("=== 検索開始（ベクトル類似度マッチング + 自己投稿除外） ===")
    
    # 1. 認証チェック
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Session not found")
    user_id = get_current_user(session_id=session_id, db=db)
    if user_id == "no":
        raise HTTPException(status_code=401, detail="Invalid session")

    # 2. 自分のプロフィールベクトルを取得（マッチング精度計算用）
    my_profile = db.query(modelDB.PassengerProfile).filter(modelDB.PassengerProfile.user_id == user_id).first()
    my_embedding = my_profile.embedding if my_profile else None
    
    if my_embedding is None:
        logger.warning(f"User {user_id} の embedding が見つかりません。デフォルト値を使用します。")

    # 3. 地名から座標を取得
    f = req.filter
    p_start = get_coordinates(f.departure)
    p_end = get_coordinates(f.destination)

    # 4. 基本クエリ作成（ベクトル距離計算を含む）
    if my_embedding is not None:
        # pgvectorを使用してドライバーとの嗜好性の距離を計算
        dist_col = modelDB.DriverProfile.embedding.cosine_distance(my_embedding).label("v_dist")
        query = db.query(modelDB.Recruitment, dist_col)
    else:
        query = db.query(modelDB.Recruitment, cast(0, Numeric).label("v_dist"))

    query = query.join(
        modelDB.Route, 
        modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).join(
        modelDB.DriverProfile,
        modelDB.Recruitment.recruiter_user_id == modelDB.DriverProfile.user_id
    )

    # --- SQLフィルタリング ---
    
    # 【重要】自分の投稿は検索結果から除外する
    query = query.filter(modelDB.Recruitment.recruiter_user_id != user_id)

    # 現在時刻以降の出発便のみ
    query = query.filter(modelDB.Route.dep_time >= datetime.now())

    # 運賃・座席数のフィルタ
    if f.priceRange.min is not None:
        query = query.filter(modelDB.Recruitment.fare >= f.priceRange.min)
    if f.priceRange.max is not None:
        query = query.filter(modelDB.Recruitment.fare <= f.priceRange.max)
    query = query.filter(modelDB.Recruitment.capacity >= f.seats)

    # 日付フィルタ（YYYY-MM-DD形式）
    if f.date:
        try:
            target_date = datetime.strptime(f.date, '%Y-%m-%d').date()
            query = query.filter(cast(modelDB.Route.dep_time, Date) == target_date)
        except ValueError:
            logger.warning(f"不正な日付形式: {f.date}")

    # 出発時間帯のフィルタ
    if f.timeRange and (f.timeRange.start != "00:00" or f.timeRange.end != "23:59"):
        start_hour = int(f.timeRange.start.split(":")[0])
        end_hour = int(f.timeRange.end.split(":")[0])
        query = query.filter(extract('hour', modelDB.Route.dep_time).between(start_hour, end_hour))

    # ステータス固定条件（募集中=0、通常募集=0）
    query = query.filter(modelDB.Recruitment.status == 0, modelDB.Recruitment.type == 0)

    # 車両内条件のフィルタ
    c = f.conditions
    if c.nonSmoking: query = query.filter(modelDB.DriverProfile.no_smoking == True)
    if c.petsAllowed: query = query.filter(modelDB.DriverProfile.pet_ok == True)
    if c.foodAllowed: query = query.filter(modelDB.DriverProfile.food_ok == True)
    if c.musicAllowed: query = query.filter(modelDB.DriverProfile.music_ok == True)

    # 嗜好性が近い順（ベクトル距離昇順）にソート
    if my_embedding is not None:
        query = query.order_by(asc("v_dist"))

    sql_results = query.all()
    logger.info(f"SQLフィルタリング完了: {len(sql_results)} 件ヒット（自己投稿除外済み）")

    response_cards = []

    # --- Python側での詳細解析（経路方向チェック・スコアリング） ---
    for r, v_dist in sql_results:
        current_dist = float(v_dist) if v_dist is not None else None
        
        route_info = db.query(modelDB.Route).filter(modelDB.Route.route_id == r.route_id).first()
        user_info = db.query(modelDB.User).filter(modelDB.User.user_id == r.recruiter_user_id).first()
        driver_info = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == r.recruiter_user_id).first()

        # 経路データのパース
        try:
            path_points = json.loads(route_info.path_data) if route_info and route_info.path_data else []
        except:
            path_points = []

        if not path_points and route_info:
            path_points = [
                [float(route_info.dep_latitude), float(route_info.dep_longitude)],
                [float(route_info.arr_latitude), float(route_info.arr_longitude)]
            ]

        # 経路の進行方向チェック（逆走防止）
        is_order_ok = True
        if p_start[0] is not None and p_end[0] is not None:
            _, idx_start = get_min_distance_to_path(p_start, path_points)
            _, idx_end = get_min_distance_to_path(p_end, path_points)
            # 乗車地点が降車地点より前にあること
            is_order_ok = (idx_start < idx_end)

        if not is_order_ok:
            logger.info(f"Skip: {user_info.name if user_info else 'Unknown'} - 進行方向不一致")
            continue

        # マッチスコア計算 (0-100)
        # コサイン距離(0〜2)を反転させてパーセント化
        if current_dist is not None:
            vector_match_score = max(0, min(100, (1 - current_dist) * 100))
        else:
            vector_match_score = 50

        # ドライバー情報の構築
        driver_name = user_info.name if user_info else "不明なユーザー"
        
        current_car_jouken = []
        if driver_info:
            if driver_info.no_smoking: current_car_jouken.append(CarCondition(jouken_name="禁煙"))
            if driver_info.pet_ok: current_car_jouken.append(CarCondition(jouken_name="ペット可"))
            if driver_info.food_ok: current_car_jouken.append(CarCondition(jouken_name="飲食OK"))
            if driver_info.music_ok: current_car_jouken.append(CarCondition(jouken_name="音楽OK"))

        response_cards.append(DriveItem(
            id=str(r.recruitment_id),
            name=driver_name,
            start=route_info.depname if route_info else "不明",
            end=route_info.arrname if route_info else "不明",
            date=route_info.dep_time.strftime('%Y-%m-%d %H:%M') if route_info else "",
            money=r.fare,
            people=r.capacity,
            match=int(vector_match_score),
            carinfo=f"{driver_info.car_model} ({driver_info.car_color})" if driver_info else "登録なし",
            state="募集中",
            car_jouken=current_car_jouken 
        ))

    logger.info(f"最終レスポンス件数: {len(response_cards)} 件")
    return cardresponse(card=response_cards)