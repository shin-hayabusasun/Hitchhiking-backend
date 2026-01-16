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
    
    try:
        # Application削除前に、関連するChatのapplication_idをNULLにする
        db.query(modelDB.Chat).filter(
            modelDB.Chat.application_id == id
        ).update({modelDB.Chat.application_id: None}, synchronize_session=False)
        
        # Applicationを削除
        db.delete(app)
        db.commit()
        return {"success": True}
    
    except Exception as e:
        db.rollback()
        logger.error(f"削除エラー: {e}")
        raise HTTPException(status_code=500, detail="削除に失敗しました")