from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import sys
from app.name.hieda.user import get_current_user

sys.path.append("..")
from db_setting import SessionLocal
import modelDB

router = APIRouter(
    prefix="/api/driver",
    tags=["driver"]
)

# --------------------
# DBセッション
# --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------
# 共通/レスポンス用スキーマ
# --------------------
class DriverInfo(BaseModel):
    name: str
    rating: float
    driveCount: int

# --- 進行中画面用 ---
class ProgressDrive(BaseModel):
    id: int
    from_: str
    to: str
    datetime: str
    price: int
    driver: DriverInfo

class ProgressResponse(BaseModel):
    drives: List[ProgressDrive]

# --- 完了処理用 ---
class CompleteRequest(BaseModel):
    driveId: int

class CompleteResponse(BaseModel):
    ok: bool
    message: str

# --- ★修正：スケジュール画面用スキーマ（フロントエンドに合わせる） ---
class ScheduleItem(BaseModel):
    id: str        # フロントがstring期待のため
    createdAt: str
    depName: str   # from_ から変更
    arrName: str   # to から変更
    depTime: str   # datetime から変更
    fare: int      # price から変更
    capacity: int  # 追加
    status: str    # 追加

class ScheduleResponse(BaseModel):
    schedules: List[ScheduleItem]


# --------------------
# ★修正：スケジュール取得
# GET /api/driver/schedules (複数形に修正)
# --------------------
