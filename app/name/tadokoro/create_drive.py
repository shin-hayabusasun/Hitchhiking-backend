import sys
import json
import requests
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/driver", tags=["drive_management"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_coordinates(address: str):
    """LocationIQ APIを使用して座標を取得（非同期版）"""
    import logging
    import asyncio
    import os
    
    logger = logging.getLogger(__name__)
    
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
                    
            except Exception as e:
                logger.error(f"Geocoding error: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
    
    return None, None

async def get_actual_route(start_lat, start_lon, end_lat, end_lon):
    """OSRM APIを使用して実際の道路に沿った経路と所要時間を取得（非同期版）"""
    import logging
    logger = logging.getLogger(__name__)
    
    max_retries = 3
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                url = f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                if data.get('code') == 'Ok':
                    coords = data['routes'][0]['geometry']['coordinates']
                    path_points = [[c[1], c[0]] for c in coords]
                    duration = data['routes'][0]['duration']
                    logger.info(f"OSRM route success: {len(path_points)} points, {duration}s")
                    return path_points, duration
            except Exception as e:
                logger.error(f"OSRM error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
    
        logger.warning(f"OSRM failed, using fallback route")
        return [[start_lat, start_lon], [end_lat, end_lon]], 10800

# スキーマ
class DriveCreateRequest(BaseModel):
    departure: str      # 地名
    destination: str    # 地名
    departureDate: str
    departureTime: str
    capacity: int
    fee: int
    message: str

class DriveResponse(BaseModel):
    ok: bool
    recruitment_id: Optional[int] = None

@router.post("/regist_drive", response_model=DriveResponse)
async def regist_drive(data: DriveCreateRequest, request: Request, db: Session = Depends(get_db)):
    # 1. セッション確認
    session_id = request.cookies.get("session_id")
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="ログインが必要です")
    
    user_id = int(res)

    # 2. 座標と経路の計算（並列実行）
    dep_coords, arr_coords = await asyncio.gather(
        get_coordinates(data.departure),
        get_coordinates(data.destination)
    )
    dep_lat, dep_lon = dep_coords
    arr_lat, arr_lon = arr_coords
    
    if dep_lat is None or arr_lat is None:
        raise HTTPException(status_code=400, detail="地点の座標特定に失敗しました。具体的な住所や駅名を入力してください。")

    path_points, duration_sec = await get_actual_route(dep_lat, dep_lon, arr_lat, arr_lon)
    
    try:
        dep_dt = datetime.strptime(f"{data.departureDate} {data.departureTime}", "%Y-%m-%d %H:%M")
        arr_dt = dep_dt + timedelta(seconds=duration_sec)

        # 3. Route(経路)の登録
        new_route = modelDB.Route(
            recruiter_user_id=user_id,
            path_data=json.dumps(path_points),
            dep_time=dep_dt,
            dep_latitude=dep_lat,
            dep_longitude=dep_lon,
            arr_time=arr_dt,
            arr_latitude=arr_lat,
            arr_longitude=arr_lon,
            depname=data.departure,
            arrname=data.destination
        )
        db.add(new_route)
        db.flush()

        # 4. プロフィール情報の取得とメッセージ(bio)の更新
        profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == user_id).first()
        
        if profile:
            # 入力された message を bio (紹介文) として更新する
            profile.bio = data.message
        else:
            # プロフィールが存在しない場合は新規作成
            new_profile = modelDB.DriverProfile(
                user_id=user_id,
                bio=data.message,
                rating=5.0,
                drive_count=0,
                car_model="トヨタ プリウス", # 初期値が必要な場合
                car_color="白",
                car_year="2022年",
                car_number="品川 300 あ 12-34"
            )
            db.add(new_profile)

        # 5. Recruitment(募集)の登録
        new_rec = modelDB.Recruitment(
            recruiter_user_id=user_id,
            status=0,   # 0: 募集中
            fare=data.fee,
            capacity=data.capacity,
            type=0,     # 0: 運転者からの募集
            route_id=new_route.route_id
        )
        db.add(new_rec)
        db.commit()

        return DriveResponse(ok=True, recruitment_id=new_rec.recruitment_id)

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"DB登録失敗: {str(e)}")
    
# スキーマの追加（詳細取得レスポンス用）
class DriveDetailResponse(BaseModel):
    departure: str
    destination: str
    departure_time: str  # HTMLの datetime-local 用に文字列で返す
    capacity: int
    fee: int
    message: str = ""
    # 車両ルール（プロフィールから取得）
    no_smoking: bool
    pet_allowed: bool
    music_allowed: bool
    food_allowed: bool

# 1. 募集詳細の取得 (GET)
@router.get("/schedules/{recruitment_id}", response_model=DriveDetailResponse)
async def get_drive_detail(
    recruitment_id: int, 
    request: Request, 
    db: Session = Depends(get_db)
):
    # ユーザー認証
    session_id = request.cookies.get("session_id")
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Unauthorized")
    my_id = int(user_id_str)

    # データの取得
    rec = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == recruitment_id,
        modelDB.Recruitment.recruiter_user_id == my_id
    ).first()

    if not rec:
        raise HTTPException(status_code=404, detail="募集が見つかりません")

    route = db.query(modelDB.Route).filter(modelDB.Route.route_id == rec.route_id).first()
    profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == my_id).first()

    return DriveDetailResponse(
        departure=route.depname if route else "",
        destination=route.arrname if route else "",
        # フロントの datetime-local 形式 (YYYY-MM-DDTHH:mm) に変換
        departure_time=route.dep_time.strftime("%Y-%m-%dT%H:%M") if route else "",
        capacity=rec.capacity,
        fee=rec.fare,
        message="", # 必要に応じてテーブルに追加してください
        no_smoking=profile.no_smoking if profile else True,
        pet_allowed=profile.pet_ok if profile else False,
        music_allowed=profile.music_ok if profile else True,
        food_allowed=profile.food_ok if profile else True
    )

# 2. 募集情報の更新 (PUT)
@router.put("/schedules/{recruitment_id}")
async def update_drive(
    recruitment_id: int, 
    data: DriveCreateRequest, # regist_driveと同じスキーマを再利用
    request: Request, 
    db: Session = Depends(get_db)
):
    session_id = request.cookies.get("session_id")
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Unauthorized")
    my_id = int(user_id_str)

    # 既存データの確認
    rec = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == recruitment_id,
        modelDB.Recruitment.recruiter_user_id == my_id
    ).first()

    if not rec:
        raise HTTPException(status_code=404, detail="対象の募集が見つかりません")

    route = db.query(modelDB.Route).filter(modelDB.Route.route_id == rec.route_id).first()

    try:
        # 地点が変更されている場合は座標と経路を再計算
        if route.depname != data.departure or route.arrname != data.destination:
            # 座標取得（並列実行）
            dep_coords, arr_coords = await asyncio.gather(
                get_coordinates(data.departure),
                get_coordinates(data.destination)
            )
            dep_lat, dep_lon = dep_coords
            arr_lat, arr_lon = arr_coords
            path_points, duration_sec = await get_actual_route(dep_lat, dep_lon, arr_lat, arr_lon)
            
            route.dep_latitude = dep_lat
            route.dep_longitude = dep_lon
            route.arr_latitude = arr_lat
            route.arr_longitude = arr_lon
            route.path_data = json.dumps(path_points)
            route.depname = data.departure
            route.arrname = data.destination
        else:
            # 時間計算のみ（地名が変わっていない場合でも時間は変わる可能性があるため）
            _, duration_sec = await get_actual_route(route.dep_latitude, route.dep_longitude, route.arr_latitude, route.arr_longitude)

        # 時間の更新
        dep_dt = datetime.strptime(f"{data.departureDate} {data.departureTime}", "%Y-%m-%d %H:%M")
        route.dep_time = dep_dt
        route.arr_time = dep_dt + timedelta(seconds=duration_sec)

        # 募集情報の更新
        rec.fare = data.fee
        rec.capacity = data.capacity

        db.commit()
        return {"ok": True, "message": "更新が完了しました"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失敗: {str(e)}")