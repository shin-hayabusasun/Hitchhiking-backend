import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Path
from sqlalchemy.orm import Session
from sqlalchemy import cast, Numeric
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sys

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user
from app.name.tadokoro.notific import create_notification

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/driver", tags=["request_detail"])

# --- Helper Functions ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---
class PassengerDetail(BaseModel):
    id: int
    name: str
    age: int
    gender: int
    rating: float
    reviewCount: int
    profileImage: str = ""
    bio: str = ""

class RequestData(BaseModel):
    id: int
    origin: str
    destination: str
    # 同乗者の緯度経度
    originLatitude: Optional[float] = None
    originLongitude: Optional[float] = None
    destinationLatitude: Optional[float] = None
    destinationLongitude: Optional[float] = None
    date: str
    time: str
    budget: int
    passengerCount: int
    message: str = ""
    status: str

class RequestDetailResponse(BaseModel):
    request: RequestData
    passenger: PassengerDetail
    matchingScore: int

class ResponseData(BaseModel):
    success: bool
    data: Optional[RequestDetailResponse] = None

class RespondBody(BaseModel):
    recruitment_id: int

# --- API Endpoints ---

@router.get("/search/{request_id}", response_model=ResponseData)
async def get_request_detail(
    request: Request,
    request_id: int = Path(..., title="Recruitment ID"),
    db: Session = Depends(get_db)
):
    # 1. 認証
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401)
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no": raise HTTPException(status_code=401)
    current_driver_id = int(user_id_str)

    # 2. ドライバー自身の情報を取得
    driver_profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == current_driver_id
    ).first()
    
    driver_embedding = driver_profile.embedding if driver_profile else None

    # 3. クエリ構築 (検索APIと同じDB内計算を使用)
    if driver_embedding is not None:
        # pgvectorで距離を計算 (0に近いほど似ている)
        dist_col = modelDB.PassengerProfile.embedding.cosine_distance(driver_embedding).label("v_dist")
        query = db.query(
            modelDB.Recruitment,
            modelDB.Route,
            modelDB.User,
            modelDB.PassengerProfile,
            dist_col 
        )
    else:
        # ベクトルがない場合は距離なし(None)
        query = db.query(
            modelDB.Recruitment,
            modelDB.Route,
            modelDB.User,
            modelDB.PassengerProfile,
            cast(None, Numeric).label("v_dist")
        )

    # 4. 募集情報の取得
    target = query.join(
        modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).join(
        modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id
    ).outerjoin(
        modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id
    ).filter(
        modelDB.Recruitment.recruitment_id == request_id,
        modelDB.Recruitment.type == 1 
    ).first()

    if not target:
        raise HTTPException(status_code=404, detail="募集が見つかりません")

    # アンパック
    recruit, route, user, profile, v_dist = target

    # 5. データ整形
    
    # 地名
    origin_name = getattr(route, 'depname', '出発地不明')
    arr_name = getattr(route, 'arrname', '目的地不明')

    # マッチングスコア計算
    current_dist = float(v_dist) if v_dist is not None else None
    if current_dist is not None:
        match_score = int(max(0, min(100, (1 - current_dist) * 100)))
    else:
        match_score = 50

    # 年齢計算
    age = 0
    if user.birth_date:
        today = datetime.today()
        age = today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))

    res_data = RequestDetailResponse(
        request=RequestData(
            id=recruit.recruitment_id,
            origin=origin_name,
            destination=arr_name,
            # ★必須：同乗者の緯度経度
            originLatitude=float(route.dep_latitude) if route and route.dep_latitude else None,
            originLongitude=float(route.dep_longitude) if route and route.dep_longitude else None,
            destinationLatitude=float(route.arr_latitude) if route and route.arr_latitude else None,
            destinationLongitude=float(route.arr_longitude) if route and route.arr_longitude else None,
            date=route.dep_time.strftime('%Y-%m-%d'),
            time=route.dep_time.strftime('%H:%M'),
            budget=recruit.fare,
            passengerCount=recruit.capacity,
            message=profile.bio if profile and profile.bio else "よろしくお願いします。", 
            status="active" if recruit.status == 0 else "closed"
        ),
        passenger=PassengerDetail(
            id=user.user_id,
            name=user.name,
            age=age,
            gender=user.gender,
            rating=float(profile.rating) if profile else 0.0,
            reviewCount=int(profile.ride_count) if profile else 0,
            profileImage="",
            bio=profile.bio if profile else ""
        ),
        matchingScore=match_score
    )

    return ResponseData(success=True, data=res_data)


@router.post("/respond", response_model=ResponseData)
async def respond_to_request(
    request: Request,
    data: RespondBody,
    db: Session = Depends(get_db)
):
    """
    募集に応答してマッチングを確定させるAPI
    """
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401)
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no": raise HTTPException(status_code=401)
    current_driver_id = int(user_id_str)

    # 排他制御
    recruit = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == data.recruitment_id,
        modelDB.Recruitment.type == 1,
        modelDB.Recruitment.status == 0 
    ).with_for_update().first()

    if not recruit:
        raise HTTPException(status_code=400, detail="この募集は既に締め切られています")

    try:
        # 1. ステータス変更
        recruit.status = 1
        
        # 2. Application作成
        new_app = modelDB.Application(
            recruitment_id=recruit.recruitment_id,
            applicant_user_id=current_driver_id, 
            status=1  # 承認済み
        )
        db.add(new_app)
        db.flush()
        
        # 3. Chat作成
        new_chat = modelDB.Chat(
            user_id=current_driver_id,
            message="マッチングが成立しました！よろしくお願いします。",
            application_id=new_app.application_id 
        )
        db.add(new_chat)
        
        db.commit()
        
        # 4. 募集者に通知を送る
        driver_user = db.query(modelDB.User).filter(
            modelDB.User.user_id == current_driver_id
        ).first()
        driver_name = driver_user.name if driver_user else "ドライバー"
        
        create_notification(
            db=db,
            user_id=recruit.recruiter_user_id,
            message=f"{driver_name}さんがあなたの募集に応答しました！マッチングが成立しました。"
        )
        
        return ResponseData(success=True)

    except Exception as e:
        db.rollback()
        print(f"Error responding: {e}")
        raise HTTPException(status_code=500, detail="処理に失敗しました")