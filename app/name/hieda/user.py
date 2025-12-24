# /api/user/* エンドポイント
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date
import sys
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
import hashlib

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
    mail: EmailStr
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


@router.post("/login", response_model=LoginResponse)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    管理者orユーザーログイン
    
    処理:
    1. メールアドレスとパスワードを取り出す gggg
    2. userテーブルから検索して認証
    3. 認証結果とセッションを返す
    """
    # TODO: 実装
    return LoginResponse(ok=True, isuser=user.isuser)


@router.post("/regist", response_model=RegistResponse)
async def regist(user: UserRegist, db: Session = Depends(get_db)):
    """
    登録API
    
    処理:
    1. リクエストヘッダーの情報を取り出す
    2. userテーブルに入れる（パスワードはhash化）
    """
    try:
        # 1. データの整形
        # 名前を結合（姓 名）
        full_name = " ".join(user.name)
        
        # 住所を結合
        full_address = " ".join(user.adress)
        
        # 誕生日を日付型に変換
        birth_date = date(user.barthday[0], user.barthday[1], user.barthday[2])
        
        # パスワードをハッシュ化（SHA-256）
        hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
        
        # identification（base64）をバイナリに変換
        import base64
        identity_doc_binary = base64.b64decode(user.identification)
        
        # 2. userテーブルに挿入
        new_user = modelDB.User(
            name=full_name,
            email=user.mail,
            password=hashed_password,
            gender=user.sex,
            birth_date=birth_date,
            address=full_address,
            identity_doc=identity_doc_binary
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # 3. 運転者としても登録する場合
        if user.isdriver == 1:
            # 運転者プロフィールのデフォルト値で登録
            driver_profile = modelDB.DriverProfile(
                user_id=new_user.user_id,
                license_id=0,  # 後で更新する必要あり
                license_expiry=date.today(),  # 後で更新する必要あり
                drive_count=0,
                rating=0.0,
                reg_date=date.today(),
                car_model="未設定",
                car_color="未設定",
                car_year="未設定",
                car_number="未設定"
            )
            db.add(driver_profile)
            db.commit()
        
        return RegistResponse(ok=True)
        
    except IntegrityError as e:
        db.rollback()
        # メールアドレスが既に存在する場合
        raise HTTPException(status_code=400, detail="Email already exists")
    except ValueError as e:
        db.rollback()
        # 日付の形式が不正な場合
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.get("/logout")
async def logout(credentials: str = "include"):
    """
    ログアウト
    
    処理:
    1. セッションからuseridを取り出す
    2. ログアウト処理してセッションを消去
    """
    # TODO: 実装
    return {"ok": True}


@router.get("/IsLogin")
async def is_login(credentials: str = "include"):
    """
    ログイン中か確認
    
    処理:
    1. セッションが発行されているものと一致するか確認
    """
    # TODO: 実装
    return {"ok": True}

