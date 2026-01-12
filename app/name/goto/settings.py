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

    # フロントエンドに返すためのプロフィール情報の形
class ProfileResponse(BaseModel):
    lastName: str
    firstName: str
    email: str
    address: str | None = None
    birthDate: str | None = None

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
    amount: int
    message: str


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
# 2.1既存情報取得
# プロフィール情報の取得（画面表示用）
@router.get("/users/me/profile", response_model=ProfileResponse)
async def get_profile(request: Request, db: Session = Depends(get_db)):
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

    
    full_name = target_user.name or ""
    if " " in full_name:
        last_name, first_name = full_name.split(" ", 1)
    elif "　" in full_name: # 全角スペース対策
        last_name, first_name = full_name.split("　", 1)
    else:
        # スペースがない場合は、とりあえず全部「姓」に入れておく
        last_name = full_name
        first_name = ""

    # 3. 生年月日の変換 (Date型 -> 文字列)
    birth_date_str = target_user.birth_date.strftime('%Y-%m-%d') if target_user.birth_date else ""


    # 4. データを返す
    return {
        "lastName": last_name,
        "firstName": first_name,
        "email": target_user.email, 
        "address": target_user.address,
        "birthDate": birth_date_str,
    }

# 登録情報更新
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


# 決済関連 (API実装: デモ用・DB保存あり)

@router.post("/payment/transactions", response_model=PaymentResponse)
async def process_payment(
    payment_data: PaymentRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    # 1. セッションチェック (ログインしているか確認)
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session")

    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = int(res)

    # 2. データベースに履歴を保存する
    
    
    # transaction_id をランダムな数値で生成 (DB定義がIntegerのため)
    dummy_tx_id = random.randint(10000000, 99999999)
    
    # Paymentモデルを作成
    new_payment = modelDB.Payment(
        user_id=user_id,
        card_number=4242,  # デモ用ダミーカード番号 
        transaction_id=dummy_tx_id,
        status=1,          # 1 = 成功 (Success) と仮定して保存
        billing_date=datetime.now()
    )
    
    try:
        db.add(new_payment)
        db.commit()
        db.refresh(new_payment)
    except Exception as e:
        db.rollback()
        print(f"Payment DB Error: {e}")

    # 3. フロントエンドへのレスポンス
    return {
        "transactionId": str(dummy_tx_id),
        "status": "completed",
        "paidAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # DB保存日時または現在時刻
        "amount": payment_data.amount,
        "message": "決済が完了しました"
    }