from fastapi import APIRouter, Depends, HTTPException, Response, Request, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sys

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user

# ルーター定義
router = APIRouter(prefix="/api/applications", tags=["applications"])

# ---------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------
class ActionResponse(BaseModel):
    message: str

# ---------------------------------------------------------
# Dependency
# ---------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# 承認 API
# ---------------------------------------------------------
@router.post("/{id}/approve", response_model=ActionResponse)
async def approve_application(request: Request, id: int = Path(..., title="Application ID"), db: Session = Depends(get_db)):
    """
    申請承認
    """
    # クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)

    # セッションIDが有効かどうかを確認
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_driver_id = int(res)

    # 対象の申請を検索 (自分が募集主であるか確認)
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Application.application_id == id,
        modelDB.Recruitment.recruiter_user_id == current_driver_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized")

    application.status = 1  # 承認
    db.commit()
    
    return ActionResponse(message="承認しました")

# ---------------------------------------------------------
# 拒否 API
# ---------------------------------------------------------
@router.post("/{id}/reject", response_model=ActionResponse)
async def reject_application(request: Request, id: int = Path(..., title="Application ID"), db: Session = Depends(get_db)):
    """
    申請拒否
    """
    # クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)

    # セッションIDが有効かどうかを確認
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_driver_id = int(res)

    # 対象の申請を検索
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Application.application_id == id,
        modelDB.Recruitment.recruiter_user_id == current_driver_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized")

    application.status = 2  # 拒否
    db.commit()
    
    return ActionResponse(message="拒否しました")