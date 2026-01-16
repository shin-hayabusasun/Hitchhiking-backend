from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
# ★追加: DB側での型キャスト用
from sqlalchemy import cast, Numeric
from pydantic import BaseModel
from typing import List
from datetime import datetime
import sys
import logging

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

# --- ログの設定 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/driver", tags=["driver"])

# ---------------------------------------------------------
# Helper Functions -> 削除 (DB内で完結するため不要)
# ---------------------------------------------------------

# ---------------------------------------------------------
# Pydantic Models
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
async def get_driver_requests(request: Request, status: str = "pending", db: Session = Depends(get_db)):
    """
    申請一覧取得 (pgvector対応版)
    """
    logger.info("=== 申請一覧取得開始（ドライバーモード） ===")
    
    # 1. 認証
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_driver_id = int(res)
    logger.info(f"セッション確認: session_id={session_id[:10]}..., current_driver_id={current_driver_id}")

    # 2. ドライバー自身のベクトル取得
    driver_profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == current_driver_id
    ).first()
    driver_embedding = driver_profile.embedding if driver_profile else None

    # 3. データ取得 (status=0: pending)
    target_status = 0

    # 申請者のPassengerProfileとの距離を計算するクエリを構築
    if driver_embedding is not None:
        # pgvectorのcosine_distanceを使用
        dist_col = modelDB.PassengerProfile.embedding.cosine_distance(driver_embedding).label("v_dist")
        query = db.query(
            modelDB.Application,
            modelDB.Recruitment,
            modelDB.User,
            modelDB.PassengerProfile,
            modelDB.Route,
            dist_col
        )
    else:
        # ベクトルがない場合は距離Noneとして扱う
        query = db.query(
            modelDB.Application,
            modelDB.Recruitment,
            modelDB.User,
            modelDB.PassengerProfile,
            modelDB.Route,
            cast(None, Numeric).label("v_dist")
        )

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
        modelDB.Recruitment.recruiter_user_id == current_driver_id,
        modelDB.Recruitment.type == 0,  # ドライバー募集のみに絞る
        modelDB.Application.status == target_status
    ).all()

    logger.info(f"SQLフィルタリング完了: {len(results)} 件の申請を取得（recruiter={current_driver_id}, type=0, status={target_status}）")
    
    # 4. 整形
    response_list = []
    for app, recruit, user, profile, route, v_dist in results:
        logger.info(f"申請詳細: app_id={app.application_id}, recruit_id={recruit.recruitment_id}, "
                   f"募集者={recruit.recruiter_user_id}, 申請者={app.applicant_user_id}, "
                   f"type={recruit.type}, status={app.status}")
        try:
            rating_val = float(profile.rating) if profile else 0.0
            review_count_val = profile.ride_count if profile else 0
            
            # マッチング率計算 (1 - コサイン距離) * 100
            current_dist = float(v_dist) if v_dist is not None else None
            if current_dist is not None:
                match_rate = int(max(0, min(100, (1 - current_dist) * 100)))
            else:
                match_rate = 50 # デフォルト値

            # DBに保存された地名をそのまま使用
            dep_str = route.depname if route.depname else "出発地情報なし"
            des_str = route.arrname if route.arrname else "目的地情報なし"
            
            dep_time_str = route.dep_time.strftime('%Y/%m/%d %H:%M')
            created_at_str = datetime.now().strftime('%Y/%m/%d')

            response_list.append(ApplicationRequestItem(
                id=app.application_id,
                passengerName=user.name,
                matchingRate=match_rate,
                rating=rating_val,
                reviewCount=review_count_val,
                departure=dep_str,
                destination=des_str,
                departureTime=dep_time_str,
                createdAt=created_at_str
            ))
        except Exception as e:
            logger.error(f"申請処理エラー (app_id={app.application_id}): {e}")
            continue

    logger.info(f"最終レスポンス件数: {len(response_list)} 件")
    return ApplicationListResponse(requests=response_list)