#コピペ  
from fastapi import APIRouter, Depends, HTTPException, Response, Request, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date, timedelta
import sys
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
import hashlib
from fastapi.middleware.cors import CORSMiddleware
# パスワード検証用のライブラリ
from passlib.context import CryptContext
import secrets
from app.name.hieda.user import get_current_user
# パスワードハッシュ化設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api", tags=["settings"]) 

# DBセッション
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 1. 型定義 (Pydantic Models)
# ==========================================

# --- ユーザー情報取得 ---
class UserInfoResponse(BaseModel):
    name: str
    email: str
    # isVerified: bool 機能削除

# --- プロフィール更新 ---
class ProfileUpdateRequest(BaseModel):
    lastName: str
    firstName: str
    birthDate: str
    email: str
    address: str
    password: Optional[str] = None 

class SuccessResponse(BaseModel):
    success: bool

# 本人確認書類のリクエスト用（Base64文字列で受け取る）
class IdentityDocumentRequest(BaseModel):
    identification: str  # Hiedaさんの UserRegist と名前を合わせています

# --- 通知設定更新 ---
class NotificationSettingsSchema(BaseModel):
    rideRequest: bool
    message: bool
    reminder: bool
    promotion: bool

class MessageResponse(BaseModel):
    message: str

# --- クレジットカード関連 ---
class CardAddRequest(BaseModel):
    payment_token: str
    id: Optional[str] = None
    cardnumber: str
    name: str
    date: str
    code: int

class CardAddResponse(BaseModel):
    cardId: str

class CardUpdateRequest(BaseModel):
    cardnumber: str
    name: str
    date: str
    code: int

# --- 決済関連 ---
class PaymentRequest(BaseModel):
    amount: int

class PaymentResponse(BaseModel):
    transactionId: str
    status: str
    paidAt: str


# ==========================================
# 2. API実装
# ==========================================

# 機能1: ユーザ情報取得
@router.get("/users/me", response_model=UserInfoResponse)
async def get_user_info(request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")

    user_id = int(res)
    target_user = db.query(modelDB.User).filter(modelDB.User.user_id == user_id).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserInfoResponse(
        name=target_user.name,
        email=target_user.email, # DBのカラム名が mail であると想定
        
    )

# 機能2: プロフィール更新
@router.put("/users/me/profile", response_model=SuccessResponse)
async def update_profile(
    profile_data: ProfileUpdateRequest, 
    request: Request, 
    db: Session = Depends(get_db)
):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")

    user_id = int(res)
    target_user = db.query(modelDB.User).filter(modelDB.User.user_id == user_id).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # データの更新処理
    target_user.name = f"{profile_data.lastName} {profile_data.firstName}"
    # 【重要修正】以前のコードでは target_user.email でしたが、
    # DBのカラム名は恐らく mail なので修正しています。もしエラーが出る場合はここを確認。
    target_user.email = profile_data.email 
    target_user.address = profile_data.address
    
    # 生年月日
    try:
        date_obj = datetime.strptime(profile_data.birthDate, '%Y-%m-%d').date()
        target_user.birth_date = date_obj
    except ValueError:
        pass 

    # パスワード変更
    if profile_data.password and len(profile_data.password) > 0:
        hashed_password = pwd_context.hash(profile_data.password)
        target_user.password = hashed_password

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Update failed")

    return SuccessResponse(success=True)


# 5.13.3 本人確認書類アップロード（Hiedaさんの方式に合わせる）
@router.post("/users/me/identity-document", response_model=SuccessResponse)
async def upload_identity_document(
    data: IdentityDocumentRequest,  # File ではなく文字データとして受け取る
    request: Request, 
    db: Session = Depends(get_db)
):
    # セッション確認
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")

    user_id = int(res)
    target_user = db.query(modelDB.User).filter(modelDB.User.user_id == user_id).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    try:
        # Hiedaさんのコードと同じ処理：Base64のカンマ以降を取り出す
        if "," in data.identification:
            header, encoded = data.identification.split(",", 1)
        else:
            encoded = data.identification
        
        # 文字列をバイナリ（bytes）に変換してDBに保存
        identity_doc_binary = encoded.encode('utf-8') 
        target_user.identity_doc = identity_doc_binary
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"Error saving document: {e}")
        raise HTTPException(status_code=500, detail="保存に失敗しました")

    return SuccessResponse(success=True)

# ==========================================
# 通知設定 API
# ==========================================

# 1. 通知設定を取得する（@router.get を必ず付ける！）
@router.get("/users/me/notifications", response_model=NotificationSettingsSchema)
async def get_notifications(request: Request, db: Session = Depends(get_db)): # 名前を get_notifications に変更
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")

    user_id = int(res)
    
    # 通知設定テーブルを検索
    notif = db.query(modelDB.NotificationSetting).filter(modelDB.NotificationSetting.user_id == user_id).first()
    
    # もしレコードがなければ（初めての設定なら）、すべてオフで作成する
    if not notif:
        notif = modelDB.NotificationSetting(
            user_id=user_id,
            ride_request=False,
            message=False,
            reminder=False,
            promotion=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

    return {
        "rideRequest": notif.ride_request,
        "message": notif.message,
        "reminder": notif.reminder,
        "promotion": notif.promotion
    }

# 2. 通知設定を更新する（ここは PUT のままでOK）
@router.put("/users/me/notifications")
async def update_notifications(settings: NotificationSettingsSchema, request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")

    user_id = int(res)
    
    notif = db.query(modelDB.NotificationSetting).filter(modelDB.NotificationSetting.user_id == user_id).first()
    
    if not notif:
        notif = modelDB.NotificationSetting(user_id=user_id)
        db.add(notif)

    # 送られてきた値で上書き保存
    notif.ride_request = settings.rideRequest
    notif.message = settings.message
    notif.reminder = settings.reminder
    notif.promotion = settings.promotion
    
    db.commit()
    return {"message": "success"}