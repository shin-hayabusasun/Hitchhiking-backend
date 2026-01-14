from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sys
import os

# パス設定：プロジェクトルートを認識させる
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from db_setting import SessionLocal
import modelDB
# 【重要】user.py から get_current_user をインポート
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/actions", tags=["DriveAction"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ApplyRequest(BaseModel):
    recruitment_id: int

@router.post("/apply")
async def apply_to_drive(apply_data: ApplyRequest, request: Request, db: Session = Depends(get_db)):
    # 1. セッションチェック
    session_id = request.cookies.get("session_id")
    if not session_id:
        return {"ok": False, "message": "ログインが必要です。"}

    # 2. ユーザー特定
    res_user_id = get_current_user(session_id=session_id, db=db)
    if res_user_id == "no":
        return {"ok": False, "message": "セッションの有効期限が切れています。"}
    
    current_user_id = int(res_user_id)

    try:
        # 3. 自作自演チェック (自分の募集には申請できないようにする)
        recruitment = db.query(modelDB.Recruitment).filter(
            modelDB.Recruitment.recruitment_id == apply_data.recruitment_id
        ).first()
        
        if not recruitment:
            return {"ok": False, "message": "対象の募集が見つかりません。"}
            
        if recruitment.recruiter_user_id == current_user_id:
            return {"ok": False, "message": "自分の募集には申請できません。"}

        # 4. 重複申請チェック
        existing = db.query(modelDB.Application).filter(
            modelDB.Application.recruitment_id == apply_data.recruitment_id,
            modelDB.Application.applicant_user_id == current_user_id
        ).first()
        if existing:
            return {"ok": False, "message": "すでにこのドライブに申請済みです。"}

        # --- 取引データの作成 (両方 nullable=True なのでこの順序がスムーズ) ---

        # 手順A: 先に Application を作成 (chat_id は一旦 None)
        new_app = modelDB.Application(
            recruitment_id=apply_data.recruitment_id,
            applicant_user_id=current_user_id,
            status=0,
            chat_id=None
        )
        db.add(new_app)
        db.flush()  # new_app.application_id を確定させる

        # 手順B: 確定した application_id を使って Chat を作成
        new_chat = modelDB.Chat(
            message="申請が届きました！",
            application_id=new_app.application_id
        )
        db.add(new_chat)
        db.flush()  # new_chat.chat_id を確定させる

        # 手順C: Application 側の chat_id を本物に更新
        new_app.chat_id = new_chat.chat_id

        # 全て正常ならコミット
        db.commit()
        
        # 成功時に ID を返すと、フロントエンドでチャット画面へ遷移させやすくなります
        return {
            "ok": True, 
            "message": "申請が完了しました！", 
            "application_id": new_app.application_id
        }

    except Exception as e:
        db.rollback()
        print(f"Apply API Error: {e}")
        return {"ok": False, "message": "サーバーエラーが発生しました。"}