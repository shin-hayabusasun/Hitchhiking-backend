import logging
import sys
import os
from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

# パス解決
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hitchhiker", tags=["MyRequests"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- 1. マイリクエスト一覧 (GET /api/hitchhiker/my-requests) ---
@router.get("/my-requests")
async def get_my_requests(request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    user_id_res = get_current_user(session_id=session_id, db=db)
    if user_id_res == "no": raise HTTPException(status_code=401)
    my_id = int(user_id_res)

    results = db.query(
        modelDB.Application, modelDB.Recruitment, modelDB.Route,
        modelDB.User, modelDB.DriverProfile
    ).join(modelDB.Recruitment, modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id)\
     .join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
     .join(modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id)\
     .outerjoin(modelDB.DriverProfile, modelDB.User.user_id == modelDB.DriverProfile.user_id)\
     .filter(modelDB.Application.applicant_user_id == my_id).all()

    requesting, approved, completed = [], [], []

    for app, recruit, route, user, prof in results:
        item = {
            "id": app.application_id,
            "recruitmentId": recruit.recruitment_id,
            "name": user.name,
            "date": route.dep_time.strftime("%Y-%m-%d"),
            "rating": float(prof.rating) if prof else 0.0,
            "reviews": prof.drive_count if prof else 0,
            "from_loc": route.depname,
            "to_loc": route.arrname,
            "time": route.dep_time.strftime("%H:%M"),
            "price": recruit.fare
        }
        if app.status == 0: requesting.append(item)
        elif app.status == 1:
            if recruit.status == 2: completed.append(item)
            else: approved.append(item)

    return {"success": True, "data": {"requesting": requesting, "approved": approved, "completed": completed}}

# --- 2. 特定のドライブ詳細 (GET /api/hitchhiker/drives/{id}) ---
# 参考APIの構造を完全に網羅
@router.get("/drives/{id}")
async def get_drive_detail(id: int, db: Session = Depends(get_db)):
    drive = db.query(modelDB.Recruitment).filter(modelDB.Recruitment.recruitment_id == id).first()
    if not drive: raise HTTPException(status_code=404, detail="Drive not found")

    driver = db.query(modelDB.User).filter(modelDB.User.user_id == drive.recruiter_user_id).first()
    route = db.query(modelDB.Route).filter(modelDB.Route.route_id == drive.route_id).first()
    profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == drive.recruiter_user_id).first()

    status_map = {0: "募集中", 1: "募集終了", 2: "運転完了"}

    return {
        "drive": {
            "id": str(drive.recruitment_id),
            "driverName": getattr(driver, 'name', "不明"),
            "departure": getattr(route, 'depname', "不明"),
            "destination": getattr(route, 'arrname', "不明"),
            "departureTime": route.dep_time.strftime("%Y-%m-%d %H:%M") if route else "",
            "fee": drive.fare,
            "capacity": drive.capacity,
            "status": status_map.get(drive.status, "不明"),
            "vehicle": {
                "model": getattr(profile, 'car_model', "未設定"),
                "color": getattr(profile, 'car_color', "-"),
                "year": getattr(profile, 'car_year', "-"),
                "number": getattr(profile, 'car_number', "-")
            },
            "driverProfile": {
                "rating": float(getattr(profile, 'rating', 0.0)),
                "reviewCount": int(getattr(profile, 'drive_count', 0)),
                "bio": getattr(profile, 'bio', "よろしくお願いします！")
            },
            "vehicleRules": {
                "noSmoking": bool(getattr(profile, 'no_smoking', True)),
                "petAllowed": bool(getattr(profile, 'pet_ok', False)),
                "musicAllowed": bool(getattr(profile, 'music_ok', True))
            }
        }
    }

# --- 3. 申請取り消し (DELETE /api/hitchhiker/cancel-request/{id}) ---
@router.delete("/cancel-request/{id}")
async def cancel_request(id: int, request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    res = get_current_user(session_id, db)
    if res == "no": raise HTTPException(status_code=401)
    
    app = db.query(modelDB.Application).filter(
        modelDB.Application.application_id == id,
        modelDB.Application.applicant_user_id == int(res)
    ).first()

    if not app: raise HTTPException(status_code=404)
    db.delete(app)
    db.commit()
    return {"success": True}