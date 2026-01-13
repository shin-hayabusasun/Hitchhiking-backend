from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict # ConfigDictを追加
from typing import List, Optional
import sys
import os

# パス設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api", tags=["MyRequests"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# Pydantic モデル定義 (ここを修正しました)
# ---------------------------------------------------------
class RequestItem(BaseModel):
    # 最新のPydanticではFieldを使ってエイリアスを指定するのが確実です
    id: int
    recruitment_id: int
    name: str
    rating: float
    reviews: int
    from_loc: str = Field(..., alias="from") # JSONでは "from" になる
    to_loc: str = Field(..., alias="to")     # JSONでは "to" になる
    time: str
    date: str
    price: int
    status: int

    # エイリアス（from/to）を使っても、Python内で普通に値を入れられるようにする設定
    model_config = ConfigDict(populate_by_name=True)

class MyRequestsData(BaseModel):
    requesting: List[RequestItem]
    approved: List[RequestItem]
    completed: List[RequestItem]

class MyRequestsResponse(BaseModel):
    success: bool
    data: Optional[MyRequestsData] = None
    message: Optional[str] = None

class ActionResponse(BaseModel):
    success: bool
    message: str

# ---------------------------------------------------------
# API実装
# ---------------------------------------------------------

@router.get("/hitchhiker/my-requests", response_model=MyRequestsResponse)
async def get_my_requests(request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        # success: False を返してフロント側でリダイレクトさせる
        return MyRequestsResponse(success=False, message="ログインしていません")

    res_user_id = get_current_user(session_id=session_id, db=db)
    if res_user_id == "no":
        return MyRequestsResponse(success=False, message="セッションが無効です")
    
    current_user_id = int(res_user_id)

    try:
        results = db.query(
            modelDB.Application,
            modelDB.Recruitment,
            modelDB.Route,
            modelDB.User,
            modelDB.DriverProfile
        ).join(modelDB.Recruitment, modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id)\
         .join(modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id)\
         .join(modelDB.User, modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id)\
         .outerjoin(modelDB.DriverProfile, modelDB.Recruitment.recruiter_user_id == modelDB.DriverProfile.user_id)\
         .filter(modelDB.Application.applicant_user_id == current_user_id)\
         .all()

        data_structure = {
            "requesting": [],
            "approved": [],
            "completed": []
        }

        for app, recruit, route, driver, profile in results:
            fmt_time = route.dep_time.strftime("%H:%M") if route.dep_time else "-"
            fmt_date = route.dep_time.strftime("%Y/%m/%d") if route.dep_time else "-"

            d_rating = float(profile.rating) if profile and profile.rating else 0.0
            d_reviews = int(profile.drive_count) if profile and profile.drive_count else 0

            # 辞書形式で作ってからRequestItemに渡すのが最も安全です
            item_data = {
                "id": app.application_id,
                "recruitment_id": recruit.recruitment_id,
                "name": driver.name,
                "rating": d_rating,
                "reviews": d_reviews,
                "from_loc": route.depname,
                "to_loc": route.arrname,
                "time": fmt_time,
                "date": fmt_date,
                "price": int(recruit.fare),
                "status": app.status
            }
            
            item = RequestItem(**item_data)

            if app.status == 0:
                data_structure["requesting"].append(item)
            elif app.status == 1:
                data_structure["approved"].append(item)
            else:
                data_structure["completed"].append(item)

        return MyRequestsResponse(
            success=True, 
            data=MyRequestsData(**data_structure)
        )

    except Exception as e:
        print(f"Error fetching requests: {e}")
        # 詳細なエラーを返すと原因が分かりやすくなります
        return MyRequestsResponse(success=False, message=str(e))

# cancel_application は変更なしでOK