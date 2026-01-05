from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sys

# --- 共通インポート ---
sys.path.append('..')
from db_setting import SessionLocal
import modelDB

router = APIRouter(prefix="/api/hitch_hiker", tags=["DriveOperation"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 設計書の型に合わせたレスポンス定義 ---
class DriveDetailResponse(BaseModel):
    ok: bool
    drive_id: int
    driver_name: str
    origin: str
    destination: str
    dep_time: str
    arr_time: str
    price: int
    capacity: int
    description: str
    status: str

@router.get("/DriveDetail", response_model=DriveDetailResponse)
async def get_drive_detail(ride_id: int, db: Session = Depends(get_db)):
    # 1. 募集テーブル (recruitments) 取得
    # クラス名は modelDB.Recruitment, カラム名は recruitment_id です
    drive = db.query(modelDB.Recruitment).filter(modelDB.Recruitment.recruitment_id == ride_id).first()
    
    if not drive:
        raise HTTPException(status_code=404, detail="募集データが見つかりません")

    # 2. ユーザー (users) 取得
    driver = db.query(modelDB.User).filter(modelDB.User.user_id == drive.recruiter_user_id).first()
    
    # 3. 経路 (routes) 取得
    route = db.query(modelDB.Route).filter(modelDB.Route.route_id == drive.route_id).first()
    
    # 4. 運転者プロフィール (driver_profiles) 取得
    profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == drive.recruiter_user_id).first()

    # --- データの組み立て (設計書 Table1~5 のカラム名を使用) ---
    return DriveDetailResponse(
        ok=True,
        drive_id=drive.recruitment_id,
        driver_name=getattr(driver, 'name', "不明"),
        origin=str(getattr(route, 'dep_point', "未設定")),
        destination=str(getattr(route, 'arr_point', "未設定")),
        dep_time=str(getattr(route, 'dep_time', "不明")),
        arr_time=str(getattr(route, 'arr_time', "不明")),
        price=getattr(drive, 'fare', 0),
        capacity=getattr(drive, 'capacity', 0),
        description=getattr(profile, 'bio', "よろしくお願いします！"),
        status=str(getattr(drive, 'status', "1"))
    )