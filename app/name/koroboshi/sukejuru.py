from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from pydantic import BaseModel
from datetime import datetime

# 自作モジュール
import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/driver", tags=["driver_kanri"])

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

# --- 自分の「募集中(status=0)」の募集一覧取得 ---
@router.get("/schedules", response_model=ScheduleListResponse)
async def get_my_schedules(request: Request, db: Session = Depends(get_db)):
    """
    ダミー値を一切使わず、DBから取得した真実の募集データを返す
    """
    # 1. ユーザー認証
    session_id = request.cookies.get("session_id")
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です")
    
    my_id = int(user_id_str)

    # 2. DBクエリ
    # RecruitmentとRouteを内部結合(JOIN)し、自分の募集かつstatus=0(募集/予定中)を抽出
    results = db.query(
        modelDB.Recruitment,
        modelDB.Route
    ).join(
        modelDB.Route, 
        modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).filter(
        modelDB.Recruitment.recruiter_user_id == my_id,
        modelDB.Recruitment.status == 0,
        modelDB.Recruitment.type == 0 # 運転者としての募集
    ).order_by(desc(modelDB.Route.dep_time)).all()

    schedules_data = []

    # 3. データの整形（ダミーを排除し、DBの値をそのままマッピング）
    for rec, route in results:
        # Routeテーブルの値を直接参照
        # ※.depname, .arrname は models.py の Route クラスで定義されているカラム名
        schedules_data.append(ScheduleItem(
            id=str(rec.recruitment_id),
            # Routeテーブルのデータ作成日時がモデルにないため、出発日の日付を表示
            createdAt=route.dep_time.strftime('%Y/%m/%d'), 
            depName=route.depname if route.depname else "出発地未設定",
            arrName=route.arrname if route.arrname else "目的地未設定",
            depTime=route.dep_time.strftime('%Y-%m-%d %H:%M'),
            fare=rec.fare,
            capacity=rec.capacity,
            status="募集中" # 内部ステータス 0 に基づく固定ラベル
        ))

    return ScheduleListResponse(schedules=schedules_data)