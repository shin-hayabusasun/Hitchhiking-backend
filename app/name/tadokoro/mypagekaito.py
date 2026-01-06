from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import Optional
import sys

# パス設定（環境に合わせて調整してください）
sys.path.append('..')
from db_setting import SessionLocal
import modelDB
from app.name.hieda.user import get_current_user  # セッション検証用関数

router = APIRouter(prefix="/api/hitchhiker", tags=["hitchhiker"])

# --- DBセッション設定 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- リクエスト/レスポンスの型定義 ---

# body: JSON.stringify({}) 用（空のリクエスト）
class MypageRequest(BaseModel):
    pass

# レスポンス形式
class HitchhikerMypageResponse(BaseModel):
    ok: bool
    name: str # 名前を追加
    bio: Optional[str] = ""
    ride_count: int = 0
    rating: float = 0.0
    reg_date: str = ""

# --- API 実装 ---

@router.post("/mypage", response_model=HitchhikerMypageResponse)
async def get_mypage(
    request: Request, 
    body: MypageRequest, 
    db: Session = Depends(get_db)
):
    # 1. クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=401, detail="セッションが見つかりません。")

    # 2. ユーザーIDを特定
    res = get_current_user(session_id=session_id, db=db)

    if res == "no":
        raise HTTPException(status_code=401, detail="セッションが切断されました。")

    user_id = int(res)

    # 3. DBから User 情報を取得 (名前を取得するため)
    user_info = db.query(modelDB.User).filter(modelDB.User.user_id == user_id).first()
    
    if not user_info:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません。")

    # 4. DBから PassengerProfile 情報を取得
    profile = db.query(modelDB.PassengerProfile).filter(modelDB.PassengerProfile.user_id == user_id).first()

    # プロフィールが存在しない場合（UserはいるがProfileレコードがない場合）
    if not profile:
        return HitchhikerMypageResponse(
            ok=True,
            name=user_info.name, # Userテーブルから取得
            bio="未設定の自己紹介",
            ride_count=0,
            rating=0.0,
            reg_date=str(date.today())
        )

    # 5. すべてのデータを統合して返却
    return HitchhikerMypageResponse(
        ok=True,
        name=user_info.name,           # Userテーブルから取得
        bio=profile.bio,               # Profileテーブルから取得
        ride_count=profile.ride_count, # Profileテーブルから取得
        rating=float(profile.rating), 
        reg_date=str(profile.reg_date) 
    )

class UpdateBioRequest(BaseModel):
    bio: str

class UpdateBioResponse(BaseModel):
    ok: bool

# --- 自己紹介更新 API ---

@router.post("/myupdate", response_model=UpdateBioResponse)
async def update_bio(
    request: Request, 
    body: UpdateBioRequest, 
    db: Session = Depends(get_db)
):
    """
    自己紹介文更新API
    
    処理:
    1. クッキーから session_id を取得
    2. get_current_user で user_id を特定
    3. PassengerProfile テーブルの該当レコードを検索
    4. bio カラムを更新して保存
    """
    
    # 1. クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="認証が必要です")

    # 2. ユーザーを特定 (res = userid の文字列)
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です")

    user_id = int(res)

    # 3. DBから該当ユーザーの PassengerProfile を取得
    profile = db.query(modelDB.PassengerProfile).filter(
        modelDB.PassengerProfile.user_id == user_id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="プロフィールが見つかりません")

    # 4. データの更新
    try:
        profile.bio = body.bio  # リクエストボディの bio を代入
        db.commit()             # 確定
        
        print(f"User {user_id} updated bio to: {body.bio}")
        return UpdateBioResponse(ok=True)

    except Exception as e:
        db.rollback()           # エラー時は巻き戻し
        print(f"Update error: {e}")
        raise HTTPException(status_code=500, detail="更新中にエラーが発生しました")