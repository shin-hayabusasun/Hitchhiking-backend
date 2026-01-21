from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import sys
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user # 既存の認証関数をインポート
from geopy.geocoders import Nominatim # ★追加

# レスポンスモデルの定義
from pydantic import BaseModel
from datetime import datetime

# 同乗者情報のモデル
class PassengerInfo(BaseModel):
    userId: int
    name: str

class DriveResponse(BaseModel):
    id: int  # recruitment_id
    departure: str
    destination: str
    departureTime: datetime
    fee: int
    capacity: int
    currentPassengers: int # 現在の同乗者数（計算が必要）
    status: str # フロントエンドのステータス文字列に変換
    approvedPassengers: List[PassengerInfo] # ★追加: 承認済み同乗者リスト

class DriveListResponse(BaseModel):
    drives: List[DriveResponse]

router = APIRouter(prefix="/api/driver", tags=["driver"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
# ★修正: 住所変換関数
def get_location_name(lat, lon) -> str:
    """LocationIQ APIを使用して逆ジオコーディング（座標→住所）"""
    import requests
    import os
    
    # 1. 値の存在チェック
    if lat is None or lon is None:
        return "場所情報なし"
    
    api_key = os.getenv("LOCATIONIQ_API_KEY", "pk.4c89f676c0053659bd58a6708715b00e")
    
    try:
        # 2. 型変換 (Decimal -> float)
        lat_f = float(lat)
        lon_f = float(lon)
        
        # 3. LocationIQ API呼び出し
        url = "https://us1.locationiq.com/v1/reverse.php"
        params = {
            "key": api_key,
            "lat": lat_f,
            "lon": lon_f,
            "format": "json",
            "accept-language": "ja"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and 'address' in data:
            addr = data['address']
            
            # 都道府県、市町村、町名などを結合
            state = addr.get('province', addr.get('state', ''))
            city = addr.get('city', addr.get('town', addr.get('village', '')))
            suburb = addr.get('suburb', addr.get('neighbourhood', ''))
            road = addr.get('road', '')
            
            # 見やすい形式に整形
            if city and road:
                return f"{city} {road}"
            if city and suburb:
                return f"{city} {suburb}"
            if 'display_name' in data:
                return data['display_name'].split(',')[0]

    except Exception as e:
        # エラー詳細をコンソールに出す（デバッグ用）
        print(f"GeoError: {e} (Lat:{lat}, Lon:{lon})")
    
    # 失敗時は座標を返す
    return f"地点({lat}, {lon})"
@router.get("/drives", response_model=DriveListResponse)
async def get_my_drives(
    request: Request, 
    status: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """
    マイドライブ一覧取得API
    """
    # 1. 認証
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401, detail="Unauthorized")
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no": raise HTTPException(status_code=401, detail="Invalid session")
    user_id = int(user_id_str)

    # 2. クエリ構築 (自分の「運転者としての募集」を取得)
    query = db.query(modelDB.Recruitment, modelDB.Route).\
        join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id).\
        filter(
            modelDB.Recruitment.recruiter_user_id == user_id,
            modelDB.Recruitment.type == 0  # ★重要: 運転者募集のみに絞る
        )

    # 3. ステータスフィルタリング (修正・追加部分)
    if status:
        if status == 'recruiting':
            query = query.filter(modelDB.Recruitment.status == 0)
        elif status == 'matched':
            query = query.filter(modelDB.Recruitment.status == 1)
        elif status == 'completed':
            query = query.filter(modelDB.Recruitment.status == 2)
        elif status == 'cancelled':
            query = query.filter(modelDB.Recruitment.status == 3)

    # 日時順（新しいものが上）
    drives_data = query.order_by(desc(modelDB.Route.dep_time)).all()

    response_list = []
    
    for recruitment, route in drives_data:
        try:
            # 同乗者情報の取得 (承認済みの人だけ)
            approved_apps = db.query(modelDB.Application, modelDB.User).\
                join(modelDB.User, modelDB.Application.applicant_user_id == modelDB.User.user_id).\
                filter(
                    modelDB.Application.recruitment_id == recruitment.recruitment_id,
                    modelDB.Application.status == 1 # 承認済み
                ).all()

            passenger_list = []
            for app, user in approved_apps:
                passenger_list.append(PassengerInfo(
                    userId=user.user_id,
                    name=user.name
                ))

            # ステータス文字列変換 (フロントエンド用)
            status_str = "recruiting"
            if recruitment.status == 1: status_str = "matched"
            elif recruitment.status == 2: status_str = "completed"
            elif recruitment.status == 3: status_str = "cancelled"

            departure_name = route.depname if route.depname else "出発地未設定"
            destination_name = route.arrname if route.arrname else "目的地未設定"

            response_list.append(DriveResponse(
                id=recruitment.recruitment_id,
                departure=departure_name, 
                destination=destination_name,
                departureTime=route.dep_time,
                fee=recruitment.fare,
                capacity=recruitment.capacity,
                currentPassengers=len(passenger_list),
                status=status_str,
                approvedPassengers=passenger_list
            ))
        except Exception as e:
            print(f"Error processing drive {recruitment.recruitment_id}: {e}")
            continue

    return DriveListResponse(drives=response_list)