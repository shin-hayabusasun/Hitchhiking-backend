from fastapi import APIRouter, Depends, HTTPException, Request, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sys
import time
from geopy.geocoders import Nominatim

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

def get_location_name(lat, lon) -> str:
    """LocationIQ APIを使用して逆ジオコーディング（座標→住所）"""
    import requests
    import os
    
    if lat is None or lon is None:
        return "場所情報なし"
    
    api_key = os.getenv("LOCATIONIQ_API_KEY", "pk.4c89f676c0053659bd58a6708715b00e")
    
    try:
        url = "https://us1.locationiq.com/v1/reverse.php"
        params = {
            "key": api_key,
            "lat": lat,
            "lon": lon,
            "format": "json",
            "accept-language": "ja"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and 'address' in data:
            addr = data['address']
            city = addr.get('city', addr.get('town', addr.get('village', '')))
            road = addr.get('road', '')
            state = addr.get('province', addr.get('state', ''))
            if city and road:
                return f"{city} {road}"
            return state + city
    except Exception:
        pass
    
    return f"地点({lat}, {lon})"

# ---------------------------------------------------------
# Pydantic Models (Response)
# ---------------------------------------------------------
class PassengerInfo(BaseModel):
    id: int
    name: str
    status: str

class VehicleRules(BaseModel):
    noSmoking: bool
    petAllowed: bool
    musicAllowed: bool
    foodAllowed: bool

class DriveDetailResponse(BaseModel):
    id: int
    driverId: int
    driverName: str
    departure: str
    destination: str
    departureTime: str
    capacity: int
    currentPassengers: int
    fee: int
    message: Optional[str] = None
    vehicleRules: VehicleRules
    status: str
    passengers: List[PassengerInfo]

class DriveDetailWrapper(BaseModel):
    drive: DriveDetailResponse

# ---------------------------------------------------------
# API Endpoint
# ---------------------------------------------------------
@router.get("/drives/{drive_id}", response_model=DriveDetailWrapper)
async def get_drive_detail(
    request: Request,
    drive_id: int = Path(..., title="Drive ID"),
    db: Session = Depends(get_db)
):
    """
    ドライブ詳細取得
    """
    # 1. 認証
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401, detail="Unauthorized")
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no": raise HTTPException(status_code=401, detail="Invalid session")
    user_id = int(user_id_str)

    # 2. ドライブ情報の取得 (自分の募集か確認)
    drive = db.query(modelDB.Recruitment, modelDB.Route).join(
        modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).filter(
        modelDB.Recruitment.recruitment_id == drive_id,
        modelDB.Recruitment.recruiter_user_id == user_id
    ).first()

    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    recruitment, route = drive

    # 3. ドライバープロフィールの取得 (車両ルール)
    driver_profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == user_id
    ).first()

    # 4. ユーザー情報の取得 (名前)
    driver_user = db.query(modelDB.User).filter(
        modelDB.User.user_id == user_id
    ).first()

    # 5. 申請者リストの取得
    applications = db.query(modelDB.Application, modelDB.User).join(
        modelDB.User, modelDB.Application.applicant_user_id == modelDB.User.user_id
    ).filter(
        modelDB.Application.recruitment_id == drive_id
    ).all()

    # 6. データ整形
    # 申請者リスト作成 & 現在の乗車人数カウント(承認済みのみ)
    passengers_list = []
    approved_count = 0
    
    for app, user in applications:
        # ステータス変換 (0:pending, 1:approved, 2:rejected)
        st_str = 'pending'
        if app.status == 1: 
            st_str = 'approved'
            approved_count += 1
        elif app.status == 2: 
            st_str = 'rejected'

        passengers_list.append(PassengerInfo(
            id=user.user_id,
            name=user.name,
            status=st_str
        ))

    # ドライブステータス変換
    status_map = {0: 'recruiting', 1: 'matched', 2: 'completed', 3: 'cancelled'}
    drive_status = status_map.get(recruitment.status, 'unknown')

    # 住所変換 (API制限回避のため待機)
    dep_name = route.depname if route.depname else "出発地未設定"
    des_name = route.arrname if route.arrname else "目的地未設定"

    # レスポンス構築
    response_data = DriveDetailResponse(
        id=recruitment.recruitment_id,
        driverId=user_id,
        driverName=driver_user.name if driver_user else "Unknown",
        departure=dep_name,
        destination=des_name,
        departureTime=route.dep_time.strftime('%Y-%m-%dT%H:%M:%S'),
        capacity=recruitment.capacity,
        currentPassengers=approved_count,
        fee=recruitment.fare,
        vehicleRules=VehicleRules(
            noSmoking=driver_profile.no_smoking if driver_profile else True,
            petAllowed=driver_profile.pet_ok if driver_profile else False,
            musicAllowed=driver_profile.music_ok if driver_profile else True,
            foodAllowed=driver_profile.food_ok if driver_profile else False,
        ),
        status=drive_status,
        passengers=passengers_list
    )

    return DriveDetailWrapper(drive=response_data)