from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sys
import os

# プロジェクトルートへのパス通し
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from db_setting import SessionLocal
import modelDB

router = APIRouter(prefix="/api/actions", tags=["DriveAction"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 申請に必要なデータの定義
class ApplyRequest(BaseModel):
    user_id: int
    recruitment_id: int

@router.post("/apply")
async def apply_to_drive(request: ApplyRequest, db: Session = Depends(get_db)):
    # 重複チェック
    existing = db.query(modelDB.Application).filter(
        modelDB.Application.recruitment_id == request.recruitment_id,
        modelDB.Application.user_id == request.user_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="すでに申請済みです")

    # 新規登録
    new_app = modelDB.Application(
        recruitment_id=request.recruitment_id,
        user_id=request.user_id,
        status="pending"
    )

    try:
        db.add(new_app)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))