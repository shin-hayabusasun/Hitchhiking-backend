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

class DriveDetailResponse(BaseModel):
    ok: bool
    drive_id: str
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
async def get_drive_detail(ride_id: str, db: Session = Depends(get_db)):
    # 1. 募集テーブル取得
    drive = db.query(modelDB.募集).filter(modelDB.募集.募集ID == ride_id).first()
    
    if not drive:
        raise HTTPException(status_code=404, detail="募集IDが見つかりません")

    # 2. 関連データ取得（存在しない可能性を考慮）
    driver = db.query(modelDB.ユーザー).filter(modelDB.ユーザー.ユーザーID == drive.募集ユーザーID).first()
    route = db.query(modelDB.経路).filter(modelDB.経路.経路ID == drive.経路ID).first()
    profile = db.query(modelDB.プロフィール_位置情報).filter(modelDB.プロフィール_位置情報.ユーザーID == drive.募集ユーザーID).first()

    # 3. 500エラーを絶対に防ぐための安全なデータ取り出し
    # 全ての項目に対して、データが無い場合の予備（デフォルト値）を設定します
    return DriveDetailResponse(
        ok=True,
        drive_id=str(getattr(drive, '募集ID', ride_id)),
        driver_name=str(getattr(driver, '名前', "不明")),
        origin=str(getattr(route, '出発位置', "未設定")),
        destination=str(getattr(route, '到着位置', "未設定")),
        dep_time=str(getattr(route, '出発時間', "不明")),
        arr_time=str(getattr(route, '到着時間', "不明")),
        price=int(getattr(drive, '運賃', 0) or 0),
        capacity=int(getattr(drive, '募集人数', 0) or 0),
        description=str(getattr(profile, 'プロフィール文', "よろしくお願いします！")),
        status=str(getattr(drive, '募集状況', "1"))
    )