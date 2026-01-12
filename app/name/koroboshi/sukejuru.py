from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

# 自作モジュール（パスはプロジェクト構成に合わせて調整してください）
import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user  # テンプレートの指定通り

router = APIRouter(prefix="/api/driver", tags=["driver_kanri"])

# --- DBセッションの取得 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- レスポンス用のデータ構造定義 ---
class ScheduleItem(BaseModel):
    id: str
    createdAt: str
    depName: str
    arrName: str
    depTime: str
    fare: int
    capacity: int
    status: str

class ScheduleListResponse(BaseModel):
    schedules: List[ScheduleItem]

# --- メインAPI: 自分の募集一覧取得 ---
@router.get("/schedules", response_model=ScheduleListResponse)
async def get_my_schedules(request: Request, db: Session = Depends(get_db)):
    """
    ログイン中の運転者の「予定中」の募集をDBから取得する
    """
    # 1. クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Session not found")

    # 2. セッションからユーザーIDを特定
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # 文字列で返ってくるため int に変換（DBがInteger型の場合）
    user_id = int(user_id_str)

    # 3. DBからデータを取得 (Recruitment と Route を Join)
    # status: 0(予定中/募集中), type: 0(運転者からの募集) と仮定
    results = db.query(
        modelDB.Recruitment,
        modelDB.Route
    ).join(
        modelDB.Route, 
        modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).filter(
        modelDB.Recruitment.recruiter_user_id == user_id,
        modelDB.Recruitment.status == 0
    ).all()

    # 4. フロントエンドが期待する形式に整形
    schedules_data = []
    for rec, route in results:
        schedules_data.append(ScheduleItem(
            id=str(rec.recruitment_id),
            # Routeテーブルの作成日がない場合は現在時刻やdep_timeで代用（ここでは仮に作成日を固定または計算）
            createdAt=datetime.now().strftime('%Y-%m-%d'), 
            depName=route.depname,
            arrName=route.arrname,
            depTime=route.dep_time.strftime('%Y-%m-%d %H:%M'),
            fare=rec.fare,
            capacity=rec.capacity,
            status="予定中"
        ))

    return ScheduleListResponse(schedules=schedules_data)