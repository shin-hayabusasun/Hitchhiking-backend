from fastapi import APIRouter, Depends, HTTPException, Request, Path
from sqlalchemy.orm import Session
from sqlalchemy import cast, Numeric
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sys
import numpy as np # 高速計算用

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/driver", tags=["request_detail"])

# --- Helper Functions ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def calculate_cosine_similarity(vec1, vec2) -> int:
    """
    ベクトルのコサイン類似度を計算し、0-100のスコアで返す
    numpyを使用しているため高速です。
    """
    if vec1 is None or vec2 is None:
        return 50 # どちらかのデータがない場合は中間値を返す
    try:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 50
            
        cos_sim = np.dot(v1, v2) / (norm1 * norm2)
        # -1~1 を 0~100 に変換 (近いほど100)
        return int(max(0, cos_sim) * 100)
    except Exception:
        return 50

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
    """
    同乗者募集の詳細を取得する
    """
    # 1. 認証 (ドライバー)
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401)
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no": raise HTTPException(status_code=401)
    current_driver_id = int(user_id_str)

    # 2. ドライバー自身の情報を取得 (マッチング計算用)
    driver_profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == current_driver_id
    ).first()
    driver_embedding = driver_profile.embedding if driver_profile else None

    # 3. 募集情報の取得 (type=1: 同乗者募集)
    # Recruitment, Route, User(Passenger), PassengerProfile を結合
    target = db.query(
        modelDB.Recruitment,
        modelDB.Route,
        modelDB.User,
        modelDB.PassengerProfile
    ).join(
        modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).join(
        modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id
    ).outerjoin(
        modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id
    ).filter(
        modelDB.Recruitment.recruitment_id == request_id,
        modelDB.Recruitment.type == 1  # 同乗者募集のみ対象
    ).first()

    if not target:
        raise HTTPException(status_code=404, detail="募集が見つかりません")

    recruit, route, user, profile = target

    # 4. データ整形
    
    # ★地名はDBから直接取得 (逆ジオコーディング不要で高速)
    origin_name = getattr(route, 'depname', '出発地不明')
    arr_name = getattr(route, 'arrname', '目的地不明')

    # ★マッチングスコア計算 (numpy)
    passenger_embedding = profile.embedding if profile else None
    score = calculate_cosine_similarity(driver_embedding, passenger_embedding)

    # 年齢計算 (簡易ロジック)
    age = 0
    if user.birth_date:
        today = datetime.today()
        age = today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))

    res_data = RequestDetailResponse(
        request=RequestData(
            id=recruit.recruitment_id,
            origin=origin_name,
            destination=arr_name,
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
        matchingScore=score
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

    # 排他制御付きで募集を取得 (with_for_update)
    recruit = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == data.recruitment_id,
        modelDB.Recruitment.type == 1, # 同乗者募集
        modelDB.Recruitment.status == 0 # 募集中
    ).with_for_update().first()

    if not recruit:
        raise HTTPException(status_code=400, detail="この募集は既に締め切られています")

    try:
        # 1. 募集ステータスを「マッチ済み(2)」に変更
        recruit.status = 2
        
        # 2. Applicationレコードを作成 (即承認状態: status=1)
        # applicant_user_id は「応募した側（ドライバー）」になります
        new_app = modelDB.Application(
            recruitment_id=recruit.recruitment_id,
            applicant_user_id=current_driver_id, 
            status=1, # 承認済み
            chat_id=0 
        )
        
        # チャットルームの作成
        new_chat = modelDB.Chat(message="マッチングが成立しました！よろしくお願いします。")
        db.add(new_chat)
        db.flush()
        new_app.chat_id = new_chat.chat_id

        db.add(new_app)
        db.commit()

        return ResponseData(success=True)

    except Exception as e:
        db.rollback()
        print(f"Error responding: {e}")
        raise HTTPException(status_code=500, detail="処理に失敗しました")