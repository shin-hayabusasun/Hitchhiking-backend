# app/goto/inquiry.py
# 問い合わせ機能（登録・一覧取得）

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List
import modelDB
from db_setting import SessionLocal 

# URLプレフィックス (POSTは /api/inquiry, GETは /api/inquiries とします)
router = APIRouter(prefix="/api", tags=["inquiry"])

# --- DB接続用 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- データ型定義 ---

# 送信用（フロントエンドから来るデータ）
class InquiryRequest(BaseModel):
    category: str
    email: EmailStr
    subject: str
    body: str

# 返信用（バックエンドから返すデータ）
class InquiryResponse(BaseModel):
    id: int
    category: str
    email: str
    subject: str
    body: str
    status: int
    created_at: datetime

    class Config:
        from_attributes = True # ORMのオブジェクトをそのまま変換できるようにする設定

# --- API実装 ---

# 1. 問い合わせ送信 (POST /api/inquiry)
@router.post("/inquiry")
def create_inquiry(req: InquiryRequest, db: Session = Depends(get_db)):
    
    new_inquiry = modelDB.Inquiry(
        category=req.category,
        email=req.email,
        subject=req.subject,
        body=req.body,
        status=0, # 0: 未対応
        created_at=datetime.now()
    )
    
    db.add(new_inquiry)
    db.commit()
    db.refresh(new_inquiry)
    
    print(f"✅ 問い合わせ保存完了 ID: {new_inquiry.inquiry_id}")

    return {"message": "Inquiry received successfully", "id": new_inquiry.inquiry_id}

# 2. ★追加: 問い合わせ一覧取得 (GET /api/inquiries)
@router.get("/inquiries")
def get_inquiries(db: Session = Depends(get_db)):
    # 作成日時が新しい順に取得
    inquiries = db.query(modelDB.Inquiry).order_by(modelDB.Inquiry.created_at.desc()).all()
    
    results = []
    for i in inquiries:
        results.append({
            "id": i.inquiry_id,
            "category": i.category,
            "email": i.email,
            "subject": i.subject,
            "body": i.body,
            "status": i.status,
            "created_at": i.created_at
        })
        
    return {"inquiries": results}