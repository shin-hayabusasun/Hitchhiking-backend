# % Start(AI Assistant)
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from geopy.geocoders import Nominatim

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

def get_coordinates(address: str):
    geocoder = Nominatim(user_agent="drive_app_v2026", timeout=10)
    try:
        location = geocoder.geocode(f"{address}, Japan")
        if location:
            return location.latitude, location.longitude
    except:
        return None, None
    return None, None

def get_actual_route(start_lat, start_lon, end_lat, end_lon):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get('code') == 'Ok':
            coords = data['routes'][0]['geometry']['coordinates']
            path_points = [[c[1], c[0]] for c in coords]
            duration = data['routes'][0]['duration']
            return path_points, duration
    except:
        pass
    return [[start_lat, start_lon], [end_lat, end_lon]], 10800

# スキーマ
class VehicleRules(BaseModel):
    noSmoking: bool
    petAllowed: bool
    foodAllowed: bool
    musicAllowed: bool

class DriveCreateRequest(BaseModel):
    departure: str
    destination: str
    departureDate: str
    departureTime: str
    capacity: int
    fee: int
    message: str
    vehiclerules: VehicleRules

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

    # 2. 座標と経路の計算
    dep_lat, dep_lon = get_coordinates(data.departure)
    arr_lat, arr_lon = get_coordinates(data.destination)
    if dep_lat is None or arr_lat is None:
        raise HTTPException(status_code=400, detail="地点の座標取得に失敗しました")

    path_points, duration_sec = get_actual_route(dep_lat, dep_lon, arr_lat, arr_lon)
    
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
            arr_longitude=arr_lon
        )
        db.add(new_route)
        db.flush()

        # 4. DriverProfile(車両ルール等)の更新
        # 既存のプロフィールがあるか確認し、ルールを更新する
        profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == user_id).first()
        if profile:
            profile.no_smoking = data.vehiclerules.noSmoking
            profile.pet_ok = data.vehiclerules.petAllowed
            profile.food_ok = data.vehiclerules.foodAllowed
            profile.music_ok = data.vehiclerules.musicAllowed
            # 募集時の現在地として出発地を保存（任意）
            profile.latitude = dep_lat
            profile.longitude = dep_lon
        
        # 5. Recruitment(募集)の登録
        # あなたのモデル定義に合わせて type=0(運転者) で登録
        new_rec = modelDB.Recruitment(
            recruiter_user_id=user_id,
            status=0, # 0: 募集中
            fare=data.fee,
            capacity=data.capacity,
            type=0,   # 0: 運転者からの募集
            route_id=new_route.route_id
        )
        db.add(new_rec)
        db.commit()

        return DriveResponse(ok=True, recruitment_id=new_rec.recruitment_id)

    except Exception as e:
        db.rollback()
        print(f"DEBUG ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"DB登録失敗: {str(e)}")
# % End