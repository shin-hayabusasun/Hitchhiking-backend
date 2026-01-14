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
    1. 申請ステータスを承認(1)に変更
    2. チャットルームを作成し、Applicationと紐付ける
    """
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no": raise HTTPException(status_code=401, detail="Invalid session")
    
    current_user_id = int(res)

    # 1. 対象の申請を検索 (自分が募集主であるか確認)
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Application.application_id == id,
        modelDB.Recruitment.recruiter_user_id == current_user_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized")

    # ★追加: 既に処理済みの場合はエラーにする（二重承認防止）
    if application.status != 0:
        raise HTTPException(status_code=400, detail="This application has already been processed")

    try:
        # 2. ステータスを承認(1)に変更
        application.status = 1 
        
        # ★追加: チャットルームの作成 (まだ紐付いていない場合)
        if application.chat_id is None:
            # 新しいチャットを作成
            new_chat = modelDB.Chat(
                message="マッチングが成立しました！チャットを開始してください。",
                application_id=application.application_id 
                # ↑ models.py の定義によっては application_id が必要ない場合もあるので確認してください
                # 以前の会話では「Chatにapplication_idがある」設計でした
            )
            db.add(new_chat)
            db.flush() # ID発行
            
            # ApplicationにチャットIDを紐付け
            application.chat_id = new_chat.chat_id

        # 3. 募集自体のステータスも「マッチ済み」にする必要がある場合
        # recruitment = db.query(modelDB.Recruitment).filter(modelDB.Recruitment.recruitment_id == application.recruitment_id).first()
        # recruitment.status = 2 # マッチ済み

        db.commit()
        return ActionResponse(message="承認しました")

    except Exception as e:
        db.rollback()
        print(f"Error approving application: {e}")
        raise HTTPException(status_code=500, detail="承認処理に失敗しました")

# ---------------------------------------------------------
# 拒否 API
# ---------------------------------------------------------
@router.post("/{id}/reject", response_model=ActionResponse)
async def reject_application(request: Request, id: int = Path(..., title="Application ID"), db: Session = Depends(get_db)):
    """
    申請拒否
    """
    session_id = request.cookies.get("session_id")
    if not session_id: raise HTTPException(status_code=401, detail="Unauthorized")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no": raise HTTPException(status_code=401, detail="Invalid session")
    
    current_user_id = int(res)

    # 対象の申請を検索
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Application.application_id == id,
        modelDB.Recruitment.recruiter_user_id == current_user_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized")

    # 既に処理済みかチェック
    if application.status != 0:
        raise HTTPException(status_code=400, detail="This application has already been processed")

    application.status = 2  # 拒否
    db.commit()
    
    return ActionResponse(message="拒否しました")