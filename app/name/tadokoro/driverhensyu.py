import sys
import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from geopy.geocoders import Nominatim

# パス設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/kaito/drives", tags=["kaito_driver_edit"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_coordinates(address: str):
    """LocationIQ APIを使用して座標を取得"""
    import requests
    import logging
    import time
    import os
    
    logger = logging.getLogger(__name__)
    
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
            logger.error(f"Geocoding error: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
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
    except Exception as e:
        print(f"経路探索エラー: {e}")
    return [[start_lat, start_lon], [end_lat, end_lon]], 10800

# --- スキーマ定義 ---
class VehicleRules(BaseModel):
    noSmoking: bool
    petAllowed: bool
    musicAllowed: bool
    foodAllowed: bool

class DriveDetailData(BaseModel):
    departure: str
    destination: str
    departureTime: str
    capacity: int
    fee: int
    message: str
    vehicleRules: VehicleRules

class DriveDetailResponse(BaseModel):
    ok: bool
    drive: Optional[DriveDetailData] = None

class DriveUpdateData(BaseModel):
    departure: str
    destination: str
    departureTime: str
    capacity: int
    fee: int
    message: Optional[str] = ""
    noSmoking: bool
    petAllowed: bool
    musicAllowed: bool
    foodAllowed: bool

class CommonResponse(BaseModel):
    ok: bool
    detail: Optional[str] = None

# --- APIエンドポイント ---

@router.get("/{drive_id}", response_model=DriveDetailResponse)
async def get_drive_detail(drive_id: int, request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        return DriveDetailResponse(ok=False)
    
    user_id = int(res)
    
    result = db.query(modelDB.Recruitment, modelDB.Route, modelDB.DriverProfile)\
        .join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
        .join(modelDB.DriverProfile, modelDB.Recruitment.recruiter_user_id == modelDB.DriverProfile.user_id)\
        .filter(modelDB.Recruitment.recruitment_id == drive_id)\
        .filter(modelDB.Recruitment.recruiter_user_id == user_id)\
        .first()

    if not result:
        return DriveDetailResponse(ok=False)

    rec, route, prof = result
    
    return DriveDetailResponse(
        ok=True,
        drive=DriveDetailData(
            departure=route.depname or "", # 地名反映
            destination=route.arrname or "", # 地名反映
            departureTime=route.dep_time.strftime("%Y-%m-%dT%H:%M"),
            capacity=rec.capacity,
            fee=rec.fare,
            message=prof.bio or "",
            vehicleRules=VehicleRules(
                noSmoking=prof.no_smoking,
                petAllowed=prof.pet_ok,
                musicAllowed=prof.music_ok,
                foodAllowed=prof.food_ok
            )
        )
    )

@router.put("/{drive_id}", response_model=CommonResponse)
async def update_drive(drive_id: int, data: DriveUpdateData, request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        return CommonResponse(ok=False, detail="Unauthorized")
    
    user_id = int(res)
    rec = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == drive_id,
        modelDB.Recruitment.recruiter_user_id == user_id
    ).first()

    if not rec:
        return CommonResponse(ok=False, detail="募集が見つかりません")

    dep_lat, dep_lon = get_coordinates(data.departure)
    arr_lat, arr_lon = get_coordinates(data.destination)
    if dep_lat is None or arr_lat is None:
        return CommonResponse(ok=False, detail="地点の特定に失敗しました")

    path_points, duration_sec = get_actual_route(dep_lat, dep_lon, arr_lat, arr_lon)

    try:
        dep_dt = datetime.strptime(data.departureTime, "%Y-%m-%dT%H:%M")
        arr_dt = dep_dt + timedelta(seconds=duration_sec)
        
        route = db.query(modelDB.Route).filter(modelDB.Route.route_id == rec.route_id).first()
        if route:
            route.path_data = json.dumps(path_points)
            route.dep_time = dep_dt
            route.dep_latitude = dep_lat
            route.dep_longitude = dep_lon
            route.arr_time = arr_dt
            route.arr_latitude = arr_lat
            route.arr_longitude = arr_lon
            route.depname = data.departure # 地名更新
            route.arrname = data.destination # 地名更新

        rec.fare = data.fee
        rec.capacity = data.capacity

        prof = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == user_id).first()
        if prof:
            prof.no_smoking = data.noSmoking
            prof.pet_ok = data.petAllowed
            prof.music_ok = data.musicAllowed
            prof.food_ok = data.foodAllowed
            prof.bio = data.message

        db.commit()
        return CommonResponse(ok=True)
    except Exception as e:
        db.rollback()
        return CommonResponse(ok=False, detail=str(e))

@router.delete("/{drive_id}", response_model=CommonResponse)
async def delete_drive(drive_id: int, request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    res = get_current_user(session_id=session_id, db=db)
    if res == "no": return CommonResponse(ok=False)

    rec = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == drive_id,
        modelDB.Recruitment.recruiter_user_id == int(res)
    ).first()

    if rec:
        rec.status = 9 # 論理削除
        db.commit()
        return CommonResponse(ok=True)
    return CommonResponse(ok=False)