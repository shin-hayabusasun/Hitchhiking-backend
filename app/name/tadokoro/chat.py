from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime

import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

# DBセッション
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---
class GetChatRequest(BaseModel):
    applicationId: int  # 募集IDから申請IDに変更

class ChatMessage(BaseModel):
    role: str  # '自分' or '相手'
    message: str
    time: str

class GetChatResponse(BaseModel):
    applicationId: int
    messages: List[ChatMessage]

class SendMessageRequest(BaseModel):
    applicationId: int  # 募集IDから申請IDに変更
    message: str

class SendMessageResponse(BaseModel):
    success: bool
    message: str

# --- API Endpoint ---
@router.post("/getchat", response_model=GetChatResponse)
async def get_chat(
    chat_request: GetChatRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    取引（Application）に紐づくチャット履歴を取得するAPI
    """
    # 1. セッション認証
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_user_id = int(user_id_str)

    # 2. 申請IDからApplicationを取得し、権限確認
    # RecruitmentとJoinして、自分が「申請者」か「募集者」かを確認する
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Application.application_id == chat_request.applicationId
    ).filter(
        (modelDB.Application.applicant_user_id == current_user_id) |
        (modelDB.Recruitment.recruiter_user_id == current_user_id)
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="取引が見つからないか、閲覧権限がありません")

    # 3. チャットメッセージを取得（時系列順）
    chat_records = db.query(modelDB.Chat).filter(
        modelDB.Chat.application_id == application.application_id
    ).order_by(
        modelDB.Chat.created_at.asc()
    ).all()

    # 4. メッセージを整形
    messages = []
    for chat in chat_records:
        role = '自分' if chat.user_id == current_user_id else '相手'
        time_str = chat.created_at.strftime('%H:%M') if chat.created_at else ''
        
        messages.append(ChatMessage(
            role=role,
            message=chat.message or '',
            time=time_str
        ))

    return GetChatResponse(
        applicationId=chat_request.applicationId,
        messages=messages
    )


@router.post("/sendmessage", response_model=SendMessageResponse)
async def send_message(
    send_request: SendMessageRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    取引（Application）に対してメッセージを送信するAPI
    """
    # 1. セッション認証
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_user_id = int(user_id_str)

    # 2. 権限確認（その取引に関わっているユーザーか）
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Application.application_id == send_request.applicationId
    ).filter(
        (modelDB.Application.applicant_user_id == current_user_id) |
        (modelDB.Recruitment.recruiter_user_id == current_user_id)
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="取引が見つからないか、送信権限がありません")

    # 3. メッセージを保存
    try:
        new_chat = modelDB.Chat(
            user_id=current_user_id,
            message=send_request.message,
            application_id=application.application_id
        )
        db.add(new_chat)
        db.commit()
        
        return SendMessageResponse(
            success=True,
            message="メッセージを送信しました"
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="メッセージの送信に失敗しました")