# ======================================
# app/name/koroboshi/mypage.py
# ======================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import sys

sys.path.append("..")
from db_setting import SessionLocal
import modelDB

router = APIRouter(prefix="/api/driver/mypage", tags=["driver"])

# ======================================
# DBセッション
# ======================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ======================================
# Pydantic Models（Next.js 完全対応）
# ======================================

class RuleModel(BaseModel):
    smoke: bool
    pet: bool
    food: bool
    music: bool


class DriverProfileUpdate(BaseModel):
    name: str
    introduction: Optional[str]
    hobby: Optional[str]
    purpose: Optional[str]
    carModel: str
    carColor: str
    carYear: str
    carNumber: str
    rules: RuleModel


class DriverProfileResponse(BaseModel):
    name: str
    initial: str
    driveCount: int
    rating: float
    registeredAt: str

    car: dict
    rules: dict

    introduction: Optional[str]
    hobby: Optional[str]
    purpose: Optional[str]

    license: dict

# ======================================
# GET：マイページ取得
# ======================================
@router.get("", response_model=DriverProfileResponse)
async def get_driver_mypage(
    db: Session = Depends(get_db)
):
    # ※ 本来はログインセッションから取得
    user_id = 1

    profile = (
        db.query(modelDB.DriverProfile)
        .filter(modelDB.DriverProfile.user_id == user_id)
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    return {
        "name": "黒星 朋来",
        "initial": "黒",
        "driveCount": profile.drive_count,
        "rating": float(profile.rating),
        "registeredAt": profile.reg_date.strftime("%Y/%m/%d"),

        "car": {
            "model": profile.car_model,
            "color": profile.car_color,
            "year": int(profile.car_year),
            "number": profile.car_number,
        },

        "rules": {
            "smoking": not profile.no_smoking,
            "pet": profile.pet_ok,
            "food": profile.food_ok,
            "music": profile.music_ok,
        },

        "introduction": profile.bio,
        "hobby": "ドライブ、写真撮影",
        "purpose": "通勤・週末のお出かけ",

        "license": {
            "number": str(profile.license_id),
            "expire": profile.license_expiry.isoformat(),
            "verified": True,
        },
    }

# ======================================
# PUT：マイページ編集保存
# ======================================
@router.put("")
async def update_driver_mypage(
    data: DriverProfileUpdate,
    db: Session = Depends(get_db)
):
    user_id = 1  # TODO: 認証から取得

    profile = (
        db.query(modelDB.DriverProfile)
        .filter(modelDB.DriverProfile.user_id == user_id)
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    # 車両情報
    profile.car_model = data.carModel
    profile.car_color = data.carColor
    profile.car_year = data.carYear
    profile.car_number = data.carNumber

    # ルール
    profile.no_smoking = not data.rules.smoke
    profile.pet_ok = data.rules.pet
    profile.food_ok = data.rules.food
    profile.music_ok = data.rules.music

    # 自己紹介
    profile.bio = data.introduction

    db.commit()

    return {
        "ok": True,
        "message": "プロフィールを更新しました"
    }
