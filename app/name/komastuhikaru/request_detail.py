from fastapi import APIRouter, Depends, HTTPException, Request, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sys
import time
import numpy as np
from geopy.geocoders import Nominatim

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/driver", tags=["driver_search"])

# ---------------------------------------------------------
# Helper Functions (既存のものを再利用)
# ---------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_location_name(lat, lon) -> str:
    if lat is None or lon is None: return "場所情報なし"
    try:
        # User-Agentはユニークなものに変更推奨
        geolocator = Nominatim(user_agent="drive_app_search_detail_v1", timeout=3)
        location = geolocator.reverse((float(lat), float(lon)), language='ja')
        if location:
            addr = location.raw.get('address', {})
            city = addr.get('city', addr.get('town', addr.get('village', '')))
            road = addr.get('road', '')
            if city and road: return f"{city} {road}"
            return location.address.split(',')[0]
    except Exception:
        pass
    return f"地点({lat}, {lon})"

def calculate_similarity(vec1: List[float], vec2: List[float]) -> int:
    if vec1 is None or vec2 is None: return 0
    try:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0: return 0
        cos_sim = np.dot(v1, v2) / (norm1 * norm2)
        return int(max(0, cos_sim) * 100)
    except Exception:
        return 0

# ---------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------
class PassengerDetail(BaseModel):
    id: int
    name: str
    age: int = 0 # DBにないので仮
    gender: int  # 1:男性, 2:女性 など
    rating: float
    reviewCount: int
    profileImage: str = "" # 仮
    bio: str = ""

class RequestData(BaseModel):
    id: int
    origin: str
    destination: str
    date: str
    time: str
    budget: int
    passengerCount: int
    message: str = "" # DBにないので仮
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

# ---------------------------------------------------------
# API 1: 同乗者募集の詳細取得
# ---------------------------------------------------------
@router.get("/search/{request_id}", response_model=ResponseData)
async def get_passenger_request_detail(
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

    # 2. ドライバー情報の取得 (マッチング率計算用)
    driver_profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == current_driver_id
    ).first()
    driver_embedding = driver_profile.embedding if driver_profile else None

    # 3. 募集情報の取得 (同乗者募集 = type 1)
    target_recruit = db.query(
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
        modelDB.Recruitment.type == 1 # 同乗者募集
    ).first()

    if not target_recruit:
        raise HTTPException(status_code=404, detail="Request not found")

    recruit, route, user, profile = target_recruit

    # 4. データ整形 & 計算
    # マッチング率
    passenger_embedding = profile.embedding if profile else None
    score = calculate_similarity(driver_embedding, passenger_embedding)

    # 地名変換
    time.sleep(1.0) # API制限対策
    origin_name = get_location_name(route.dep_latitude, route.dep_longitude)
    dest_name = get_location_name(route.arr_latitude, route.arr_longitude)

    # ステータス文字列
    status_map = {0: 'active', 1: 'matched', 2: 'completed', 3: 'cancelled'}
    status_str = status_map.get(recruit.status, 'unknown')

    # 年齢計算 (生年月日から)
    age = 0
    if user.birth_date:
        today = datetime.today()
        age = today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))

    res_data = RequestDetailResponse(
        request=RequestData(
            id=recruit.recruitment_id,
            origin=origin_name,
            destination=dest_name,
            date=route.dep_time.strftime('%Y-%m-%d'),
            time=route.dep_time.strftime('%H:%M'),
            budget=recruit.fare,
            passengerCount=recruit.capacity, # 同乗希望人数
            message=profile.bio if profile and profile.bio else "よろしくお願いします。", # 仮
            status=status_str
        ),
        passenger=PassengerDetail(
            id=user.user_id,
            name=user.name,
            age=age,
            gender=user.gender,
            rating=float(profile.rating) if profile else 0.0,
            reviewCount=profile.ride_count if profile else 0,
            profileImage="", # DBにないので空
            bio=profile.bio if profile else ""
        ),
        matchingScore=score
    )

    return ResponseData(success=True, data=res_data)


# ---------------------------------------------------------
# API 2: 募集への応答（即確定）
# ---------------------------------------------------------
@router.post("/respond", response_model=ResponseData)
async def respond_to_request(
    request: Request,
    data: RespondBody,
    db: Session = Depends(get_db)
):
    """
    運転者が同乗者の募集に応答するAPI
    申請→承認プロセスをスキップし、即座にマッチング成立（確定）とします。
    """
    # 1. 認証
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401)
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no": raise HTTPException(status_code=401)
    current_driver_id = int(user_id_str)

    # 2. 募集データの取得とロック
    # with_for_update() で同時実行制御（排他ロック）
    recruit = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == data.recruitment_id,
        modelDB.Recruitment.type == 1, # 同乗者募集のみ
        modelDB.Recruitment.status == 0 # 募集中のみ
    ).with_for_update().first()

    if not recruit:
        raise HTTPException(status_code=400, detail="This request is not available or already matched.")

    try:
        # 3. マッチング成立処理
        # ステータスを「募集終了(確定)」に変更
        recruit.status = 1 
        
        # どのドライバーが応答したかを記録する必要がありますが、
        # 現在のDB設計では Recruitment テーブルに応答者IDカラムがなさそうです。
        # 代わりに「Application」テーブルを使って「承認済み」として記録を残します。
        
        # Applicationレコード作成 (status=1: 承認済み)
        # applicant_user_id = 応答したドライバー
        new_app = modelDB.Application(
            recruitment_id=recruit.recruitment_id,
            applicant_user_id=current_driver_id,
            status=1, # 最初から承認済み
            # chat_id は必須だが、まだチャットルームがない場合はどうするか要検討
            # ここでは仮に None または ダミーを入れる必要がありますが、DB制約によります
            # 今回は chat_id=0 か、別途チャット作成ロジックが必要
            chat_id=0 # TODO: Chatテーブルを作成してそのIDを入れるのが正しい
        )
        
        # ※Chatテーブルの作成が必要な場合
        new_chat = modelDB.Chat(message="マッチングが成立しました！")
        db.add(new_chat)
        db.flush() # chat_idを取得
        new_app.chat_id = new_chat.chat_id

        db.add(new_app)
        db.commit()

        return ResponseData(success=True)

    except Exception as e:
        db.rollback()
        print(f"Error responding to request: {e}")
        raise HTTPException(status_code=500, detail="Failed to respond")