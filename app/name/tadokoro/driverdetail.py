from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import sys

sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/drives", tags=["drives"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 型定義 ---
class VehicleRules(BaseModel):
    noSmoking: bool = False
    petAllowed: bool = False
    musicAllowed: bool = False
    foodAllowed: bool = False

class Passenger(BaseModel):
    id: int
    name: str
    status: str

class DriveDetailResponse(BaseModel):
    id: int
    driverId: int
    driverName: str
    departure: str
    destination: str
    departureTime: datetime
    capacity: int
    currentPassengers: int
    fee: int
    message: Optional[str] = None
    vehicleRules: VehicleRules
    status: str
    passengers: List[Passenger]

class DriveDetailWrapper(BaseModel):
    drive: DriveDetailResponse

class ApplyResponse(BaseModel):
    ok: bool
    message: str

# --- GET: ドライブ詳細 ---
@router.get("/{drive_id}", response_model=DriveDetailWrapper)
async def get_drive_detail(drive_id: int, request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Session expired")

    drive_data = db.query(modelDB.Recruitment, modelDB.Route, modelDB.DriverProfile, modelDB.User).\
        join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id).\
        join(modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id).\
        join(modelDB.DriverProfile, modelDB.User.user_id == modelDB.DriverProfile.user_id).\
        filter(modelDB.Recruitment.recruitment_id == drive_id).first()

    if not drive_data:
        raise HTTPException(status_code=404, detail="Drive not found")

    recruitment, route, driver_profile, driver_user = drive_data

    # 同乗者情報の取得
    applications = db.query(modelDB.Application, modelDB.User).\
        join(modelDB.User, modelDB.Application.applicant_user_id == modelDB.User.user_id).\
        filter(modelDB.Application.recruitment_id == drive_id).all()

    passenger_list = []
    approved_count = 0
    for app, p_user in applications:
        p_status = "approved" if app.status == 1 else "pending"
        if app.status == 1: approved_count += 1
        passenger_list.append(Passenger(id=app.application_id, name=p_user.name, status=p_status))

    return DriveDetailWrapper(
        drive=DriveDetailResponse(
            id=recruitment.recruitment_id,
            driverId=driver_user.user_id,
            driverName=driver_user.name,
            departure=route.depname,
            destination=route.arrname,
            departureTime=route.dep_time,
            capacity=recruitment.capacity,
            currentPassengers=approved_count,
            fee=recruitment.fare,
            message=driver_profile.bio,
            vehicleRules=VehicleRules(
                noSmoking=driver_profile.no_smoking or False,
                petAllowed=driver_profile.pet_ok or False,
                musicAllowed=driver_profile.music_ok or False,
                foodAllowed=driver_profile.food_ok or False
            ),
            status="active",
            passengers=passenger_list
        )
    )

# --- POST: 相乗り申請 ---
@router.post("/{drive_id}/apply", response_model=ApplyResponse)
async def apply_for_drive(drive_id: int, request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Session expired")
    
    my_id = int(res)

    try:
        new_app = modelDB.Application(
            recruitment_id=drive_id,
            applicant_user_id=my_id,
            status=0,   # 0: 申請中
            chat_id=0   # 暫定（NotNull制約対策。DB修正後は不要）
        )
        db.add(new_app)
        db.commit()
        return ApplyResponse(ok=True, message="Success")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))