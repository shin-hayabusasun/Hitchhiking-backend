from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import sys

# --- 共通インポート ---
sys.path.append('..')
from db_setting import SessionLocal
import modelDB

# フロントエンドの fetch('/api/drives/${id}') に合わせるため
# 本来は prefix="/api/drives" ですが、他の方の形式に合わせて定義します
router = APIRouter(prefix="/api/drives", tags=["DriveDetail"])

# DBセッション取得用
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- フロントエンドの Interface とモック構造に合わせたレスポンス型定義 ---
class DriverProfileSchema(BaseModel):
    rating: float
    reviewCount: int
    verificationStatus: str

class VehicleRulesSchema(BaseModel):
    noSmoking: bool
    petAllowed: bool
    musicAllowed: bool

class DriveDetailSchema(BaseModel):
    id: str
    driverId: str
    driverName: str
    driverProfile: DriverProfileSchema
    departure: str
    destination: str
    departureTime: str
    capacity: int
    currentPassengers: int
    fee: int
    message: str
    vehicleRules: VehicleRulesSchema

class DriveDetailResponse(BaseModel):
    drive: DriveDetailSchema

# --- API 処理 ---
# フロントエンドが `/api/drives/${id}` と送るため、パスパラメータ {id} を使用
@router.get("/{id}", response_model=DriveDetailResponse)
async def get_drive_detail(id: int, db: Session = Depends(get_db)):
    """
    フロントエンドのドライブ詳細画面用API
    
    1. recruitments (募集) を取得
    2. users (ドライバー名) を取得
    3. routes (出発・到着) を取得
    4. driver_profiles (車両ルール・評価) を取得
    """
    
    # 1. 募集データの取得 (設計書の recruitment_id)
    drive = db.query(modelDB.Recruitment).filter(modelDB.Recruitment.recruitment_id == id).first()
    
    if not drive:
        # DBにデータがない場合は、フロントが止まらないよう「モックデータ」を返却する
        return DriveDetailResponse(
            drive=DriveDetailSchema(
                id=str(id),
                driverId="mock_id",
                driverName="田中 太郎(Mock)",
                driverProfile=DriverProfileSchema(rating=4.8, reviewCount=45, verificationStatus="verified"),
                departure="東京駅",
                destination="横浜駅",
                departureTime="2025-11-05 09:00",
                capacity=2,
                currentPassengers=0,
                fee=800,
                message="DBにデータがないためモックを表示しています。",
                vehicleRules=VehicleRulesSchema(noSmoking=True, petAllowed=False, musicAllowed=True)
            )
        )

    # 2. 関連データの取得 (他の方のコードを参考に getattr で安全に取得)
    driver = db.query(modelDB.User).filter(modelDB.User.user_id == drive.recruiter_user_id).first()
    route = db.query(modelDB.Route).filter(modelDB.Route.route_id == drive.route_id).first()
    profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == drive.recruiter_user_id).first()

    # --- データの組み立て ---
    # フロントエンドの mockDriveDetail の構造を完全に再現
    return DriveDetailResponse(
        drive=DriveDetailSchema(
            id=str(drive.recruitment_id),
            driverId=str(getattr(driver, 'user_id', "0")),
            driverName=getattr(driver, 'name', "不明"),
            driverProfile=DriverProfileSchema(
                rating=float(getattr(profile, 'rating', 0.0)),
                reviewCount=int(getattr(profile, 'drive_count', 0)),
                verificationStatus="verified" # DBに項目がないため固定
            ),
            # DB構成図の routes テーブルに基づき取得
            departure=str(getattr(route, 'path_data', "地点未設定")), 
            destination=str(getattr(route, 'path_data', "地点未設定")),
            departureTime=str(getattr(route, 'dep_time', "時刻不明")),
            capacity=getattr(drive, 'capacity', 0),
            currentPassengers=0, # applicationテーブルからカウントが必要だが一旦0
            fee=getattr(drive, 'fare', 0),
            message=getattr(profile, 'bio', "よろしくお願いします！"),
            vehicleRules=VehicleRulesSchema(
                noSmoking=bool(getattr(profile, 'no_smoking', True)),
                petAllowed=bool(getattr(profile, 'pet_ok', False)),
                musicAllowed=bool(getattr(profile, 'music_ok', True))
            )
        )
    )