from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
import sys
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

# ルーター定義 (prefixは機能に合わせて設定)
router = APIRouter(prefix="/api/drives", tags=["drives"])

# DBセッション
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------
# レスポンスモデル定義
# ------------------------------

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

# ------------------------------
# APIエンドポイント実装
# ------------------------------

# パターン3: セッション認証 + DB取得
@router.get("/{drive_id}", response_model=DriveDetailWrapper)
async def get_drive_detail(
    drive_id: int,
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    ドライブ詳細取得API
    
    処理:
    1. セッションIDの検証
    2. DBから指定されたdrive_idの情報を取得
    3. 関連テーブル（Route, DriverProfile, Application）を結合してデータを整形
    """
    
    # 1. クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 2. セッションIDが有効か確認
    res = get_current_user(session_id=session_id, db=db)
    
    if res == "no":
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    
    # ユーザーID取得 (strで返ってくるためintに変換)
    user_id = int(res)

    # 3. データベースからドライブ情報を取得
    # Recruitment, Route, User(運転者), DriverProfile を結合
    drive_data = db.query(modelDB.Recruitment, modelDB.Route, modelDB.DriverProfile, modelDB.User).\
        join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id).\
        join(modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id).\
        join(modelDB.DriverProfile, modelDB.User.user_id == modelDB.DriverProfile.user_id).\
        filter(modelDB.Recruitment.recruitment_id == drive_id).first()

    if not drive_data:
        raise HTTPException(status_code=404, detail="Drive not found")

    recruitment, route, driver_profile, driver_user = drive_data

    # 4. 同乗者リストと現在の乗車人数を取得
    applications = db.query(modelDB.Application, modelDB.User).\
        join(modelDB.User, modelDB.Application.applicant_user_id == modelDB.User.user_id).\
        filter(modelDB.Application.recruitment_id == drive_id).all()

    passenger_list = []
    current_passenger_count = 0

    for app, passenger_user in applications:
        # ステータス判定 (DBの値 -> フロントエンド用文字列)
        status_str = "pending"
        if app.status == 1: # 承認済み
            status_str = "approved"
            current_passenger_count += 1
        elif app.status == 2: # 拒否
            status_str = "rejected"
        
        passenger_list.append(Passenger(
            id=app.application_id,
            name=passenger_user.name,
            status=status_str
        ))

    # ドライブ自体のステータス変換
    drive_status = "recruiting"
    if recruitment.status == 0: drive_status = "active"
    elif recruitment.status == 1: drive_status = "scheduled" # 確定済み等
    elif recruitment.status == 2: drive_status = "completed"
    elif recruitment.status == 3: drive_status = "cancelled"

    # TODO: 地名データの取得 (現在はDBにカラムがないため仮置き)
    # 本来はRouteテーブルにdeparture_name等のカラムを追加するか、座標から逆ジオコーディングが必要
    departure_name = "出発地(座標)" 
    destination_name = "目的地(座標)"

    # 5. レスポンスデータの構築
    response_data = DriveDetailResponse(
        id=recruitment.recruitment_id,
        driverId=driver_user.user_id,
        driverName=driver_user.name,
        departure=departure_name,
        destination=destination_name,
        departureTime=route.dep_time,
        capacity=recruitment.capacity,
        currentPassengers=