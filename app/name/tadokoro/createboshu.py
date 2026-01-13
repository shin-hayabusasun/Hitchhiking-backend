import sys
import json
import requests
import secrets
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from geopy.geocoders import Nominatim

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/hitchhiker", tags=["recruitment"])

# --- ヘルパー関数 ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_coordinates(address: str):
    """地名から座標を取得（Nominatim使用）"""
    geocoder = Nominatim(user_agent="hitchhiker_app_v2026", timeout=10)
    try:
        # 日本国内を優先的に検索
        location = geocoder.geocode(f"{address}, Japan")
        if location:
            return location.latitude, location.longitude
    except:
        return None, None
    return None, None

def get_actual_route(start_lat, start_lon, end_lat, end_lon):
    """OSRM APIを使用して実際の道路に沿った経路と所要時間を取得"""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('code') == 'Ok':
            coords = data['routes'][0]['geometry']['coordinates']
            path_points = [[c[1], c[0]] for c in coords]
            duration = data['routes'][0]['duration']  # 秒
            return path_points, duration
    except Exception as e:
        print(f"経路探索エラー: {e}")
    
    # 失敗時は直線距離を想定（デフォルト3時間）
    return [[start_lat, start_lon], [end_lat, end_lon]], 10800

# --- スキーマ定義 ---

class RecruitmentCreate(BaseModel):
    departure: str # 地名
    destination: str #  地名
    departureDate: str  # YYYY-MM-DD
    departureTime: str  # HH:mm
    capacity: int
    fee: int
    message: str

class RecruitmentResponse(BaseModel):
    ok: bool
    recruitment_id: Optional[int] = None

class RecruitmentItem(BaseModel):
    id: int
    status: str
    statusText: str
    appliedDate: str
    userName: str
    rating: str
    reviews: str
    from_location: str
    to_location: str
    date: str
    people: str
    price: str

class RecruitmentListResponse(BaseModel):
    success: bool
    data: List[RecruitmentItem]

# --- API処理 ---

@router.post("/regist_recruitment", response_model=RecruitmentResponse)
async def regist_recruitment(
    data: RecruitmentCreate, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    1. 新規募集および経路の登録
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="セッションがありません")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="ログインが必要です")
    
    user_id = int(res)

    # 座標取得
    dep_lat, dep_lon = get_coordinates(data.departure)
    arr_lat, arr_lon = get_coordinates(data.destination)

    if dep_lat is None or arr_lat is None:
        raise HTTPException(status_code=400, detail="地点の座標取得に失敗しました")

    # 経路と所要時間計算
    path_points, duration_sec = get_actual_route(dep_lat, dep_lon, arr_lat, arr_lon)

    # 到着予想日時の計算
    try:
        dep_datetime = datetime.strptime(f"{data.departureDate} {data.departureTime}", "%Y-%m-%d %H:%M")
        arr_datetime = dep_datetime + timedelta(seconds=duration_sec)
    except ValueError:
        raise HTTPException(status_code=400, detail="日時の形式が不正です")

    try:
        # Route登録
        new_route = modelDB.Route(
            recruiter_user_id=user_id,
            path_data=json.dumps(path_points),
            dep_time=dep_datetime,
            dep_latitude=dep_lat,
            dep_longitude=dep_lon,
            arr_time=arr_datetime,
            arr_latitude=arr_lat,
            arr_longitude=arr_lon,
            arrname=data.destination,
            depname=data.departure
        )
        db.add(new_route)
        db.flush()

        # Recruitment登録
        new_recruitment = modelDB.Recruitment(
            recruiter_user_id=user_id,
            status=0,  # 募集中
            fare=data.fee,
            capacity=data.capacity,
            type=1,    # 同乗者募集
            route_id=new_route.route_id
        )
        db.add(new_recruitment)
        db.commit()

        return RecruitmentResponse(ok=True, recruitment_id=new_recruitment.recruitment_id)

    except Exception as e:
        db.rollback()
        print(f"募集登録エラー: {e}")
        raise HTTPException(status_code=500, detail="登録に失敗しました")

@router.get("/my_recruitments", response_model=RecruitmentListResponse)
async def get_my_recruitments(request: Request, db: Session = Depends(get_db)):
    """
    2. 自分が作成した募集一覧の取得
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = int(res)

    # テーブル結合（募集、経路、ユーザー、プロフィール）
    results = db.query(
        modelDB.Recruitment,
        modelDB.Route,
        modelDB.User,
        modelDB.PassengerProfile
    ).join(
        modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).join(
        modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id
    ).join(
        modelDB.PassengerProfile, modelDB.User.user_id == modelDB.PassengerProfile.user_id
    ).filter(
        modelDB.Recruitment.recruiter_user_id == user_id,
        modelDB.Recruitment.type == 1  # ここに追加
    ).all()

    response_data = []
    for rec, route, user, profile in results:
        status_map = {
            0: ("OPEN", "募集中"),
            1: ("MATCHED", "マッチ済み"),
            2: ("COMPLETED", "運転完了")
        }
        status_val, status_text = status_map.get(rec.status, ("UNKNOWN", "不明"))

        item = RecruitmentItem(
            id=rec.recruitment_id,
            status=status_val,
            statusText=status_text,
            appliedDate=route.dep_time.strftime("%Y.%m.%d"),
            userName=user.name,
            rating=str(profile.rating),
            reviews=str(profile.ride_count),
            from_location=route.depname,
            to_location=route.arrname,
            date=route.dep_time.strftime("%m-%d %H:%M"),
            people=str(rec.capacity),
            price=str(rec.fare)
        )
        response_data.append(item)

    return RecruitmentListResponse(success=True, data=response_data)
# --- スキーマ定義 ---

class RecruitmentUpdate(BaseModel):
    recruitment_id: int  # どの募集を更新するか
    departure: str
    destination: str
    departureDate: str  # YYYY-MM-DD
    departureTime: str  # HH:mm
    capacity: int
    fee: int
    message: str  # DB保存対象外

class UpdateResponse(BaseModel):
    ok: bool
    message: Optional[str] = None

# --- API処理 ---

@router.post("/update_recruitment", response_model=UpdateResponse)
async def update_recruitment(
    data: RecruitmentUpdate, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    既存の募集内容を編集するAPI
    """
    # 1. セッション確認とユーザー特定
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = int(res)

    # 2. 対象の募集データが存在するか、かつ本人のものか確認
    recruitment = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == data.recruitment_id,
        modelDB.Recruitment.recruiter_user_id == user_id
    ).first()

    if not recruitment:
        raise HTTPException(status_code=404, detail="指定された募集が見つからないか、編集権限がありません")

    # 3. 新しい地点の座標を取得
    dep_lat, dep_lon = get_coordinates(data.departure)
    arr_lat, arr_lon = get_coordinates(data.destination)

    if dep_lat is None or arr_lat is None:
        raise HTTPException(status_code=400, detail="地点の座標取得に失敗しました")

    # 4. 新しい経路計算
    path_points, duration_sec = get_actual_route(dep_lat, dep_lon, arr_lat, arr_lon)

    # 5. 日時の計算
    try:
        dep_datetime = datetime.strptime(f"{data.departureDate} {data.departureTime}", "%Y-%m-%d %H:%M")
        arr_datetime = dep_datetime + timedelta(seconds=duration_sec)
    except ValueError:
        raise HTTPException(status_code=400, detail="日時の形式が不正です")

    try:
        # 6. Routeテーブルの更新
        route = db.query(modelDB.Route).filter(modelDB.Route.route_id == recruitment.route_id).first()
        if route:
            route.path_data = json.dumps(path_points)
            route.dep_time = dep_datetime
            route.dep_latitude = dep_lat
            route.dep_longitude = dep_lon
            route.arr_time = arr_datetime
            route.arr_latitude = arr_lat
            route.arr_longitude = arr_lon
            route.depname = data.departure
            route.arrname = data.destination

        # 7. Recruitmentテーブルの更新
        recruitment.fare = data.fee
        recruitment.capacity = data.capacity
        # ステータスは「募集中(1)」のまま維持する想定
        
        db.commit()
        return UpdateResponse(ok=True)

    except Exception as e:
        db.rollback()
        print(f"募集更新エラー: {e}")
        raise HTTPException(status_code=500, detail="更新に失敗しました")

 
 # --- 追加のスルキーマ定義 ---

class RecruitmentDetailData(BaseModel):
    recruitment_id: int
    dep_time: str
    dep_latitude: str
    arr_latitude: str
    capacity: int
    fare: int
    message: Optional[str] = ""
    departure_name: Optional[str] = None
    destination_name: Optional[str] = None

class RecruitmentDetailResponse(BaseModel):
    ok: bool
    data: Optional[RecruitmentDetailData] = None

class DeleteResponse(BaseModel):
    ok: bool

# --- 追加のAPIエンドポイント ---

@router.get("/recruitment_detail", response_model=RecruitmentDetailResponse)
async def get_recruitment_detail(
    recruitment_id: int, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    特定の募集詳細を取得するAPI
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = int(res)

    # 本人の募集であることも確認して取得
    result = db.query(modelDB.Recruitment, modelDB.Route).join(
        modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).filter(
        modelDB.Recruitment.recruitment_id == recruitment_id,
        modelDB.Recruitment.recruiter_user_id == user_id
    ).first()

    if not result:
        return RecruitmentDetailResponse(ok=False, data=None)

    rec, route = result

    detail = RecruitmentDetailData(
        recruitment_id=rec.recruitment_id,
        dep_time=route.dep_time.strftime("%Y-%m-%d %H:%M"),
        dep_latitude=str(route.dep_latitude),
        arr_latitude=str(route.arr_latitude),
        capacity=rec.capacity,
        fare=rec.fare,
        message="", 
        departure_name=route.depname,
        destination_name=route.arrname
    )

    return RecruitmentDetailResponse(ok=True, data=detail)


@router.post("/delete_recruitment", response_model=DeleteResponse)
async def delete_recruitment(
    recruitment_id: int, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    募集を削除（論理削除）するAPI
    """
    session_id = request.cookies.get("session_id")
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401)
    
    user_id = int(res)

    # 本人の募集か確認
    recruitment = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == recruitment_id,
        modelDB.Recruitment.recruiter_user_id == user_id
    ).first()

    if not recruitment:
        raise HTTPException(status_code=404, detail="募集が見つかりません")

    try:
        # ステータスを「削除済み(9など)」にする（論理削除）
        recruitment.status = 9 
        db.commit()
        return DeleteResponse(ok=True)
    except Exception as e:
        db.rollback()
        return DeleteResponse(ok=False)