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
    recruitmentId: int

class ChatMessage(BaseModel):
    role: str  # '自分' or '相手'
    message: str
    time: str

class GetChatResponse(BaseModel):
    recruitmentId: int
    messages: List[ChatMessage]

# --- API Endpoint ---
@router.post("/getchat", response_model=GetChatResponse)
async def get_chat(
    chat_request: GetChatRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    チャット履歴を取得するAPI
    
    Parameters:
    - recruitmentId: 募集ID (Recruitment ID)
    
    Returns:
    - recruitmentId: 募集ID
    - messages: チャットメッセージのリスト
    """
    # 1. セッション認証
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_user_id = int(user_id_str)

    # 2. 募集IDから関連するApplicationを取得
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Recruitment.recruitment_id == chat_request.recruitmentId
    ).filter(
        # 自分が申請者または募集者である場合のみ
        (modelDB.Application.applicant_user_id == current_user_id) |
        (modelDB.Recruitment.recruiter_user_id == current_user_id)
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="該当する申請が見つかりません")

    # 3. 相手のユーザーIDを特定
    recruitment = db.query(modelDB.Recruitment).filter(
        modelDB.Recruitment.recruitment_id == chat_request.recruitmentId
    ).first()
    
    if not recruitment:
        raise HTTPException(status_code=404, detail="募集が見つかりません")
    
    # 自分が募集者なら相手は申請者、自分が申請者なら相手は募集者
    if recruitment.recruiter_user_id == current_user_id:
        other_user_id = application.applicant_user_id
    else:
        other_user_id = recruitment.recruiter_user_id

    # 4. application_idに紐づくチャットメッセージを全て取得（時系列順）
    chat_records = db.query(modelDB.Chat).filter(
        modelDB.Chat.application_id == application.application_id
    ).order_by(
        modelDB.Chat.created_at.asc()
    ).all()

    # 5. メッセージを整形
    messages = []
    for chat in chat_records:
        # user_idが自分か相手かを判定
        role = '自分' if chat.user_id == current_user_id else '相手'
        
        # 時刻をフォーマット (HH:MM形式)
        time_str = chat.created_at.strftime('%H:%M') if chat.created_at else ''
        
        messages.append(ChatMessage(
            role=role,
            message=chat.message or '',
            time=time_str
        ))

    return GetChatResponse(
        recruitmentId=chat_request.recruitmentId,
        messages=messages
    )


# --- メッセージ送信API ---
class SendMessageRequest(BaseModel):
    recruitmentId: int
    message: str

class SendMessageResponse(BaseModel):
    success: bool
    message: str

@router.post("/sendmessage", response_model=SendMessageResponse)
async def send_message(
    send_request: SendMessageRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    チャットメッセージを送信するAPI
    
    Parameters:
    - recruitmentId: 募集ID
    - message: 送信するメッセージ
    
    Returns:
    - success: 成功/失敗
    - message: 結果メッセージ
    """
    # 1. セッション認証
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_user_id = int(user_id_str)

    # 2. 募集IDから関連するApplicationを取得
    application = db.query(modelDB.Application).join(
        modelDB.Recruitment,
        modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).filter(
        modelDB.Recruitment.recruitment_id == send_request.recruitmentId
    ).filter(
        # 自分が申請者または募集者である場合のみ
        (modelDB.Application.applicant_user_id == current_user_id) |
        (modelDB.Recruitment.recruiter_user_id == current_user_id)
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="該当する申請が見つかりません")

    # 3. 新しいチャットメッセージを作成
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
        print(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail="メッセージの送信に失敗しました")
