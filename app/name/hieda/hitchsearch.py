import logging
import json
import math
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import extract, cast, Date
from pydantic import BaseModel
from geopy.geocoders import Nominatim

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

# --- Pydanticモデル定義 (NameError回避のため、使用される順序で定義) ---

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
    """地名から座標を取得し、日本国内を優先する"""
    geocoder = Nominatim(user_agent="hitchhiker_app_v2026", timeout=10)
    try:
        location = geocoder.geocode(f"{address}, Japan")
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        logger.error(f"ジオコーディングエラー ({address}): {e}")
        return None, None
    return None, None

def get_min_distance_to_path(point_p, path_points):
    """
    点P(lat, lon) と 経路(path_points) の最小距離(2乗)と、その地点のインデックスを計算
    """
    min_dist_sq = float('inf')
    closest_index = -1
    
    if not path_points or point_p[0] is None:
        return min_dist_sq, closest_index
        
    for i, pt in enumerate(path_points):
        # pt = [lat, lon] の形式を想定
        dist_sq = (point_p[0] - pt[0])**2 + (point_p[1] - pt[1])**2
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            closest_index = i
            
    return min_dist_sq, closest_index

# --- APIエンドポイント ---

@router.post("/boshukensaku", response_model=cardresponse)
async def search_recruitments(req: Req, request: Request, db: Session = Depends(get_db)):
    logger.info("=== 検索デバッグ開始 ===")
    
    # 1. 認証チェック
    session_id = request.cookies.get("session_id")
    if not session_id:
        logger.warning("セッションIDがクッキーにありません")
        raise HTTPException(status_code=401, detail="Session not found")

    user_id = get_current_user(session_id=session_id, db=db)
    if user_id == "no":
        logger.warning(f"無効なセッションIDです: {session_id}")
        raise HTTPException(status_code=401, detail="Invalid session")
    
    logger.info(f"ログインユーザーID: {user_id}")

    # 2. 地名から座標を取得
    f = req.filter
    logger.info(f"入力フィルタ: 出発={f.departure}, 到着={f.destination}, 日付={f.date}")
    
    p_start = get_coordinates(f.departure)
    p_end = get_coordinates(f.destination)
    logger.info(f"取得座標: 出発={p_start}, 到着={p_end}")

    if p_start[0] is None or p_end[0] is None:
        logger.warning("座標の取得に失敗したため、検索を中断します")
        return cardresponse(card=[])

    # 3. 基本クエリ作成
    query = db.query(modelDB.Recruitment).join(
        modelDB.Route, 
        modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).join(
        modelDB.DriverProfile,
        modelDB.Recruitment.recruiter_user_id == modelDB.DriverProfile.user_id
    )
    
    logger.info(f"DB初期全件数: {query.count()}件")

    # --- SQLフィルタリング段階のログ ---
    # ① 運賃
    if f.priceRange.min is not None:
        query = query.filter(modelDB.Recruitment.fare >= f.priceRange.min)
    if f.priceRange.max is not None:
        query = query.filter(modelDB.Recruitment.fare <= f.priceRange.max)
    logger.info(f"運賃フィルタ適用後: {query.count()}件")

    # ② 必要な座席数
    query = query.filter(modelDB.Recruitment.capacity >= f.seats)
    logger.info(f"座席数({f.seats}以上)適用後: {query.count()}件")

    # ③ 日付
    if f.date:
        target_date = datetime.strptime(f.date, '%Y-%m-%d').date()
        query = query.filter(cast(modelDB.Route.dep_time, Date) == target_date)
        logger.info(f"日付({target_date})適用後: {query.count()}件")

    # ④ 時間帯
    if f.timeRange:
        start_hour = int(f.timeRange.start.split(":")[0])
        end_hour = int(f.timeRange.end.split(":")[0])
        query = query.filter(extract('hour', modelDB.Route.dep_time).between(start_hour, end_hour))
        logger.info(f"時間帯({start_hour}-{end_hour}時)適用後: {query.count()}件")

    # ⑤ 状態・タイプ (募集中=1, 運転者からの募集=0)
    query = query.filter(modelDB.Recruitment.status == 1)
    query = query.filter(modelDB.Recruitment.type == 0)
    logger.info(f"ステータス(募集中/運転者)適用後: {query.count()}件")

    # ⑥ 車両条件
    c = f.conditions
    conditions_list = [
        (c.nonSmoking, modelDB.DriverProfile.no_smoking, "禁煙"),
        (c.petsAllowed, modelDB.DriverProfile.pet_ok, "ペット"),
        (c.foodAllowed, modelDB.DriverProfile.food_ok, "飲食"),
        (c.musicAllowed, modelDB.DriverProfile.music_ok, "音楽"),
    ]
    for filter_val, db_column, label in conditions_list:
        if filter_val: # Trueの場合のみ絞り込む
            query = query.filter(db_column == True)
            logger.info(f"車両条件({label})適用後: {query.count()}件")

    # --- Python側での詳細な経路解析 ---
    sql_results = query.all()
    response_cards = []

    for r in sql_results:
        # 関連情報の取得
        route_info = db.query(modelDB.Route).filter(modelDB.Route.route_id == r.route_id).first()
        user_info = db.query(modelDB.User).filter(modelDB.User.user_id == r.recruiter_user_id).first()
        driver_info = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == r.recruiter_user_id).first()

        # 経路データ(path_data)のデコード
        try:
            path_points = json.loads(route_info.path_data) if route_info.path_data else []
        except:
            path_points = []

        if not path_points:
            path_points = [
                [float(route_info.dep_latitude), float(route_info.dep_longitude)],
                [float(route_info.arr_latitude), float(route_info.arr_longitude)]
            ]

        # 経路の類似性と近傍判定
        dist_start_sq, idx_start = get_min_distance_to_path(p_start, path_points)
        dist_end_sq, idx_end = get_min_distance_to_path(p_end, path_points)

        # 順序チェック
        is_order_ok = idx_start < idx_end
        
        # マッチスコア計算 (ユークリッド距離合計に基づく)
        dist_total = math.sqrt(dist_start_sq) + math.sqrt(dist_end_sq)
        similarity_score = 100 - (dist_total * 1000)
        
        # 各募集の詳細デバッグログ
        log_prefix = f"[Recruitment ID: {r.recruitment_id} / Driver: {user_info.name if user_info else '??'}]"
        logger.info(f"{log_prefix} Score: {similarity_score:.2f}, StartIdx: {idx_start}, EndIdx: {idx_end}, Order: {is_order_ok}")

        # 判定
        if not is_order_ok:
            logger.info(f"  -> 除外: 通過順序が不正です (Start:{idx_start} >= End:{idx_end})")
            continue
        if similarity_score < 60:
            logger.info(f"  -> 除外: スコア不足 ({similarity_score:.2f} < 60)")
            continue

        logger.info(f"  -> 採用！")

        # 車両条件ラベル
        current_car_jouken = []
        if driver_info:
            if driver_info.no_smoking: current_car_jouken.append(CarCondition(jouken_name="禁煙"))
            if driver_info.pet_ok: current_car_jouken.append(CarCondition(jouken_name="ペット可"))
            if driver_info.food_ok: current_car_jouken.append(CarCondition(jouken_name="飲食OK"))
            if driver_info.music_ok: current_car_jouken.append(CarCondition(jouken_name="音楽OK"))

        response_cards.append(DriveItem(
            id=str(r.recruitment_id),
            name=user_info.name if user_info else "不明なユーザー",
            start=route_info.depname,
            end=route_info.arrname,
            date=route_info.dep_time.strftime('%Y-%m-%d %H:%M') if route_info else "",
            money=r.fare,
            people=r.capacity,
            match=int(similarity_score),
            carinfo=f"{driver_info.car_model} ({driver_info.car_color})" if driver_info else "登録車両なし",
            state="募集中",
            car_jouken=current_car_jouken 
        ))

    # スコア順にソート
    response_cards.sort(key=lambda x: x.match if x.match else 0, reverse=True)
    logger.info(f"=== 最終返却件数: {len(response_cards)}件 ===")

    return cardresponse(card=response_cards)