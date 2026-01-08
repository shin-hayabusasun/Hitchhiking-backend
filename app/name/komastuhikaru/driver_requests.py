from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
import sys

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
# 認証関数のインポート（環境に合わせて調整してください）
from app.name.hieda.user import get_current_user 

router = APIRouter(prefix="/api/driver", tags=["driver"])

# ---------------------------------------------------------
# Pydantic Models (Response Schema)
# Reactの interface Request に合わせる
# ---------------------------------------------------------
class ApplicationRequestItem(BaseModel):
    id: int               # React側: number
    passengerName: str
    matchingRate: int
    rating: float
    reviewCount: int
    departure: str
    destination: str
    departureTime: str    # React側: string (フォーマット済み日時)
    createdAt: str        # React側: string

class ApplicationListResponse(BaseModel):
    requests: List[ApplicationRequestItem]

# ---------------------------------------------------------
# Dependency
# ---------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# API Endpoint
# ---------------------------------------------------------
@router.get("/requests", response_model=ApplicationListResponse)
async def get_driver_requests(
    request: Request,
    status: str = "pending",
    db: Session = Depends(get_db)
):
    """
    運転者向け申請一覧取得 (GET /api/driver/requests)
    """
    # 1. 認証・ユーザー特定
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_driver_id = int(user_id_str)

    # ステータス定義 (DB仕様想定: 0=申請中, 1=承認, 2=拒否)
    # クエリパラメータ ?status=pending なら 0 を対象にする
    target_status = 0 
    
    # 2. データ取得 (Join)
    # Application -> Recruitment (自分の募集) -> User (申請者) -> PassengerProfile (評価) -> Route (場所・時間)
    results = db.query(
        modelDB.Application,
        modelDB.Recruitment,
        modelDB.User,
        modelDB.PassengerProfile,
        modelDB.Route
    ).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).join(
        modelDB.User,
        modelDB.Application.applicant_user_id == modelDB.User.user_id
    ).outerjoin( # プロフィールは未登録の可能性もあるため外部結合
        modelDB.PassengerProfile,
        modelDB.User.user_id == modelDB.PassengerProfile.user_id
    ).join(
        modelDB.Route,
        modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).filter(
        modelDB.Recruitment.recruiter_user_id == current_driver_id, # 自分が募集主であること
        modelDB.Application.status == target_status               # 申請中のもの
    ).all()

    # 3. レスポンス整形
    response_list = []
    for app, recruit, user, profile, route in results:
        # プロフィール情報の取得 (存在しない場合はデフォルト0)
        rating_val = float(profile.rating) if profile else 0.0
        review_count_val = profile.ride_count if profile else 0
        
        # 場所・時間のフォーマット
        # DBには緯度経度(Numeric)が入っているため、文字列に変換
        # ※本来は逆ジオコーディングAPI等で「新宿駅」のような地名にする必要がありますが、
        # ここでは簡易的に座標を表示します。
        dep_str = f"地点({route.dep_latitude}, {route.dep_longitude})"
        des_str = f"地点({route.arr_latitude}, {route.arr_longitude})"
        
        # datetime -> string 変換
        dep_time_str = route.dep_time.strftime('%Y-%m-%d %H:%M')
        
        # 作成日 (Applicationテーブルにcreated_atがないため現在時刻で代用)
        # TODO: modelDB.Application に created_at カラムを追加することを推奨
        created_at_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

        # マッチング度 (TODO: embeddingを使った計算ロジックが必要だが、今回は固定値またはランダム)
        match_rate = 88 

        item = ApplicationRequestItem(
            id=app.application_id, # int型
            passengerName=user.name,
            matchingRate=match_rate,
            rating=rating_val,
            reviewCount=review_count_val,
            departure=dep_str,
            destination=des_str,
            departureTime=dep_time_str,
            createdAt=created_at_str
        )
        response_list.append(item)

    return ApplicationListResponse(requests=response_list)