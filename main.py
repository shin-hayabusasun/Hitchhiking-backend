# FastAPIをインポート

from db_setting import engine, Base, SessionLocal
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import modelDB  # models.pyをインポート(DBモデル定義)
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date


# テーブル作成
modelDB.Base.metadata.create_all(bind=engine)

# FastAPIのインスタンス作成
app = FastAPI(
    title="Rideshare API",
    description="ライドシェアアプリケーションのAPI",
    version="1.0.0"
)


# Pydantic レスポンスモデル
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    gender: int
    birth_date: str  # YYYY-MM-DD形式
    address: str


class UserOut(BaseModel):
    user_id: int
    name: str
    email: str
    
    class Config:
        orm_mode = True


class DriverProfileCreate(BaseModel):
    user_id: int
    license_id: int
    license_expiry: str  # YYYY-MM-DD形式
    car_model: str
    car_color: str
    car_year: str
    car_number: str
    no_smoking: Optional[bool] = None
    pet_ok: Optional[bool] = None
    food_ok: Optional[bool] = None
    music_ok: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bio: Optional[str] = None


class DriverProfileOut(BaseModel):
    user_id: int
    license_id: int
    drive_count: int
    rating: float
    car_model: str
    car_color: str
    latitude: Optional[float]
    longitude: Optional[float]
    
    class Config:
        orm_mode = True


# DBセッションをリクエストごとに生成・破棄する
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===============================
# ルートエンドポイント
# ===============================

@app.get("/")
async def root():
    return {
        "message": "Rideshare API - Successfully Running",
        "status": "ok",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy"}


# ===============================
# ユーザー関連エンドポイント
# ===============================

@app.post("/users/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """ユーザーを作成"""
    try:
        birth_date_obj = datetime.strptime(user.birth_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    new_user = modelDB.User(
        name=user.name,
        email=user.email,
        password=user.password,  # 本番環境ではハッシュ化必須
        gender=user.gender,
        birth_date=birth_date_obj,
        address=user.address,
        identity_doc=b''  # 一時的に空のバイナリ
    )
    
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")


@app.get("/users/", response_model=List[UserOut])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """ユーザー一覧を取得"""
    users = db.query(modelDB.User).offset(skip).limit(limit).all()
    return users


@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """特定のユーザーを取得"""
    user = db.query(modelDB.User).filter(modelDB.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ===============================
# 運転者プロフィール関連エンドポイント
# ===============================

@app.post("/driver-profiles/", response_model=DriverProfileOut)
def create_driver_profile(profile: DriverProfileCreate, db: Session = Depends(get_db)):
    """運転者プロフィールを作成"""
    # ユーザー存在チェック
    user = db.query(modelDB.User).filter(modelDB.User.user_id == profile.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 既にプロフィールが存在するかチェック
    existing = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == profile.user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Driver profile already exists")
    
    try:
        license_expiry_obj = datetime.strptime(profile.license_expiry, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    new_profile = modelDB.DriverProfile(
        user_id=profile.user_id,
        license_id=profile.license_id,
        license_expiry=license_expiry_obj,
        drive_count=0,
        rating=0.0,
        reg_date=date.today(),
        car_model=profile.car_model,
        car_color=profile.car_color,
        car_year=profile.car_year,
        car_number=profile.car_number,
        no_smoking=profile.no_smoking,
        pet_ok=profile.pet_ok,
        food_ok=profile.food_ok,
        music_ok=profile.music_ok,
        latitude=profile.latitude,
        longitude=profile.longitude,
        bio=profile.bio
    )
    
    db.add(new_profile)
    try:
        db.commit()
        db.refresh(new_profile)
        return new_profile
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create driver profile")


@app.get("/driver-profiles/", response_model=List[DriverProfileOut])
def get_driver_profiles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """運転者プロフィール一覧を取得"""
    profiles = db.query(modelDB.DriverProfile).offset(skip).limit(limit).all()
    return profiles


@app.get("/driver-profiles/{user_id}", response_model=DriverProfileOut)
def get_driver_profile(user_id: int, db: Session = Depends(get_db)):
    """特定の運転者プロフィールを取得"""
    profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return profile


# ===============================
# テーブル一覧確認（デバッグ用）
# ===============================

@app.get("/debug/tables")
def list_tables(db: Session = Depends(get_db)):
    """作成されたテーブル一覧を取得（デバッグ用）"""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return {"tables": tables}
