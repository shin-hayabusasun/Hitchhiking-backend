from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

# 自作モジュールのインポート（パスは環境に合わせて調整してください）
import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user

# ★ これが足りなかったためにエラーになっていました
router = APIRouter(prefix="/api/driver", tags=["completion"])

# --- スキーマ定義 (ProgressResponseなどが使われている場合) ---
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
    driver: DriverInfo

class ProgressResponse(BaseModel):
    drives: List[ProgressDriveItem]

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()


@router.get("/completion", response_model=ProgressResponse)
async def get_completion_drives(request: Request, db: Session = Depends(get_db)):
    # 1. セッションから自分のIDを特定
    session_id = request.cookies.get("session_id")
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401)
    my_id = int(res)

    final_list = []

    # パターンA: 自分が「運転者（募集者）」だった完了済みドライブ
    # -> 相手（同乗者/申請者）の情報を取得
    driver_side = db.query(
        modelDB.Recruitment, modelDB.Route, modelDB.Application, 
        modelDB.User, modelDB.PassengerProfile
    ).join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
     .join(modelDB.Application, modelDB.Recruitment.recruitment_id == modelDB.Application.recruitment_id)\
     .join(modelDB.User, modelDB.Application.applicant_user_id == modelDB.User.user_id)\
     .join(modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id)\
     .filter(
         modelDB.Recruitment.recruiter_user_id == my_id,
         modelDB.Recruitment.status == 2, # 完了
         modelDB.Application.status == 1  # 承認済みだったもの
     ).all()

    for rec, route, app, user, prof in driver_side:
        final_list.append(ProgressDriveItem(
            id=str(rec.recruitment_id),
            from_loc=route.depname,
            to_loc=route.arrname,
            datetime=route.dep_time.strftime('%Y-%m-%d %H:%M'),
            price=rec.fare,
            driver=DriverInfo(
                name=user.name, # 相手の名前
                rating=float(prof.rating),
                driveCount=prof.ride_count
            )
        ))

    # パターンB: 自分が「同乗者（申請者）」だった完了済みドライブ
    # -> 相手（運転者/募集者）の情報を取得
    passenger_side = db.query(
        modelDB.Application, modelDB.Recruitment, modelDB.Route,
        modelDB.User, modelDB.PassengerProfile
    ).join(modelDB.Recruitment, modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id)\
     .join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
     .join(modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id)\
     .join(modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id)\
     .filter(
         modelDB.Application.applicant_user_id == my_id,
         modelDB.Application.status == 1,
         modelDB.Recruitment.status == 2
     ).all()

    for app, rec, route, user, prof in passenger_side:
        final_list.append(ProgressDriveItem(
            id=str(rec.recruitment_id),
            from_loc=route.depname,
            to_loc=route.arrname,
            datetime=route.dep_time.strftime('%Y-%m-%d %H:%M'),
            price=rec.fare,
            driver=DriverInfo(
                name=user.name, # 相手の名前
                rating=float(prof.rating),
                driveCount=prof.ride_count
            )
        ))

    return ProgressResponse(drives=final_list)