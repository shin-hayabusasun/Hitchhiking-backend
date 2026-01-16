import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel

import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hitchhiker", tags=["passenger_reviews"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydanticモデル ---
class ReviewRequest(BaseModel):
    # フロントが "recruitment_id" というキー名で送ってくるため、ここを戻します
    recruitment_id: int 
    rating: int
    comment: Optional[str] = None

@router.post("/reviews")
async def post_passenger_review(req: ReviewRequest, request: Request, db: Session = Depends(get_db)):
    # 1. 認証
    session_id = request.cookies.get("session_id")
    my_id_str = get_current_user(session_id=session_id, db=db)
    if my_id_str == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です")
    my_id = int(my_id_str)

    try:
        # 2. 【ロジックの肝】フロントから届いた req.recruitment_id は、
        # 実は Application ID なので、それを使って Application テーブルを検索する
        app = db.query(modelDB.Application).filter(
            modelDB.Application.application_id == req.recruitment_id
        ).first()
        
        if not app:
            logger.error(f"Application ID {req.recruitment_id} (passed as recruitment_id) not found.")
            raise HTTPException(status_code=404, detail="対象の申請データが見つかりません。")

        # 本当の募集IDを取得
        real_rec_id = app.recruitment_id
        logger.info(f"=== レビュー開始: Application ID {req.recruitment_id} -> Real Recruitment ID {real_rec_id} ===")

        # 3. 募集データを取得
        rec = db.query(modelDB.Recruitment).filter(modelDB.Recruitment.recruitment_id == real_rec_id).first()

        # 4. 二重投稿チェック（本当の募集IDを使用）
        already_exists = db.query(modelDB.Review).filter(
            modelDB.Review.recruitment_id == real_rec_id,
            modelDB.Review.reviewer_user_id == my_id
        ).first()
        if already_exists:
            return {"ok": False, "status": "already_reviewed", "message": "既に投稿済みです"}

        # 5. 権限チェック
        if rec.type == 0:
            driver_id = rec.recruiter_user_id
            is_valid_passenger = (app.applicant_user_id == my_id)
        else:
            driver_id = app.applicant_user_id
            is_valid_passenger = (rec.recruiter_user_id == my_id)

        if not is_valid_passenger:
            raise HTTPException(status_code=403, detail="この取引を評価する権限がありません")

        # 6. レビュー保存
        new_review = modelDB.Review(
            reviewer_user_id=my_id,
            reviewee_user_id=driver_id,
            recruitment_id=real_rec_id, # 本当の募集IDを保存
            rating=req.rating,
            comment=req.comment,
            created_at=datetime.now()
        )
        db.add(new_review)
        db.flush()

        # 7. 相手のプロファイル更新（運転者）
        driver_profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == driver_id).first()
        if driver_profile:
            cnt = driver_profile.drive_count or 0
            rate = driver_profile.rating or 0.0
            driver_profile.rating = round(((rate * cnt) + req.rating) / (cnt + 1), 1)
            driver_profile.drive_count = cnt + 1

        # 8. 相互レビュー判定
        partner_review = db.query(modelDB.Review).filter(
            modelDB.Review.recruitment_id == real_rec_id,
            modelDB.Review.reviewer_user_id == driver_id,
            modelDB.Review.reviewee_user_id == my_id
        ).first()

        if partner_review:
            for uid in [my_id, driver_id]:
                balance = db.query(modelDB.UserBalance).filter(modelDB.UserBalance.user_id == uid).first()
                if not balance:
                    balance = modelDB.UserBalance(user_id=uid, point_balance=0, sales_history=0)
                    db.add(balance)
                balance.point_balance = (balance.point_balance or 0) + 1
                if uid == driver_id:
                    reward = int(rec.fare * (5 / 6))
                    balance.sales_history = (balance.sales_history or 0) + reward
            rec.status = 3
            app.status = 2 

        db.commit()
        return {"ok": True, "status": "completed" if partner_review else "pending_partner"}

    except Exception as e:
        db.rollback()
        logger.exception("Internal Error")
        raise HTTPException(status_code=500, detail=str(e))