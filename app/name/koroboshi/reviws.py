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
from app.name.tadokoro.notific import create_notification

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
    二重投稿防止、相互レビュー判定、決済、両者へのポイント加算、およびステータス完了更新(status=3)
    """
    # 1. 認証
    session_id = request.cookies.get("session_id")
    my_id_str = get_current_user(session_id=session_id, db=db)
    if my_id_str == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です")
    my_id = int(my_id_str)

    # 2. 二重投稿チェック（同一募集への連投防止）
    already_exists = db.query(modelDB.Review).filter(
        modelDB.Review.recruitment_id == req.recruitment_id,
        modelDB.Review.reviewer_user_id == my_id
    ).first()

    if already_exists:
        return {
            "ok": False, 
            "status": "already_reviewed", 
            "message": "既にレビューを投稿済みです"
        }

    try:
        # 3. 募集と承認済み申請データの取得
        rec = db.query(modelDB.Recruitment).filter(modelDB.Recruitment.recruitment_id == req.recruitment_id).first()
        app = db.query(modelDB.Application).filter(
            modelDB.Application.recruitment_id == req.recruitment_id,
            or_(modelDB.Application.status == 1, modelDB.Application.status == 2)
        ).first()

        if not rec or not app:
            raise HTTPException(status_code=404, detail="対象の取引が見つかりません")

        # 4. 役割（運転者/同乗者）と相手(target)の特定
        if rec.type == 0:
            driver_id = rec.recruiter_user_id
            passenger_id = app.applicant_user_id
        else:
            driver_id = app.applicant_user_id
            passenger_id = rec.recruiter_user_id

        target_user_id = passenger_id if my_id == driver_id else driver_id

        # 5. 今回のレビューを保存
        new_review = modelDB.Review(
            reviewer_user_id=my_id,
            reviewee_user_id=target_user_id,
            recruitment_id=req.recruitment_id,
            rating=req.rating,
            comment=req.comment,
            created_at=datetime.now()
        )
        db.add(new_review)

        # 6. 相手側のプロファイル（平均レート）更新
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

        # レビューを受けた相手に通知
        reviewer_user = db.query(modelDB.User).filter(
            modelDB.User.user_id == my_id
        ).first()
        reviewer_name = reviewer_user.name if reviewer_user else "ユーザー"
        
        create_notification(
            db=db,
            user_id=target_user_id,
            message=f"{reviewer_name}さんからレビューが投稿されました（評価: {req.rating}）"
        )

        # 7. 相互評価完了判定
        partner_review = db.query(modelDB.Review).filter(
            modelDB.Review.recruitment_id == req.recruitment_id,
            modelDB.Review.reviewer_user_id == target_user_id,
            modelDB.Review.reviewee_user_id == my_id
        ).first()

        if partner_review:
            # --- 相互評価が揃った場合の最終処理 ---
            
            # A. 両者のポイント加算 (+1pt)
            for uid in [my_id, target_user_id]:
                balance = db.query(modelDB.UserBalance).filter(modelDB.UserBalance.user_id == uid).first()
                if not balance:
                    balance = modelDB.UserBalance(user_id=uid, point_balance=0, sales_history=0)
                    db.add(balance)
                
                balance.point_balance += 1
                
                # ポイント加算通知を送る
                create_notification(
                    db=db,
                    user_id=uid,
                    message="相互レビューが完了しました！ポイント+1を獲得しました🎉"
                )
                
                # B. 運転者への売上反映
                if uid == driver_id:
                    # 報酬計算: $fare \times \frac{5}{6}$
                    reward = int(rec.fare * (5 / 6))
                    balance.sales_history += reward
                    
                    # 売上反映通知（運転者のみ）
                    create_notification(
                        db=db,
                        user_id=uid,
                        message=f"売上が反映されました！報酬: ¥{reward}"
                    )

            # C. 募集ステータスを「3: 取引完了」に更新
            rec.status = 3
            # D. (任意) 申請ステータスも完了(2)に更新して不整合を防ぐ
            app.status = 2

        db.commit()
        return {
            "ok": True, 
            "status": "completed" if partner_review else "pending_partner"
        }

    except Exception as e:
        db.rollback()
        print(f"Transaction Error: {e}")
        raise HTTPException(status_code=500, detail="決済処理中にエラーが発生しました")