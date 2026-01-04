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
router = APIRouter(prefix="/api/user", tags=["user"]) #これは自分たちのパスを入れる(これ以降、ルートノードからの記述をする)
######

###コピペ不要　お手本
"""
APIの中をきれいにするために、使いまわせる関数を定義しておく場合
"""
def create_session(db: Session, user_id: int):#呼び出すときはcreate_session(db=DB変数, user_id=userid変数)
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
###

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
#パターン1 post
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

#パターン2　セッションを使うとき(ログインしているかどうか)
@router.get("/IsLogin",response_model=IsLoginResponse)
async def is_login(request: Request, db: Session = Depends(get_db)):#リクエストbodyがないときは記述しなくてよい,reqestはリクエストのセッション情報を見るために使う
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
    
    res=get_current_user(session_id=session_id,db= db)#sessionが有効か見る。有効の場合はuseridがstrで返る

    # セッションIDが有効かどうかをデータベースで確認
    if res=="no":
        return RegistResponse(ok=False)

    return IsLoginResponse(ok=True,userid=res)

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

