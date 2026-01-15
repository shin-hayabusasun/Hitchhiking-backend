from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import sys

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
@router.get("/schedules", response_model=ScheduleResponse)
def get_schedules(db: Session = Depends(get_db)):
    """
    募集中のドライブ一覧（スケジュール）を取得
    URLを /schedules に変更し、返すデータ構造も修正
    """
    
    # status=0 (募集中) のデータを取得
    recruitments = (
        db.query(modelDB.Recruitment)
        .filter(modelDB.Recruitment.status == 0)
        .all()
    )

    results = []

    for r in recruitments:
        results.append(
            ScheduleItem(
                id=str(r.recruitment_id), # 文字列に変換
                createdAt="2025/01/10",   # 仮の日付（DBにカラムがあれば r.created_at など）
                depName="東京駅",         # 仮のデータ
                arrName="羽田空港",       # 仮のデータ
                depTime="2025-02-01 09:00", 
                fare=r.fare,
                capacity=4,               # 仮の定員
                status="募集中"            # 仮のステータス表示
            )
        )

    return ScheduleResponse(schedules=results)

# --------------------
# ★追加：スケジュールの削除
# DELETE /api/driver/schedules/{id}
# --------------------
@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)):
    # ここに削除ロジック（DBからstatusを更新するなど）を書く
    # 今回はフロントエンドのエラーを防ぐため、とりあえず成功を返す
    return {"message": "deleted", "id": schedule_id}


# --------------------
# 進行中ドライブ取得
# GET /api/driver/progress
# --------------------
@router.get("/progress", response_model=ProgressResponse)
def get_progress(db: Session = Depends(get_db)):
    """
    進行中（status=1）のドライブ一覧を取得
    """
    recruitments = (
        db.query(modelDB.Recruitment)
        .filter(modelDB.Recruitment.status == 1)
        .all()
    )

    drives = []

    for r in recruitments:
        drives.append(
            ProgressDrive(
                id=r.recruitment_id,
                from_="東京駅", 
                to="羽田空港",
                datetime="2025-01-01 10:00",
                price=r.fare,
                driver=DriverInfo(
                    name="山田 太郎",
                    rating=4.8,
                    driveCount=120
                )
            )
        )

    return ProgressResponse(drives=drives)

# --------------------
# ドライブ完了
# POST /api/driver/complete
# --------------------
@router.post("/complete", response_model=CompleteResponse)
def complete_drive(
    req: CompleteRequest,
    db: Session = Depends(get_db)
):
    """
    ドライブを完了状態に更新
    """
    recruitment = (
        db.query(modelDB.Recruitment)
        .filter(modelDB.Recruitment.recruitment_id == req.driveId)
        .first()
    )

    if not recruitment:
        raise HTTPException(status_code=404, detail="Drive not found")

    recruitment.status = 2  # 運転完了
    db.commit()

    return CompleteResponse(
        ok=True,
        message="ドライブを完了しました"
    )