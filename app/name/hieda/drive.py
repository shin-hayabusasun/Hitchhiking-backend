import random
import json
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey

# 自作モジュール（環境に合わせてパスを調整）
import modelDB
from db_setting import SessionLocal
from pydantic import BaseModel
# 認証が必要な場合に使用
# from app.name.hieda.hitchhikersearch import get_current_user

router = APIRouter(prefix="/api/test/drive", tags=["testdriveuser"])

# --- データベースセッション設定 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- テスト用ダミーデータ作成API ---

class UserIdListResponse(BaseModel):
    ok: bool
    user_ids: list[int]

@router.get("/ids", response_model=UserIdListResponse)
def get_all_user_ids(db: Session = Depends(get_db)):
    users = db.query(modelDB.User.user_id).all()

    # [(1,), (2,), ...] → [1, 2, ...]
    user_ids = [u.user_id for u in users]

    return UserIdListResponse(ok=True, user_ids=user_ids)

@router.post("/fill_test_driver_profile/{user_id}")
async def fill_driver_profile(user_id: int, db: Session = Depends(get_db)):
    """
    指定された user_id のプロフィール項目をダミーデータで埋める（デバッグ用）
    """
    
    # 1. ユーザーの存在確認（DriverProfileの前にUserテーブルにあるか確認するのが安全）
    # user_exists = db.query(modelDB.User).filter(modelDB.User.user_id == user_id).first()
    # if not user_exists:
    #     raise HTTPException(status_code=404, detail="User not found in users table")

    # 2. すでにプロフィールがあるか確認
    profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == user_id).first()
    
    # ダミーデータの候補
    car_models = ["トヨタ プリウス", "ホンダ N-BOX", "日産 セレナ", "トヨタ アクア", "マツダ CX-5"]
    colors = ["ホワイト", "ブラック", "シルバー", "ブルー", "レッド"]
    bios = [
        "安全運転を心がけています。よろしくお願いします！",
        "週末によく遠出をします。楽しくお話ししましょう。",
        "静かな車内が好きです。音楽のリクエストも受け付けます。",
        "初心者ですが、丁寧に運転します。"
    ]

    # 3. データの生成
    dummy_data = {
        "license_id": random.randint(100000000000, 999999999999), # 12桁のランダムな数字
        "license_expiry": date.today() + timedelta(days=random.randint(365, 1825)), # 1〜5年後の有効期限
        "drive_count": random.randint(0, 100),
        "rating": round(random.uniform(3.5, 5.0), 1), # 3.5〜5.0の評価
        "reg_date": date.today() - timedelta(days=random.randint(1, 365)), # 過去1年以内の登録日
        "car_model": random.choice(car_models),
        "car_color": random.choice(colors),
        "car_year": str(random.randint(2015, 2025)),
        "car_number": f"{random.choice(['品川', '世田谷', '横浜', '足立'])} {random.randint(100, 999)} あ {random.randint(1000, 9999)}",
        "no_smoking": random.choice([True, False]),
        "pet_ok": random.choice([True, False]),
        "food_ok": random.choice([True, False]),
        "music_ok": random.choice([True, False]),
        "latitude": 35.6812 + random.uniform(-0.1, 0.1),  # 東京駅周辺のランダムな座標
        "longitude": 139.7671 + random.uniform(-0.1, 0.1),
        "bio": random.choice(bios),
        "embedding": [0.0] * 384 # 384次元のゼロベクトル
    }

    try:
        if profile:
            # 既存プロフィールの更新
            for key, value in dummy_data.items():
                setattr(profile, key, value)
        else:
            # 新規プロフィールの作成
            profile = modelDB.DriverProfile(user_id=user_id, **dummy_data)
            db.add(profile)

        db.commit()
        
        return {
            "status": "success",
            "message": f"User {user_id} のプロフィールをダミーデータで更新しました。",
            "data": {
                "car": dummy_data["car_model"],
                "rating": dummy_data["rating"],
                "is_new": profile is None
            }
        }
    except Exception as e:
        db.rollback()
        # 詳細なエラー内容を表示（デバッグ用）
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")