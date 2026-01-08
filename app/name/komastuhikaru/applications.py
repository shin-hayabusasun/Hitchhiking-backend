from fastapi import APIRouter, Depends, HTTPException, Request, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sys

# パス設定
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user 

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

# DBステータス定数
STATUS_PENDING = 0
STATUS_APPROVED = 1
STATUS_REJECTED = 2

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

# 承認 API
@router.post("/{id}/approve", response_model=ActionResponse)
async def approve_application(
    request: Request,
    id: int = Path(..., title="Application ID"), # Reactに合わせてintで受け取る
    db: Session = Depends(get_db)
):
    """
    申請承認 (POST /api/applications/:id/approve)
    """
    # 認証
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_driver_id = int(user_id_str)

    # 対象の申請を検索 & 権限チェック
    # (Recruitmentと結合して、募集主(recruiter_user_id)が自分であるか確認する)
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Application.application_id == id,
        modelDB.Recruitment.recruiter_user_id == current_driver_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized")

    # ステータス更新
    application.status = STATUS_APPROVED
    db.commit()

    return ActionResponse(message="承認しました")


# 拒否 API
@router.post("/{id}/reject", response_model=ActionResponse)
async def reject_application(
    request: Request,
    id: int = Path(..., title="Application ID"), # Reactに合わせてintで受け取る
    db: Session = Depends(get_db)
):
    """
    申請拒否 (POST /api/applications/:id/reject)
    """
    # 認証
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_driver_id = int(user_id_str)

    # 対象の申請を検索 & 権限チェック
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Application.application_id == id,
        modelDB.Recruitment.recruiter_user_id == current_driver_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized")

    # ステータス更新
    application.status = STATUS_REJECTED
    db.commit()

    return ActionResponse(message="拒否しました")