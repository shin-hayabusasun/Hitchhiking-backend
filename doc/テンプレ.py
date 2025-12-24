#コピペ
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
####

#####一部変える
router = APIRo
uter(prefix="/api/user", tags=["user"]) #これは自分たちのパスを入れる(これ以降、ルートノードからの記述をする)
######

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

######

###すべて変える（APIの処理を記述する）
@router.post("/login", response_model=LoginResponse)#ここでレスポンスやリクエストの型を定義したものを使用する
async def login(user: UserLogin, db: Session = Depends(get_db)):#ここでリクエストの型を定義したものを使用する

    """
    管理者orユーザーログイン
    
    処理:
    1. メールアドレスとパスワードを取り出す
    2. userテーブルから検索して認証
    3. 認証結果とセッションを返す

    例:DBアクセスとリクエストアクセスのやり方
    
    db.query(modelDB.User).filter(modelDB.User.email == user.mail).first()#DBアクセス
    user.mail#リクエストアクセス
    """
    
    return LoginResponse(ok=True, isuser=user.isuser)#ここでレスポンスの型を定義したものを使用する
####

