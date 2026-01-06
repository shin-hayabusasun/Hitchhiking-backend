#コピペ
from fastapi import APIRouter, Depends, HTTPException,Response,Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date,timedelta
import sys
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
import hashlib
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
# パスワード検証用のライブラリ (bcrypt)
from passlib.context import CryptContext
import secrets
from app.name.hieda import get_current_user#ヒエダのuser apiにあるget_current_user関数をimportする（パスがあってるかわからないので調べて）
####

#####一部変える
router = APIRouter(prefix="/api/", tags=["settings"]) #これは自分たちのパスを入れる(これ以降、ルートノードからの記述をする)
######

# ###コピペ不要　お手本
# """
# APIの中をきれいにするために、使いまわせる関数を定義しておく場合
# """
# def create_session(db: Session, user_id: int):#呼び出すときはcreate_session(db=DB変数, user_id=userid変数)
#     session_id = secrets.token_urlsafe(32)  # 推測不能
#     expires_at = datetime.utcnow() + timedelta(days=1)

#     session = modelDB.Session(
#         session_id=session_id,
#         user_id=user_id,
#         expires_at=expires_at
#     )
#     db.add(session)
#     db.commit()

#     return session_id
# ###

######コピペ
# DBセッション
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#######

# 一部変える（レスポンスやリクエストの型を定義する）
# ==========================================
# 1. 型定義 (Pydantic Models)
#    設計書の Request / Response に合わせて定義
#    ※ コピペ元の UserLogin などは全て消して、これを貼ってください
# ==========================================

# --- 5.13.1 ユーザー情報取得 (GET /api/users/me) ---
class UserInfoResponse(BaseModel):
    name: str
    email: str
    isVerified: bool

# --- 5.13.2 プロフィール更新 (PUT /api/users/me/profile) ---
class ProfileUpdateRequest(BaseModel):
    lastName: str
    firstName: str
    birthDate: str
    email: str
    phone: str
    address: str
    password: Optional[str] = None  # パスワード変更の際は入力される

class SuccessResponse(BaseModel):
    success: bool

# --- 5.13.3 本人確認書類 (POST) はファイルアップロードなのでBaseModel定義は不要 ---

# --- 5.13.4 通知設定更新 (PUT /api/settings/notifications) ---
class NotificationUpdateRequest(BaseModel):
    rideRequest: bool
    message: bool
    reminder: bool
    promotion: bool

class MessageResponse(BaseModel):
    message: str

# --- 5.13.5 クレジットカード追加 (POST /api/payment/cards) ---
class CardAddRequest(BaseModel):
    # 設計書にある項目
    payment_token: str       # 決済トークン
    id: Optional[str] = None # 新規時は不要かもしれないが念のため
    cardnumber: str
    name: str
    date: str
    code: int

class CardAddResponse(BaseModel):
    cardId: str

# --- 5.13.6 クレジットカード編集 (PUT /api/payment/cards/{id}) ---
class CardUpdateRequest(BaseModel):
    # IDはパスパラメータで来るのでここには含めなくてもOKだが、設計書に合わせて定義
    cardnumber: str
    name: str
    date: str
    code: int

# --- 5.14 決済 (POST /api/payment/transactions) ---
class PaymentRequest(BaseModel):
    amount: int  # 決済金額

class PaymentResponse(BaseModel):
    transactionId: str
    status: str
    paidAt: str

######

###すべて変える（APIの処理を記述する）


#パターン3　セッションを使用してログインしているユーザーを特定して、何かする場合
@router.get("/mypage",response_model=mypageResponse)
async def is_login(user:UserMypage"""リクエストのデータ構造定義""",request: Request, db: Session = Depends(get_db)):#リクエストbodyがないときは記述しなくてよい,reqestはリクエストのセッション情報を見るために使う
    
    # クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")

    if not session_id:
        return RegistResponse(ok=False)

    res=get_current_user(session_id=session_id,db= db)#sessionが有効か見る。有効の場合はuseridがstrで返る

    # セッションIDが有効かどうかをデータベースで確認
    if res=="no":
        return mypageResponse(エラー処理)
    """
    resにはセッションのuseridが入ってるのでそれを使って、ＤＢでマイページ情報を取得して、mypageobjectに入れる
    """

    return mypageResponse(mypagedata=mypageobject)
####
#機能1:ユーザ情報取得
@router.get("/users/me",response_model=UserInfoResponse)
async def get_user_info(request: Request. db: Session = Depends(get_db)):
    #クッキーからセッションIDを習得
    session_id = request.cookies.get("session_id")

    if not session_id:
        return RegistResponse(ok=False)

        res=get_current_user(session_id=session_id, db=db)

if res=="no":
    return mypageResponse(エラー処理)

#IDを使用してデータベースから情報を検索
target_user = db.query(modelDB.User).filter(modelDB.User.id == user_id).first()

if not target_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

#取得したデータを、設計書通りの形にして返す
return UserInfoResponse(
        name=target_user.name,         # DBのカラム名に合わせてください
        email=target_user.mail,        # DBのカラム名（mailかemailか確認）
        isVerified=True # 本来は target_user.is_verified などDBの値を入れる
)

#機能2:プロフィール更新
@router.put("/users/me/profile", response_model=SuccessResponse)
async def update_profile(
    profile_data: ProfileUpdateRequest, 
    request: Request, 
    db: Session = Depends(get_db)
):

#クッキーからセッションIDを習得
    session_id = request.cookies.get("session_id")

    if not session_id:
        return RegistResponse(ok=False)

        res=get_current_user(session_id=session_id, db=db)

if res=="no":
    return mypageResponse(エラー処理)

    #IDを使用してデータベースから情報を検索
target_user = db.query(modelDB.User).filter(modelDB.User.id == user_id).first()

if not target_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

# 3. データの更新処理
    
    # (A) 名前: 姓と名を結合して保存 (例: "山田 太郎")
    target_user.name = f"{profile_data.lastName} {profile_data.firstName}"
    
    # (B) メールアドレス
    target_user.email = profile_data.email
    
    # (C) 住所
    target_user.address = profile_data.address
    
    # (D) 生年月日: 文字列(YYYY-MM-DD) を Pythonの日付型に変換
    try:
        # フロントエンドから "1990-01-01" のような形式で来ると仮定
        date_obj = datetime.strptime(profile_data.birthDate, '%Y-%m-%d').date()
        target_user.birth_date = date_obj
    except ValueError:
        pass 

    # (E) 電話番号
    
    # カラムを追加したら以下のコメントアウトを外してください。
    # target_user.phone = profile_data.phone

    # (F) パスワード変更
    # 入力がある場合のみ更新する（空文字やNoneなら変更しない）
    if profile_data.password and len(profile_data.password) > 0:
        # 生のパスワードではなく、ハッシュ化したものを保存する
        hashed_password = pwd_context.hash(profile_data.password)
        target_user.password = hashed_password

    # 4. 変更をデータベースに反映 (コミット)
    try:
        db.commit()
    except Exception as e:
        db.rollback() # エラーが起きたら元に戻す
        raise HTTPException(status_code=500, detail="更新に失敗しました")

    return SuccessResponse(success=True)


# 5.13.3 本人確認書類アップロード
@router.post("/users/me/identity-document", response_model=SuccessResponse)
async def upload_identity_document(
    file: UploadFile = File(...),  # フロントから送られてくる画像ファイル
    request: Request, 
    db: Session = Depends(get_db)
):

#クッキーからセッションIDを習得
    session_id = request.cookies.get("session_id")

    if not session_id:
        return RegistResponse(ok=False)

        res=get_current_user(session_id=session_id, db=db)

if res=="no":
    return mypageResponse(エラー処理)

    #IDを使用してデータベースから情報を検索
target_user = db.query(modelDB.User).filter(modelDB.User.id == user_id).first()

if not target_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

try:
        # アップロードされたファイルの中身をバイナリとして読み込む
        file_content = await file.read()
        
        # DBのBYTEAカラムにそのまま入れる
        target_user.identity_doc = file_content
        
        # ★補足: ここで「確認ステータス」を更新したい場合
        # models.py に is_verified や status カラムがあればここで更新します
        # target_user.is_verified = False  # 再申請なので「未確認」に戻すなど

        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="ファイルの保存に失敗しました")

    return SuccessResponse(success=True)

#通知設定
@router.put("/settings/notifications", response_model=MessageResponse)
async def update_notifications(
    settings: NotificationUpdateRequest, 
    request: Request, 
    db: Session = Depends(get_db)
):

#クッキーからセッションIDを習得
    session_id = request.cookies.get("session_id")

    if not session_id:
        return RegistResponse(ok=False)

        res=get_current_user(session_id=session_id, db=db)

if res=="no":
    return mypageResponse(エラー処理)

#IDを使用してデータベースから情報を検索
target_user = db.query(modelDB.User).filter(modelDB.User.id == user_id).first()

if not target_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

# 3. 設定の更新処理
    # リクエスト(settings) の値を、DBのカラム(target_user) に書き写す
    
    target_user.notify_ride_request = settings.rideRequest
    target_user.notify_message = settings.message
    target_user.notify_reminder = settings.reminder
    target_user.notify_promotion = settings.promotion

# 4. データベースに保存
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="設定の保存に失敗しました")

    return MessageResponse(message="通知設定を更新しました")