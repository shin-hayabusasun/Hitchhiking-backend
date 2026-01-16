from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from db_setting import SessionLocal
import modelDB

router = APIRouter(prefix="/api", tags=["DriveDetail"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# 1. 特定のドライブの詳細を取得（同乗者向け）
# ---------------------------------------------------------
@router.get("/drives/{id}")
async def get_drive_detail(id: int, db: Session = Depends(get_db)):
    drive = db.query(modelDB.Recruitment).filter(modelDB.Recruitment.recruitment_id == id).first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    driver = db.query(modelDB.User).filter(modelDB.User.user_id == drive.recruiter_user_id).first()
    route = db.query(modelDB.Route).filter(modelDB.Route.route_id == drive.route_id).first()
    profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == drive.recruiter_user_id).first()

    # 現在の乗車人数を取得（承認済みの申請数）
    current_passengers = db.query(modelDB.Application).filter(
        modelDB.Application.recruitment_id == id,
        modelDB.Application.status == 1  # 承認済み
    ).count()

    status_map = {0: "募集中", 1: "募集終了", 2: "運転完了"}

    return {
        "drive": {
            # ===============================
            # ドライバー情報
            # ===============================
            "driverName": getattr(driver, 'name', "不明"),
            "isVerified": bool(getattr(driver, 'identity_doc', False)),  # 本人確認書類があるか
            
            # ドライバープロフィール
            "driverProfile": {
                "bio": getattr(profile, 'bio', "よろしくお願いします！"),
                "rating": float(getattr(profile, 'rating', 0.0)),
                "reviewCount": int(getattr(profile, 'drive_count', 0))
            },
            
            # ===============================
            # ルート情報
            # ===============================
            "departure": getattr(route, 'depname', "不明"),
            "destination": getattr(route, 'arrname', "不明"),
            
            # 出発地の緯度経度
            "departureLatitude": float(route.dep_latitude) if route and route.dep_latitude else None,
            "departureLongitude": float(route.dep_longitude) if route and route.dep_longitude else None,
            "departureLat": float(route.dep_latitude) if route and route.dep_latitude else None,
            "departureLng": float(route.dep_longitude) if route and route.dep_longitude else None,
            
            # 目的地の緯度経度
            "destinationLatitude": float(route.arr_latitude) if route and route.arr_latitude else None,
            "destinationLongitude": float(route.arr_longitude) if route and route.arr_longitude else None,
            "destinationLat": float(route.arr_latitude) if route and route.arr_latitude else None,
            "destinationLng": float(route.arr_longitude) if route and route.arr_longitude else None,
            
            # ===============================
            # ドライブ詳細情報
            # ===============================
            "departureTime": route.dep_time.strftime("%Y-%m-%d %H:%M") if route and route.dep_time else "",
            "capacity": drive.capacity,
            "currentPassengers": current_passengers,
            "status": status_map.get(drive.status, "不明"),
            "fee": drive.fare,
            
            # ===============================
            # 車両情報
            # ===============================
            "vehicle": {
                "model": getattr(profile, 'car_model', "未設定"),
                "color": getattr(profile, 'car_color', "-"),
                "year": getattr(profile, 'car_year', "-"),
                "number": getattr(profile, 'car_number', "-")
            },
            
            # ===============================
            # 車両ルール
            # ===============================
            "vehicleRules": {
                "noSmoking": bool(getattr(profile, 'no_smoking', True)),
                "petAllowed": bool(getattr(profile, 'pet_ok', False)),
                "musicAllowed": bool(getattr(profile, 'music_ok', True)),
                "conversation": "適度な会話を楽しみましょう"  # デフォルト値
            }
        }
    }

# ---------------------------------------------------------
# 2. 運転者向けの「届いた申請一覧」を取得
# ★このエンドポイントは app/name/komastuhikaru/driver_requests.py に移行しました
# ★そちらには認証・フィルタが実装されています
# ---------------------------------------------------------
# @router.get("/driver/requests")
# async def get_driver_requests(status: int = 0, db: Session = Depends(get_db)):
#     # 申請、ユーザー、ルート情報を結合して取得
#     results = db.query(
#         modelDB.Application,
#         modelDB.User,
#         modelDB.Route
#     ).join(modelDB.User, modelDB.Application.applicant_user_id == modelDB.User.user_id)\
#      .join(modelDB.Recruitment, modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id)\
#      .join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
#      .filter(modelDB.Application.status == status).all()

#     return {"requests": [
#         {
#             "id": app.application_id,
#             "passengerName": user.name,
#             "matchingRate": 95, # ロジック未実装のためダミー
#             "rating": 4.5,      # ロジック未実装のためダミー
#             "reviewCount": 10,  # ロジック未実装のためダミー
#             "departure": route.depname,
#             "destination": route.arrname,
#             "departureTime": route.dep_time.strftime("%m/%d %H:%M"),
#             "createdAt": app.application_id # IDをキーにしているため適宜調整
#         } for app, user, route in results
#     ]}