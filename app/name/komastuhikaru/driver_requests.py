# import logging # ★追加
# from fastapi import APIRouter, Depends, HTTPException, Request
# from sqlalchemy.orm import Session
# from sqlalchemy import cast, Numeric
# from pydantic import BaseModel
# from typing import List
# from datetime import datetime, timedelta
# import sys

# # パス設定
# sys.path.append('..')
# from db_setting import SessionLocal
# import modelDB
# from app.name.hieda.user import get_current_user

# # ★ログ設定を追加 (参考コードに合わせる)
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/api/driver", tags=["driver"])

# # ---------------------------------------------------------
# # Pydantic Models
# # ---------------------------------------------------------
# class ApplicationRequestItem(BaseModel):
#     id: int
#     passengerName: str
#     matchingRate: int
#     rating: float
#     reviewCount: int
#     departure: str
#     destination: str
#     departureTime: str
#     createdAt: str

# class ApplicationListResponse(BaseModel):
#     requests: List[ApplicationRequestItem]

# # ---------------------------------------------------------
# # Dependency
# # ---------------------------------------------------------
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # ---------------------------------------------------------
# # API Endpoint
# # ---------------------------------------------------------
# @router.get("/requests", response_model=ApplicationListResponse)
# async def get_driver_requests(request: Request, status: str = "pending", db: Session = Depends(get_db)):
#     """
#     申請一覧取得 (ドライバー向け)
#     自分が「運転者として」作成した募集への申請のみを表示
#     """
#     logger.info("=== 申請一覧取得API (get_driver_requests) 開始 ===")

#     # 1. 認証
#     session_id = request.cookies.get("session_id")
#     if not session_id: raise HTTPException(status_code=401, detail="Unauthorized")

#     res = get_current_user(session_id=session_id, db=db)
#     if res == "no": raise HTTPException(status_code=401, detail="Invalid session")
    
#     current_driver_id = int(res)

#     # ★デバッグログ: 誰がログインしているか確認
#     logger.info(f"アクセスユーザーID (current_driver_id): {current_driver_id}")

#     # 2. ドライバー自身のベクトル取得
#     driver_profile = db.query(modelDB.DriverProfile).filter(
#         modelDB.DriverProfile.user_id == current_driver_id
#     ).first()
#     driver_embedding = driver_profile.embedding if driver_profile else None

#     # 3. データ取得 (status=0: pending)
#     target_status = 0

#     # クエリ構築
#     if driver_embedding is not None:
#         dist_col = modelDB.PassengerProfile.embedding.cosine_distance(driver_embedding).label("v_dist")
#         query = db.query(
#             modelDB.Application,
#             modelDB.Recruitment,
#             modelDB.User,
#             modelDB.PassengerProfile,
#             modelDB.Route,
#             dist_col
#         )
#     else:
#         query = db.query(
#             modelDB.Application,
#             modelDB.Recruitment,
#             modelDB.User,
#             modelDB.PassengerProfile,
#             modelDB.Route,
#             cast(None, Numeric).label("v_dist")
#         )

#     # 現在時刻 (JST補正)
#     now = datetime.utcnow() + timedelta(hours=9)
#     logger.info(f"現在時刻(JST基準): {now}")

#     # フィルタリング実行
#     results = query.join(
#         modelDB.Recruitment,
#         modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
#     ).join(
#         modelDB.User,
#         modelDB.Application.applicant_user_id == modelDB.User.user_id
#     ).outerjoin(
#         modelDB.PassengerProfile,
#         modelDB.User.user_id == modelDB.PassengerProfile.user_id
#     ).join(
#         modelDB.Route,
#         modelDB.Recruitment.route_id == modelDB.Route.route_id
#     ).filter(
#         # ★重要1: 自分が作成した募集であること
#         modelDB.Recruitment.recruiter_user_id == current_driver_id,
        
#         # ★重要2: 「運転者募集 (type=0)」に限定する
#         modelDB.Recruitment.type == 0,

#         # ステータスと日時のフィルタ
#         modelDB.Application.status == target_status,
#         modelDB.Route.dep_time >= now 
#     ).all()

#     # ★デバッグログ: SQLヒット件数
#     logger.info(f"SQLヒット件数: {len(results)} 件")

#     # 4. 整形
#     response_list = []
#     for app, recruit, user, profile, route, v_dist in results:
#         # ★詳細デバッグログ: 1件ごとの詳細を確認
#         logger.info(f"--- データ詳細 ---")
#         logger.info(f"  Application ID: {app.application_id}")
#         logger.info(f"  Recruit Owner ID: {recruit.recruiter_user_id} (Expected: {current_driver_id})")
#         logger.info(f"  Applicant Name: {user.name}")
#         logger.info(f"  Departure Time: {route.dep_time}")

#         # ID不一致チェック (本来ありえないが念のため)
#         if recruit.recruiter_user_id != current_driver_id:
#             logger.error(f"【異常】他人の募集データが混入しています！ Owner: {recruit.recruiter_user_id}, Current: {current_driver_id}")

#         try:
#             rating_val = float(profile.rating) if profile else 0.0
#             review_count_val = profile.ride_count if profile else 0
            
#             # マッチング率計算
#             current_dist = float(v_dist) if v_dist is not None else None
#             if current_dist is not None:
#                 match_rate = int(max(0, min(100, (1 - current_dist) * 100)))
#             else:
#                 match_rate = 50 

#             dep_str = route.depname if route.depname else "出発地情報なし"
#             des_str = route.arrname if route.arrname else "目的地情報なし"
            
#             dep_time_str = route.dep_time.strftime('%Y/%m/%d %H:%M')
#             created_at_str = datetime.now().strftime('%Y/%m/%d') # 本来は app.created_at

#             response_list.append(ApplicationRequestItem(
#                 id=app.application_id,
#                 passengerName=user.name,
#                 matchingRate=match_rate,
#                 rating=rating_val,
#                 reviewCount=review_count_val,
#                 departure=dep_str,
#                 destination=des_str,
#                 departureTime=dep_time_str,
#                 createdAt=created_at_str
#             ))
#         except Exception as e:
#             logger.error(f"Error processing item: {e}")
#             continue

#     return ApplicationListResponse(requests=response_list)
import logging # ★必須
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import cast, Numeric
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
import sys

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

# ★ログ設定 (Uvicornのログ形式に合わせる)
logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/driver", tags=["driver"])

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
    申請一覧取得 (ドライバー向け)
    """
    # ★目印ログ (これがログに出なければ、コードが更新されていません)
    logger.info("🔰🔰🔰 申請一覧API (get_driver_requests) が呼ばれました 🔰🔰🔰")

    # 1. 認証
    session_id = request.cookies.get("session_id")
    if not session_id: 
        logger.error("❌ エラー: セッションIDがありません")
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no": 
        logger.error("❌ エラー: セッションが無効です")
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_driver_id = int(res)
    logger.info(f"👤 アクセス中のユーザーID: {current_driver_id}")

    # 2. ドライバー自身のベクトル取得
    driver_profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == current_driver_id
    ).first()
    driver_embedding = driver_profile.embedding if driver_profile else None

    # 3. データ取得 (status=0: pending)
    target_status = 0

    # クエリ構築
    if driver_embedding is not None:
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
        query = db.query(
            modelDB.Application,
            modelDB.Recruitment,
            modelDB.User,
            modelDB.PassengerProfile,
            modelDB.Route,
            cast(None, Numeric).label("v_dist")
        )

    # 現在時刻 (JST補正)
    now = datetime.utcnow() + timedelta(hours=9)
    logger.info(f"🕒 現在時刻(JST): {now}")

    # フィルタリング実行
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
        # ★重要: 自分が作成した募集であること
        modelDB.Recruitment.recruiter_user_id == current_driver_id,
        
        # ★重要: 運転者募集 (type=0)
        modelDB.Recruitment.type == 0,

        # ステータスと日時のフィルタ
        modelDB.Application.status == target_status,
        modelDB.Route.dep_time >= now 
    ).all()

    logger.info(f"🔍 ヒットした申請数: {len(results)} 件")

    # 4. 整形
    response_list = []
    for app, recruit, user, profile, route, v_dist in results:
        logger.info(f"📋 データ詳細 -> 申請ID:{app.application_id}, 募集主ID:{recruit.recruiter_user_id}, 申請者:{user.name}")

        # ID不一致チェック
        if recruit.recruiter_user_id != current_driver_id:
            logger.error(f"😱【異常】他人の募集データが混入！ Owner:{recruit.recruiter_user_id} != User:{current_driver_id}")

        try:
            rating_val = float(profile.rating) if profile else 0.0
            review_count_val = profile.ride_count if profile else 0
            
            current_dist = float(v_dist) if v_dist is not None else None
            if current_dist is not None:
                match_rate = int(max(0, min(100, (1 - current_dist) * 100)))
            else:
                match_rate = 50 

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
            logger.error(f"⚠️ データ処理エラー: {e}")
            continue

    return ApplicationListResponse(requests=response_list)