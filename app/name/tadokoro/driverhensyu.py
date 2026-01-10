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

# パス設定（上位ディレクトリのdb_setting等を参照可能に）
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

# フロントエンドの fetch(`/api/kaito/drives/${driveId}`) に完全に合わせる
router = APIRouter(prefix="/api/kaito/drives", tags=["kaito_driver_edit"])

# --- ヘルパー関数 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_coordinates(address: str):
    geocoder = Nominatim(user_agent="hitchhiker_app_v2026", timeout=10)
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
    except Exception as e:
        print(f"経路探索エラー: {e}")
    return [[start_lat, start_lon], [end_lat, end_lon]], 10800

# --- テンプレ準拠：レスポンス・リクエストの型定義 ---

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

# --- API処理 ---

# 1. 編集画面の初期データ取得 (GET)
@router.get("/{drive_id}", response_model=DriveDetailResponse)
async def get_drive_detail(drive_id: int, request: Request, db: Session = Depends(get_db)):
    # クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")
    # セッションが有効か見る（hiedaさんの関数を使用）
    res = get_current_user(session_id=session_id, db=db)
    
    if res == "no":
        return DriveDetailResponse(ok=False)
    
    user_id = int(res)
    
    # 募集、経路、ドライバープロフィールを結合して取得
    result = db.query(modelDB.Recruitment, modelDB.Route, modelDB.DriverProfile)\
        .join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
        .join(modelDB.DriverProfile, modelDB.Recruitment.recruiter_user_id == modelDB.DriverProfile.user_id)\
        .filter(modelDB.Recruitment.recruitment_id == drive_id)\
        .filter(modelDB.Recruitment.recruiter_user_id == user_id)\
        .first()

    if not result:
        return DriveDetailResponse(ok=False)

    rec, route, prof = result
    
    # フロントエンドが期待する構造に整形して返却
    return DriveDetailResponse(
        ok=True,
        drive=DriveDetailData(
            departure=f"{route.dep_latitude}, {route.dep_longitude}",
            destination=f"{route.arr_latitude}, {route.arr_longitude}",
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

# 2. 編集内容の保存 (PUT)
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
        return CommonResponse(ok=False, detail="Recruitment not found")

    # 座標再取得
    dep_lat, dep_lon = get_coordinates(data.departure)
    arr_lat, arr_lon = get_coordinates(data.destination)
    if dep_lat is None or arr_lat is None:
        return CommonResponse(ok=False, detail="座標取得失敗")

    path_points, duration_sec = get_actual_route(dep_lat, dep_lon, arr_lat, arr_lon)

    try:
        dep_dt = datetime.strptime(data.departureTime, "%Y-%m-%dT%H:%M")
        arr_dt = dep_dt + timedelta(seconds=duration_sec)
        
        # Route情報を更新
        route = db.query(modelDB.Route).filter(modelDB.Route.route_id == rec.route_id).first()
        if route:
            route.path_data = json.dumps(path_points)
            route.dep_time = dep_dt
            route.dep_latitude = dep_lat
            route.dep_longitude = dep_lon
            route.arr_time = arr_dt
            route.arr_latitude = arr_lat
            route.arr_longitude = arr_lon

        # Recruitment情報を更新
        rec.fare = data.fee
        rec.capacity = data.capacity

        # プロフィール（車内ルール等）を更新
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

# 3. 募集の削除 (DELETE)
@router.delete("/{drive_id}", response_model=CommonResponse)
async def delete_drive(drive_id: int, request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        return CommonResponse(ok=False)

    rec = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == drive_id,
        modelDB.Recruitment.recruiter_user_id == int(res)
    ).first()

    if rec:
        rec.status = 9 # 論理削除
        db.commit()
        return CommonResponse(ok=True)
    return CommonResponse(ok=False)