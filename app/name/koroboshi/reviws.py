from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 自作モジュールのインポート
import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api", tags=["reviews"])

# --- DBセッションの取得 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- リクエストスキーマ ---
class ReviewRequest(BaseModel):
    recruitment_id: int
    rating: int
    comment: Optional[str] = None

# --- メインAPI ---
@router.post("/reviews")
async def post_review(req: ReviewRequest, request: Request, db: Session = Depends(get_db)):
    """
    二重投稿防止、相互レビュー判定、決済・ポイント・レート更新API
    """
    # 1. 認証：セッションから自分のユーザーIDを取得
    session_id = request.cookies.get("session_id")
    my_id_str = get_current_user(session_id=session_id, db=db)
    if my_id_str == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です")
    my_id = int(my_id_str)

    # ★ 追加：二重投稿チェック
    # 同じ募集IDで、自分が既にレビューを投稿しているか確認
    already_exists = db.query(modelDB.Review).filter(
        modelDB.Review.recruitment_id == req.recruitment_id,
        modelDB.Review.reviewer_user_id == my_id
    ).first()

    if already_exists:
        # すでに投稿済みの場合は 200 OK で ok: False を返す
        return {
            "ok": False, 
            "status": "already_reviewed", 
            "message": "このドライブに対するレビューは既に投稿済みです"
        }

    try:
        # 2. 募集データと承認済み申請データを取得
        rec = db.query(modelDB.Recruitment).filter(
            modelDB.Recruitment.recruitment_id == req.recruitment_id
        ).first()
        
        app = db.query(modelDB.Application).filter(
            modelDB.Application.recruitment_id == req.recruitment_id,
            or_(modelDB.Application.status == 1, modelDB.Application.status == 2)
        ).first()

        if not rec or not app:
            raise HTTPException(status_code=404, detail="対象の取引が見つかりません")

        # 3. 役割と相手(target)の特定
        if rec.type == 0:
            driver_id = rec.recruiter_user_id
            passenger_id = app.applicant_user_id
        else:
            driver_id = app.applicant_user_id
            passenger_id = rec.recruiter_user_id

        target_user_id = passenger_id if my_id == driver_id else driver_id

        # 4. レビューをDBに保存
        new_review = modelDB.Review(
            reviewer_user_id=my_id,
            reviewee_user_id=target_user_id,
            recruitment_id=req.recruitment_id,
            rating=req.rating,
            comment=req.comment,
            created_at=datetime.now()
        )
        db.add(new_review)

        # 5. レート更新ロジック
        if target_user_id == driver_id:
            profile = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == target_user_id).first()
        else:
            profile = db.query(modelDB.PassengerProfile).filter(modelDB.PassengerProfile.user_id == target_user_id).first()

        if profile:
            all_revs = db.query(modelDB.Review).filter(modelDB.Review.reviewee_user_id == target_user_id).all()
            count = len(all_revs) + 1
            total_sum = sum([r.rating for r in all_revs]) + req.rating
            profile.rating = round(float(total_sum) / count, 1)
            
            if hasattr(profile, 'drive_count'): profile.drive_count += 1
            if hasattr(profile, 'ride_count'): profile.ride_count += 1

        # 6. 相互レビュー判定と決済・ポイント処理
        partner_review = db.query(modelDB.Review).filter(
            modelDB.Review.recruitment_id == req.recruitment_id,
            modelDB.Review.reviewer_user_id == target_user_id,
            modelDB.Review.reviewee_user_id == my_id
        ).first()

        if partner_review:
            for uid in [my_id, target_user_id]:
                balance = db.query(modelDB.UserBalance).filter(modelDB.UserBalance.user_id == uid).first()
                if not balance:
                    balance = modelDB.UserBalance(user_id=uid, point_balance=0, sales_history=0)
                    db.add(balance)
                
                balance.point_balance += 1
                if uid == driver_id:
                    reward = int(rec.fare * (5 / 6))
                    balance.sales_history += reward

            rec.status = 3

        db.commit()
        return {"ok": True, "status": "completed" if partner_review else "pending_partner"}

    except Exception as e:
        db.rollback()
        print(f"Transaction Error: {e}")
        raise HTTPException(status_code=500, detail="決済処理中にエラーが発生しました")