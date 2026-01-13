from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import cast, Numeric
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sys
import os

# パス設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/driver", tags=["DriverAction"])

# ---------------------------------------------------------
# Pydantic モデル定義
# ---------------------------------------------------------
class ApplicationRequestItem(BaseModel):
    id: int
    passengerName: str
    matchingRate: int
    rating: float
    reviewCount: int
    departure: str
    destination: str
    departureTime: str
    createdAt: str

class ApplicationListResponse(BaseModel):
    requests: List[ApplicationRequestItem]

# ---------------------------------------------------------
# DBセッション
# ---------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# API: 運転者向けの「届いた申請一覧」取得
# ---------------------------------------------------------
@router.get("/requests", response_model=ApplicationListResponse)
async def get_driver_requests(request: Request, db: Session = Depends(get_db)):
    """
    運転者本人に届いている「申請（ステータス0）」を一覧取得する
    """
    # 1. ログインユーザー（運転者）の特定
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="ログインが必要です")

    res_user_id = get_current_user(session_id=session_id, db=db)
    if res_user_id == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です")
    
    current_driver_id = int(res_user_id)

    # 2. マッチング計算用の運転者ベクトル取得
    driver_profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == current_driver_id
    ).first()
    driver_embedding = driver_profile.embedding if driver_profile else None

    # 3. クエリ構築 (申請, 募集, ユーザー, 同乗者プロフ, ルート を結合)
    # マッチング率（ベクトルの距離）を計算
    if driver_embedding is not None:
        # pgvectorのcosine_distanceを使用
        dist_col = modelDB.PassengerProfile.embedding.cosine_distance(driver_embedding).label("v_dist")
        query = db.query(
            modelDB.Application,
            modelDB.User,
            modelDB.PassengerProfile,
            modelDB.Route,
            dist_col
        )
    else:
        # ベクトルがない場合は距離Noneとして扱う
        query = db.query(
            modelDB.Application,
            modelDB.User,
            modelDB.PassengerProfile,
            modelDB.Route,
            cast(None, Numeric).label("v_dist")
        )

    # テーブル結合とフィルタリング
    results = query.join(
        modelDB.Recruitment, 
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).join(
        modelDB.User, 
        modelDB.Application.applicant_user_id == modelDB.User.user_id
    ).outerjoin(
        modelDB.PassengerProfile, 
        modelDB.User.user_id == modelDB.PassengerProfile.user_id
    ).join(
        modelDB.Route, 
        modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).filter(
        modelDB.Recruitment.recruiter_user_id == current_driver_id, # 自分が募集したもの
        modelDB.Application.status == 0                             # 申請中のもの
    ).all()

    # 4. レスポンス形式に整形
    response_list = []
    for app, user, profile, route, v_dist in results:
        try:
            # マッチング率計算 (1 - コサイン距離) * 100
            if v_dist is not None:
                match_rate = int(max(0, min(100, (1 - float(v_dist)) * 100)))
            else:
                match_rate = 0 # データがない場合は0%

            response_list.append(ApplicationRequestItem(
                id=app.application_id,
                passengerName=user.name,
                matchingRate=match_rate,
                rating=float(profile.rating) if profile else 0.0,
                reviewCount=int(profile.ride_count) if profile else 0,
                departure=route.depname or "不明",
                destination=route.arrname or "不明",
                departureTime=route.dep_time.strftime("%m/%d %H:%M") if route.dep_time else "-",
                createdAt=datetime.now().strftime("%Y/%m/%d") # 本来はapp.created_at
            ))
        except Exception as e:
            print(f"データ変換エラー: {e}")
            continue

    return ApplicationListResponse(requests=response_list)