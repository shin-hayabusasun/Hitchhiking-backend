from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/driver", tags=["progress"])

# --- レスポンス用スキーマ ---
class DriverInfo(BaseModel):
    name: str
    rating: float
    driveCount: int

class ProgressDriveItem(BaseModel):
    id: str
    from_loc: str
    to_loc: str
    datetime: str
    price: int
    driver: DriverInfo  # UI上のラベルはdriverですが、中身は「相手」の情報

class ProgressResponse(BaseModel):
    drives: List[ProgressDriveItem]

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.get("/progress", response_model=ProgressResponse)
async def get_progress_drives(request: Request, db: Session = Depends(get_db)):
    # 1. セッション確認
    session_id = request.cookies.get("session_id")
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    my_id = int(user_id_str)

    response_list = []

    # パターンA: 自分が「運転者（募集者）」の場合
    # Recruitment.status=1(募集終了) かつ Application.status=1(承認済) の同乗者情報を取得
    driver_side = db.query(
        modelDB.Recruitment,
        modelDB.Route,
        modelDB.Application,
        modelDB.User,
        modelDB.PassengerProfile
    ).join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
     .join(modelDB.Application, modelDB.Recruitment.recruitment_id == modelDB.Application.recruitment_id)\
     .join(modelDB.User, modelDB.Application.applicant_user_id == modelDB.User.user_id)\
     .join(modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id)\
     .filter(
         modelDB.Recruitment.recruiter_user_id == my_id,
         modelDB.Recruitment.status == 1,  # 募集終了/進行中
         modelDB.Application.status == 1   # 承認済み
     ).all()

    for rec, route, app, user, prof in driver_side:
        response_list.append(ProgressDriveItem(
            id=str(rec.recruitment_id),
            from_loc=route.depname,
            to_loc=route.arrname,
            datetime=route.dep_time.strftime('%Y-%m-%d %H:%M'),
            price=rec.fare,
            driver=DriverInfo(
                name=user.name, # 同乗者の名前
                rating=float(prof.rating),
                driveCount=prof.ride_count
            )
        ))

    # パターンB: 自分が「同乗者（申請者）」の場合
    # Application.applicant_user_id=自分のID かつ Application.status=1(承認済) の運転者情報を取得
    passenger_side = db.query(
        modelDB.Application,
        modelDB.Recruitment,
        modelDB.Route,
        modelDB.User,
        modelDB.PassengerProfile # 本来はDriverProfileだが、提示されたPassengerProfileを使用
    ).join(modelDB.Recruitment, modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id)\
     .join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
     .join(modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id)\
     .join(modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id)\
     .filter(
         modelDB.Application.applicant_user_id == my_id,
         modelDB.Application.status == 1,
         modelDB.Recruitment.status == 1
     ).all()

    for app, rec, route, user, prof in passenger_side:
        response_list.append(ProgressDriveItem(
            id=str(rec.recruitment_id),
            from_loc=route.depname,
            to_loc=route.arrname,
            datetime=route.dep_time.strftime('%Y-%m-%d %H:%M'),
            price=rec.fare,
            driver=DriverInfo(
                name=user.name, # 運転者の名前
                rating=float(prof.rating),
                driveCount=prof.ride_count # 本来は運転回数
            )
        ))

    return ProgressResponse(drives=response_list)