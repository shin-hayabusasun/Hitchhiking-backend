from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import sys
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user # 既存の認証関数をインポート

# レスポンスモデルの定義
from pydantic import BaseModel
from datetime import datetime

class DriveResponse(BaseModel):
    id: int  # recruitment_id
    departure: str
    destination: str
    departureTime: datetime
    fee: int
    capacity: int
    currentPassengers: int # 現在の同乗者数（計算が必要）
    status: str # フロントエンドのステータス文字列に変換

class DriveListResponse(BaseModel):
    drives: List[DriveResponse]

router = APIRouter(prefix="/api/driver", tags=["driver"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/drives", response_model=DriveListResponse)
async def get_my_drives(
    request: Request, 
    status: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """
    マイドライブ一覧取得API
    """
    # 1. セッションIDからユーザーIDを取得
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = int(user_id_str)

    # 2. データベースからドライブ情報を取得
    # RecruitmentテーブルとRouteテーブルを結合
    query = db.query(modelDB.Recruitment, modelDB.Route).\
        join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id).\
        filter(modelDB.Recruitment.recruiter_user_id == user_id)

    # ステータスフィルタリング (必要であれば)
    # DBのstatusはint型: 0:募集中, 1:募集終了(確定), 2:完了, 3:中止 と仮定
    if status:
        if status == 'recruiting':
            query = query.filter(modelDB.Recruitment.status == 0)
        elif status == 'matched':
            query = query.filter(modelDB.Recruitment.status == 1)
        # ... 他のステータスも同様に

    # 日時順（未来の日付が上）にソート
    drives_data = query.order_by(desc(modelDB.Route.dep_time)).all()

    response_list = []
    for recruitment, route in drives_data:
        # 現在の同乗者数をカウント (Applicationテーブルから承認済みの人数を取得)
        # status=1 (承認) の数をカウント
        passenger_count = db.query(modelDB.Application).\
            filter(
                modelDB.Application.recruitment_id == recruitment.recruitment_id,
                modelDB.Application.status == 1 
            ).count()

        # ステータスコードを文字列に変換
        status_str = "recruiting"
        if recruitment.status == 0: status_str = "recruiting"
        elif recruitment.status == 1: status_str = "matched"
        elif recruitment.status == 2: status_str = "completed"
        elif recruitment.status == 3: status_str = "cancelled"

        # Routeテーブルには経度緯度が入っているが、フロントエンドの表示用に地名が必要
        # ここでは簡易的に緯度経度を返すか、別途逆ジオコーディングするか、
        # あるいはpath_dataに地名が含まれているならそこから取得する。
        # 今回は一旦 path_data に "東京駅" のような文字列が入っているか、
        # または別途地名カラムが必要だが、モデル定義にはないので仮置き。
        # ※本来は departure_name, destination_name カラムがRouteにあると良い
        
        # path_dataから無理やり地名を取り出すか、固定値を返す（要DB設計確認）
        # 仮の実装: path_dataをそのまま使うか、"座標"として返す
        departure_name = "出発地" # TODO: 座標から地名への変換ロジック
        destination_name = "目的地" # TODO: 座標から地名への変換ロジック

        response_list.append(DriveResponse(
            id=recruitment.recruitment_id,
            departure=departure_name, 
            destination=destination_name,
            departureTime=route.dep_time,
            fee=recruitment.fare,
            capacity=recruitment.capacity,
            currentPassengers=passenger_count,
            status=status_str
        ))

    return DriveListResponse(drives=response_list)