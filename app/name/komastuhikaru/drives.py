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
    # 1. 値の存在チェック
    if lat is None or lon is None:
        return "場所情報なし"
    
    try:
        # 2. 型変換 (Decimal -> float)
        # SQLAlchemyのNumeric型はPythonのDecimalになるため、必ずfloatにする
        lat_f = float(lat)
        lon_f = float(lon)
        
        # 3. Geocoderの初期化 (user_agentは必ずユニークなものを指定)
        geolocator = Nominatim(user_agent="my_ride_share_app_v1_0", timeout=5)
        
        # 4. API実行
        # language='ja' で日本語を指定
        location = geolocator.reverse((lat_f, lon_f), language='ja')
        
        if location:
            # 住所情報の抽出ロジック
            addr = location.raw.get('address', {})
            
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
            return location.address.split(',')[0] # フォールバック: 先頭の部分だけ返す

    except Exception as e:
        # エラー詳細をコンソールに出す（デバッグ用）
        print(f"GeoError: {e} (Lat:{lat}, Lon:{lon})")
        pass
    
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

    # response_list = []
    # for recruitment, route in drives_data:
    #     # 現在の同乗者数をカウント (Applicationテーブルから承認済みの人数を取得)
    #     # status=1 (承認) の数をカウント
    #     passenger_count = db.query(modelDB.Application).\
    #         filter(
    #             modelDB.Application.recruitment_id == recruitment.recruitment_id,
    #             modelDB.Application.status == 1 
    #         ).count()

    #     # ステータスコードを文字列に変換
    #     status_str = "recruiting"
    #     if recruitment.status == 0: status_str = "recruiting"
    #     elif recruitment.status == 1: status_str = "matched"
    #     elif recruitment.status == 2: status_str = "completed"
    #     elif recruitment.status == 3: status_str = "cancelled"

    #     # Routeテーブルには経度緯度が入っているが、フロントエンドの表示用に地名が必要
    #     # ここでは簡易的に緯度経度を返すか、別途逆ジオコーディングするか、
    #     # あるいはpath_dataに地名が含まれているならそこから取得する。
    #     # 今回は一旦 path_data に "東京駅" のような文字列が入っているか、
    #     # または別途地名カラムが必要だが、モデル定義にはないので仮置き。
    #     # ※本来は departure_name, destination_name カラムがRouteにあると良い
        
    #     # path_dataから無理やり地名を取り出すか、固定値を返す（要DB設計確認）
    #     # 仮の実装: path_dataをそのまま使うか、"座標"として返す
    #     departure_name = "出発地" # TODO: 座標から地名への変換ロジック
    #     destination_name = "目的地" # TODO: 座標から地名への変換ロジック

    #     response_list.append(DriveResponse(
    #         id=recruitment.recruitment_id,
    #         departure=departure_name, 
    #         destination=destination_name,
    #         departureTime=route.dep_time,
    #         fee=recruitment.fare,
    #         capacity=recruitment.capacity,
    #         currentPassengers=passenger_count,
    #         status=status_str
    #     ))

    response_list = []
    # ★修正: ループ内の処理を try-except で囲んでAPI全体が落ちるのを防ぐ
    for recruitment, route in drives_data:
        try:
            # 同乗者情報の取得
            approved_apps = db.query(modelDB.Application, modelDB.User).\
                join(modelDB.User, modelDB.Application.applicant_user_id == modelDB.User.user_id).\
                filter(
                    modelDB.Application.recruitment_id == recruitment.recruitment_id,
                    modelDB.Application.status == 1,
                    modelDB.Recruitment.type == 0  # <--- ★これを追加！(0:運転者募集)
                ).all()

            passenger_list = []
            for app, user in approved_apps:
                passenger_list.append(PassengerInfo(
                    userId=user.user_id,
                    name=user.name,
                    passengerCount=1
                ))

            # ステータス判定
            status_str = "recruiting"
            if recruitment.status == 1: status_str = "matched"
            elif recruitment.status == 2: status_str = "completed"
            elif recruitment.status == 3: status_str = "cancelled"

            # # ★修正: float()変換を削除し、値をそのまま関数へ渡す（関数内で安全に変換）
            # departure_name = get_location_name(route.dep_latitude, route.dep_longitude)
            # destination_name = get_location_name(route.arr_latitude, route.arr_longitude)
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
            # エラーが起きたデータはスキップするか、デフォルト値で追加するなどの対策が可能
            continue

    return DriveListResponse(drives=response_list)