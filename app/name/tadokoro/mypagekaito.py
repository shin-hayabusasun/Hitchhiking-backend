from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import Optional
import sys
import logging # 追加

# --- ログの設定を追加 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

from ai_model import get_embedding # インポートを確認

@router.post("/myupdate", response_model=UpdateBioResponse)
async def update_bio(
    request: Request, 
    body: UpdateBioRequest, 
    db: Session = Depends(get_db)
):
    """
    自己紹介文およびベクトル（embedding）更新API
    """
    
    # 1. クッキーからセッションIDを取得
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="認証が必要です")

    # 2. ユーザーを特定
    res = get_current_user(session_id=session_id, db=db)
    if res == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です")

    user_id = int(res)

    # --- 新しい Embedding の生成 ---
    # bioが空文字の場合は、前回同様デフォルトテキストで埋めるか、
    # あるいは空文字のベクトルを取得します（ここでは入力された bio を使用）
    try:
        new_embedding = get_embedding(body.bio) if body.bio.strip() else get_embedding("未設定")
    except Exception as e:
        logger.error(f"Embedding update failed: {e}")
        new_embedding = None

    # 3. 各プロフィールの更新処理
    try:
        # ① PassengerProfile の更新
        p_profile = db.query(modelDB.PassengerProfile).filter(
            modelDB.PassengerProfile.user_id == user_id
        ).first()
        
        if p_profile:
            p_profile.bio = body.bio
            p_profile.embedding = new_embedding

        # ② DriverProfile の更新 (存在する場合のみ)
        d_profile = db.query(modelDB.DriverProfile).filter(
            modelDB.DriverProfile.user_id == user_id
        ).first()
        
        if d_profile:
            d_profile.bio = body.bio
            d_profile.embedding = new_embedding

        # どちらのプロフィールも見つからない場合
        if not p_profile and not d_profile:
            raise HTTPException(status_code=404, detail="プロフィールが見つかりません")

        db.commit() # 確定
        
        logger.info(f"User {user_id} updated bio and embedding.")
        return UpdateBioResponse(ok=True)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Update error: {e}")
        raise HTTPException(status_code=500, detail="更新中にエラーが発生しました")