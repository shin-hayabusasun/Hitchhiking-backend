from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user

router = APIRouter(prefix="/api", tags=["notifications"])

# DBセッション
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---
class NotificationItem(BaseModel):
    id: str
    type: str  # 'request', 'approval', 'message', 'system'
    title: str
    message: str
    timestamp: str
    isRead: bool
    link: Optional[str] = None

class NotificationsResponse(BaseModel):
    success: bool
    data: List[NotificationItem]

class MarkAsReadResponse(BaseModel):
    success: bool
    message: str

# --- Helper Functions ---
def parse_notification_type(message: str) -> tuple[str, str]:
    """
    メッセージ内容から通知タイプとタイトルを推測
    
    Returns:
        (type, title)
    """
    message_lower = message.lower()
    
    # 申請関連
    if "申請" in message:
        if "承認" in message:
            return ("approval", "申請が承認されました")
        elif "拒否" in message or "否認" in message:
            return ("approval", "申請が拒否されました")
        else:
            return ("request", "新しい申請がありました")
    
    # メッセージ関連
    if "メッセージ" in message or "チャット" in message:
        return ("message", "新しいメッセージ")
    
    # ドライブ関連
    if "ドライブ" in message or "募集" in message:
        return ("request", "ドライブ関連の通知")
    
    # レビュー関連
    if "レビュー" in message or "評価" in message:
        return ("system", "レビューのお願い")
    
    # システム関連
    if "システム" in message or "メンテナンス" in message:
        return ("system", "システムのお知らせ")
    
    # デフォルト
    return ("system", "お知らせ")

def format_timestamp(dt: datetime) -> str:
    """
    DateTimeをフロントエンド用のフォーマットに変換
    例: "2024-01-15 10:30"
    """
    return dt.strftime('%Y-%m-%d %H:%M') if dt else ''

# --- API Endpoints ---

@router.get("/notifications", response_model=NotificationsResponse)
async def get_notifications(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    通知一覧を取得するAPI
    
    Returns:
    - success: 成功/失敗
    - data: 通知のリスト
    """
    # 1. セッション認証
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_user_id = int(user_id_str)

    # 2. ユーザーの通知を取得（新しい順）
    notifications = db.query(modelDB.notification).filter(
        modelDB.notification.user_id == current_user_id
    ).order_by(
        modelDB.notification.created_at.desc()
    ).all()

    # 3. データを整形
    notification_list = []
    for notif in notifications:
        # メッセージからタイプとタイトルを推測
        notif_type, title = parse_notification_type(notif.message)
        
        notification_list.append(NotificationItem(
            id=str(notif.notification_id),
            type=notif_type,
            title=title,
            message=notif.message,
            timestamp=format_timestamp(notif.created_at),
            isRead=notif.is_read,
            link=None  # 現在のDBにはリンク情報がないため
        ))

    return NotificationsResponse(
        success=True,
        data=notification_list
    )


@router.post("/notifications/{notification_id}/read", response_model=MarkAsReadResponse)
async def mark_notification_as_read(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    特定の通知を既読にするAPI
    
    Parameters:
    - notification_id: 通知ID
    
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

    # 2. 該当する通知を取得（自分のものか確認）
    notification = db.query(modelDB.notification).filter(
        modelDB.notification.notification_id == notification_id,
        modelDB.notification.user_id == current_user_id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="通知が見つかりません")

    # 3. 既読フラグを更新
    try:
        notification.is_read = True
        db.commit()
        
        return MarkAsReadResponse(
            success=True,
            message="通知を既読にしました"
        )
    
    except Exception as e:
        db.rollback()
        print(f"Error marking as read: {e}")
        raise HTTPException(status_code=500, detail="既読処理に失敗しました")


@router.post("/notifications/read-all", response_model=MarkAsReadResponse)
async def mark_all_notifications_as_read(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    すべての通知を既読にするAPI
    
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

    # 2. 自分の未読通知をすべて既読にする
    try:
        db.query(modelDB.notification).filter(
            modelDB.notification.user_id == current_user_id,
            modelDB.notification.is_read == False
        ).update(
            {modelDB.notification.is_read: True},
            synchronize_session=False
        )
        db.commit()
        
        return MarkAsReadResponse(
            success=True,
            message="すべての通知を既読にしました"
        )
    
    except Exception as e:
        db.rollback()
        print(f"Error marking all as read: {e}")
        raise HTTPException(status_code=500, detail="一括既読処理に失敗しました")


# --- 通知作成用のヘルパー関数（他のAPIから使用） ---
def create_notification(
    db: Session,
    user_id: int,
    message: str
) -> bool:
    """
    新しい通知を作成する
    
    Parameters:
    - db: データベースセッション
    - user_id: 通知を送るユーザーID
    - message: 通知メッセージ
    
    Returns:
    - 成功: True, 失敗: False
    """
    try:
        new_notification = modelDB.notification(
            user_id=user_id,
            message=message,
            is_read=False
        )
        db.add(new_notification)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error creating notification: {e}")
        return False
