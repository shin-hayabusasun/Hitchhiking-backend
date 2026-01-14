# app/name/goto/reviews.py

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import random # ダミー決済ID用
import sys

# パス設定（環境に合わせて調整してください）
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

# ルーターの設定
router = APIRouter(prefix="/api", tags=["reviews"])

# DBセッション取得
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 型定義
# ==========================================
class ReviewCreateRequest(BaseModel):
    recruitment_id: int
    target_user_id: int # レビューされる相手（同乗者）
    rating: int         # 1~5
    comment: Optional[str] = None

class SuccessResponse(BaseModel):
    success: bool
    message: str

# ==========================================
# レビュー投稿 & 相互完了時の決済処理 API
# ==========================================
@router.post("/reviews", response_model=SuccessResponse)
async def create_review(
    review_data: ReviewCreateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    # --------------------------------------------------
    # 1. ユーザー認証 (今回は「運転者」が操作している前提)
    # --------------------------------------------------
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session")
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    reviewer_id = int(res) # レビューする人（＝運転者）

    # --------------------------------------------------
    # 2. 二重投稿チェック
    # --------------------------------------------------
    existing_review = db.query(modelDB.Review).filter(
        modelDB.Review.recruitment_id == review_data.recruitment_id,
        modelDB.Review.reviewer_user_id == reviewer_id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="すでにレビュー済みです")

    # --------------------------------------------------
    # 3. レビューを保存 (まずは記録する)
    # --------------------------------------------------
    new_review = modelDB.Review(
        recruitment_id=review_data.recruitment_id,
        reviewer_user_id=reviewer_id,
        reviewee_user_id=review_data.target_user_id, # ★ここを修正（reviewee_user_idにする）
        rating=review_data.rating,
        comment=review_data.comment
    )
    db.add(new_review)
    # ここで一度コミットして、「自分がレビューした事実」を確定させる
    try:
        db.commit()
        db.refresh(new_review)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存エラー: {e}")

    # --------------------------------------------------
    # 4. 相互レビュー判定 & 決済・実績反映ロジック
    # --------------------------------------------------
    
    # 「同じ募集ID」で「相手(同乗者)が書いたレビュー」があるか探す
    opponent_review = db.query(modelDB.Review).filter(
        modelDB.Review.recruitment_id == review_data.recruitment_id,
        modelDB.Review.reviewer_user_id == review_data.target_user_id
    ).first()

    # ▼▼▼ 相手がまだレビューしていない場合 ▼▼▼
    if not opponent_review:
        return {"success": True, "message": "レビューを保存しました。相手のレビューを待ちます。"}

    # ▼▼▼ 相手もレビュー済みの場合 (ここからが本番！) ▼▼▼
    print("相互レビュー完了を確認。決済と実績更新を実行します。")

    try:
        # (A) 両者にポイント +1
        # ----------------------------------------
        # 自分の残高 (運転者)
        my_balance = db.query(modelDB.UserBalance).filter(modelDB.UserBalance.user_id == reviewer_id).first()
        if not my_balance:
            my_balance = modelDB.UserBalance(user_id=reviewer_id, point_balance=0, sales_history=0)
            db.add(my_balance)
        
        # 相手の残高 (同乗者)
        target_balance = db.query(modelDB.UserBalance).filter(modelDB.UserBalance.user_id == review_data.target_user_id).first()
        if not target_balance:
            target_balance = modelDB.UserBalance(user_id=review_data.target_user_id, point_balance=0, sales_history=0)
            db.add(target_balance)

        # ポイント加算
        my_balance.point_balance = (my_balance.point_balance or 0) + 1
        target_balance.point_balance = (target_balance.point_balance or 0) + 1


        # (B) 決済処理 & 運転者の売上加算
        # ----------------------------------------
        # 募集情報から金額を取得
        recruitment = db.query(modelDB.Recruitment).filter(
            modelDB.Recruitment.recruitment_id == review_data.recruitment_id
        ).first()

        if recruitment:
            fare_amount = recruitment.fare
            
            # 運転者(自分)の売上履歴(総額)に加算
            my_balance.sales_history = (my_balance.sales_history or 0) + fare_amount
            
            # Paymentテーブルに「決済完了」履歴を作成 (張りぼてAPIと同じロジック)
            dummy_tx_id = random.randint(10000000, 99999999)
            payment_record = modelDB.Payment(
                user_id=review_data.target_user_id, # 支払ったのは同乗者
                card_number=4242,                   # ダミー番号
                transaction_id=dummy_tx_id,         # ダミーID
                status=1,                           # 成功
                billing_date=datetime.now()
            )
            db.add(payment_record)


        # (C) 運転者の運転回数を +1
        # ----------------------------------------
        my_driver_profile = db.query(modelDB.DriverProfile).filter(
            modelDB.DriverProfile.user_id == reviewer_id
        ).first()

        if my_driver_profile:
            my_driver_profile.drive_count += 1
            # ※ここで必要なら平均レートの再計算も行う

        # すべての変更を一括コミット
        db.commit()

        return {"success": True, "message": "相互レビュー完了。決済とポイント付与が完了しました。"}

    except Exception as e:
        db.rollback()
        print(f"Transaction Error: {e}")
        # レビュー自体は保存されているので、ここはエラーを返さずログ出力に留めるか、
        # あるいは厳密にエラーを返すか。今回はわかりやすくエラーを返します。
        raise HTTPException(status_code=500, detail="決済処理中にエラーが発生しました")