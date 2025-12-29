# /api/user/* エンドポイント
from fastapi import APIRouter, Depends, HTTPException,Response,Request
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
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
# パスワード検証用のライブラリ (bcrypt)
from passlib.context import CryptContext


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
    
    # 3. ★ クッキーをセット（これが credentials: 'include' で送受信される）
    # ここでは例としてユーザーIDを入れていますが、実際はJWTなどを生成して入れます
    response.set_cookie(
        key="session_id",
        value=str(user_in_db.user_id), 
        httponly=True,   # JSから盗まれないようにする
        samesite="lax",  # CSRF対策
        max_age=3600 * 24, # 1日有効
        secure=False,    # 開発中はFalse、本番(HTTPS)はTrue
    )

    
    return LoginResponse(ok=True, isuser=user.isuser)

@router.post("/regist", response_model=RegistResponse)
async def regist(user: UserRegist, db: Session = Depends(get_db)):
    """
    新規ユーザー登録API
    フロントエンドの配列形式（name, barthday, adress）と
    Base64画像データ（プレフィックス付き）に対応
    """
    try:
        # 1. 名前の結合 (例: ["山田", "太郎"] -> "山田 太郎")
        full_name = " ".join(user.name)
        
        # 2. 住所の結合 (例: ["123-4567", "東京都", ...] -> "123-4567 東京都 ...")
        full_address = " ".join(user.adress)
        
        # 3. 生年月日の変換 (例: [2025, 1, 1] -> date型)
        try:
            birth_date = date(user.barthday[0], user.barthday[1], user.barthday[2])
        except (IndexError, ValueError):
            raise HTTPException(status_code=400, detail="生年月日の形式が不正です")
        
        # 4. パスワードのハッシュ化
        hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
        
        # 5. identification (Base64) の処理
        # FileReader.readAsDataURL の結果は "data:image/png;base64,iVBOR..." となるため、
        # カンマより後ろの純粋なデータ部分のみを抽出する
        try:
            if "," in user.identification:
                # プレフィックス(data:image/xxx;base64,)を切り捨てる
                header, encoded = user.identification.split(",", 1)
            else:
                encoded = user.identification
            #identity_doc_binary = base64.b64decode(encoded)
            identity_doc_binary= encoded.encode('utf-8')  # バイナリとして保存
        except Exception:
            raise HTTPException(status_code=400, detail="本人確認書類のデータが不正です")
        
        # 6. Userテーブルへの挿入
        new_user = modelDB.User(
            name=full_name,
            email=user.mail,
            password=hashed_password,
            gender=user.sex, # フロントから 1(男性) or 0(女性) が来る
            birth_date=birth_date,
            address=full_address,
            identity_doc=identity_doc_binary
        )
        
        db.add(new_user)
        db.flush() # IDを確定させるために一旦反映（commitはまだしない）
        
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
                car_number="未設定"
            )
            db.add(driver_profile)
        
        # 最後にまとめてコミット（一貫性を保つため）
        db.commit()
        return RegistResponse(ok=True)
        
    except IntegrityError:
        db.rollback()
        # メールアドレスの重複など
        raise HTTPException(status_code=400, detail="このメールアドレスは既に登録されています")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"予期せぬエラーが発生しました: {str(e)}")


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

    # セッションIDが有効かどうかをデータベースで確認
    user_in_db = db.query(modelDB.User).filter(modelDB.User.user_id == session_id).first()
    
    if not user_in_db:
        return RegistResponse(ok=False)

    print(user_in_db)  # ログにユーザー情報を出力

    # キャッシュを無効にするヘッダーを設定

    return RegistResponse(ok=True)