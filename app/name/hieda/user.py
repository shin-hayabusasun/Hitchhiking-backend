# /api/user/* エンドポイント
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
from ai_model import get_embedding


router = APIRouter(prefix="/api/user", tags=["user"])


# DBセッションhieda
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# スキーマ
class UserLogin(BaseModel):
    mail: str
    password: str
    isuser: int  # 1: ユーザー, 0: 管理者
    credentials: str = "include"


class LoginResponse(BaseModel):
    ok: bool
    isuser: int


class UserRegist(BaseModel):
    mail: EmailStr
    password: str
    name: List[str]  # [姓, 名]
    sex: int  # 1: 男, 0: 女
    barthday: List[int]  # [年, 月, 日]
    adress: List[str]  # 住所情報のリスト
    identification: str  # base64
    isdriver: int  # 1: 運転者として登録, 0: しない


class RegistResponse(BaseModel):
    ok: bool

class IsLoginResponse(BaseModel):
    ok: bool
    userid: int | None

#settion生成
def create_session(db: Session, user_id: int):
    session_id = secrets.token_urlsafe(32)  # 推測不能
    expires_at = datetime.utcnow() + timedelta(days=1)

    session = modelDB.Session(
        session_id=session_id,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()

    return session_id

def get_current_user(
    session_id: str,
    db: Session
):

    session = db.query(modelDB.Session)\
        .filter(modelDB.Session.session_id == session_id)\
        .first()

    if not session:
        return "no"

    if session.expires_at < datetime.utcnow():
        db.query(modelDB.Session)\
          .filter(modelDB.Session.session_id == session_id)\
          .delete()
        db.commit()
        return "no"

    user = db.query(modelDB.User)\
        .filter(modelDB.User.user_id == session.user_id)\
        .first()

    userid=str(user.user_id)

    return userid

@router.post("/login", response_model=LoginResponse)
async def login(
    user: UserLogin, 
    response: Response, # ★ クッキー操作のために追加
    db: Session = Depends(get_db)
):
    # 1. ユーザーをDBから取得
    user_in_db = db.query(modelDB.User).filter(modelDB.User.email == user.mail).first()
    
    if not user_in_db:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # 2. パスワード照合
    # ※ 本来は pwd_context.verify(user.password, user_in_db.password) を推奨
    hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
    if user_in_db.password != hashed_password:
        return LoginResponse(ok=False, isuser=user.isuser)
    
    if user.isuser == user_in_db.admin_flag :
        return LoginResponse(ok=False, isuser=user.isuser)
    
    session_id = create_session(db, user_in_db.user_id)
    
    # 3. ★ クッキーをセット（これが credentials: 'include' で送受信される）
    # ここでは例としてユーザーIDを入れていますが、実際はJWTなどを生成して入れます
    response.set_cookie(
        key="session_id",
        value=session_id, 
        httponly=True,   # JSから盗まれないようにする
        samesite="lax",  # CSRF対策
        max_age=3600 * 24, # 1日有効
        secure=False,    # 開発中はFalse、本番(HTTPS)はTrue
    )

    
    return LoginResponse(ok=True, isuser=user.isuser)

import logging
import hashlib
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# 自作モジュール
import modelDB
from db_setting import SessionLocal
# ★ ai_model から関数をインポート (パスは環境に合わせて調整してください)
from ai_model import get_embedding 

# --- (中略: Pydanticモデル定義など) ---

@router.post("/regist", response_model=RegistResponse)
async def regist(user: UserRegist, db: Session = Depends(get_db)):
    try:
        # 1. 名前の結合
        full_name = " ".join(user.name)
        
        # 2. 住所の結合
        full_address = " ".join(user.adress)
        
        # 3. 生年月日の変換
        try:
            birth_date = date(user.barthday[0], user.barthday[1], user.barthday[2])
        except (IndexError, ValueError):
            raise HTTPException(status_code=400, detail="生年月日の形式が不正です")
        
        # 4. パスワードのハッシュ化
        hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
        
        # 5. identification (Base64) の処理
        try:
            if "," in user.identification:
                header, encoded = user.identification.split(",", 1)
            else:
                encoded = user.identification
            identity_doc_binary = encoded.encode('utf-8') 
        except Exception:
            raise HTTPException(status_code=400, detail="本人確認書類のデータが不正です")

        setadmin_flag = 1 if user.mail == "admin@gmail.com" else 0

        # --- Embeddingの初期化処理 ---
        # bioが空なので、初期ベクトル作成用のデフォルトテキストを使用
        default_bio_text = "新規ユーザーです。よろしくお願いします。"
        try:
            initial_embedding = get_embedding(default_bio_text)
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            initial_embedding = None # 失敗した場合はNoneを許容

        # 6. Userテーブルへの挿入
        new_user = modelDB.User(
            name=full_name,
            email=user.mail,
            password=hashed_password,
            gender=user.sex,
            birth_date=birth_date,
            address=full_address,
            identity_doc=identity_doc_binary,
            admin_flag=setadmin_flag
        )
        
        db.add(new_user)
        db.flush() # user_id を確定させる

        # --- PassengerProfile の登録 ---
        passenger_profile = modelDB.PassengerProfile(
            user_id=new_user.user_id,
            ride_count=0,
            rating=0.0,
            reg_date=date.today(),
            bio="", # 初期は空
            latitude=None,
            longitude=None,
            embedding=initial_embedding # ★ 生成したベクトルをセット
        )
        db.add(passenger_profile)

        # --- UserBalance の登録 ---
        user_balance = modelDB.UserBalance(
            user_id=new_user.user_id,
            point_balance=100,
            sales_history=0
        )
        db.add(user_balance)
        
        # 7. 運転者としても登録する場合 (isdriver == 1)
        if user.isdriver == 1:
            driver_profile = modelDB.DriverProfile(
                user_id=new_user.user_id,
                license_id="0",
                license_expiry=date.today(),
                drive_count=0,
                rating=0.0,
                reg_date=date.today(),
                car_model="未設定",
                car_color="未設定",
                car_year="未設定",
                car_number="未設定",
                no_smoking=True,
                pet_ok=False,
                food_ok=False,
                music_ok=True,
                latitude=None,
                longitude=None,
                bio="", # 初期は空
                embedding=initial_embedding # ★ 生成したベクトルをセット
            )
            db.add(driver_profile)
        
        # 最後にまとめてコミット
        db.commit()
        return RegistResponse(ok=True)

    except Exception as e:
        db.rollback() 
        print(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="サーバーエラーが発生しました")

@router.get("/logout")
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    session_id = request.cookies.get("session_id")
    if session_id:
        db.query(modelDB.Session).filter(modelDB.Session.session_id == session_id).delete()
        db.commit()

    response.delete_cookie("session_id")
    return {"ok": True}

@router.get("/IsLogin")
async def is_login(request: Request, db: Session = Depends(get_db)):
    """
    ログイン中か確認
    
    処理:
    1. セッションIDがクッキーに存在するか確認
    2. セッションIDが有効かどうかを確認
    """
    # クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")

    
    
    if not session_id:
        return RegistResponse(ok=False)
    
    res=get_current_user(session_id=session_id,db= db)

    # セッションIDが有効かどうかをデータベースで確認
    if res=="no":
        return RegistResponse(ok=False)

    return IsLoginResponse(ok=True,userid=res)

