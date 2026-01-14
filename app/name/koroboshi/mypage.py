from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime

# プロジェクトの構成に合わせたインポート
import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user  # セッション確認用関数
from ai_model import get_embedding          # ベクトル化用関数

# ログ設定
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/driver", tags=["driver"])

# DBセッション取得
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic スキーマ定義（フロントエンドの型に準拠） ---

class CarInfo(BaseModel):
    model: str
    color: str
    year: int
    number: str

class Rules(BaseModel):
    smoking: bool
    pet: bool
    food: bool
    music: bool

class DriverProfileResponse(BaseModel):
    name: str
    initial: str
    driveCount: int
    rating: float
    registeredAt: str
    car: CarInfo
    rules: Rules
    introduction: str

class UpdateDriverRequest(BaseModel):
    introduction: str
    carModel: str
    carColor: str
    carYear: str
    carNumber: str
    rules: dict # フロントエンドからの {smoke, pet, food, music}

# --- ヘルパー関数 ---

def safe_int(val, default=0):
    """
    文字列やNoneを安全に数値に変換する。
    '未設定' などの文字列が来た場合は default (0) を返す。
    """
    try:
        if val is None:
            return default
        # 数字のみで構成されているか確認
        s_val = str(val).strip()
        if s_val.isdigit():
            return int(s_val)
        return default
    except (ValueError, TypeError):
        return default

# --- API 実装 ---

@router.get("/mypage", response_model=DriverProfileResponse)
async def get_driver_mypage(request: Request, db: Session = Depends(get_db)):
    """
    ドライバーのマイページ情報を取得（User + DriverProfile 結合）
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="認証が必要です")

    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です")
    
    user_id = int(user_id_str)

    # UserテーブルとDriverProfileテーブルを結合して取得
    result = db.query(modelDB.User, modelDB.DriverProfile).join(
        modelDB.DriverProfile, modelDB.User.user_id == modelDB.DriverProfile.user_id
    ).filter(modelDB.User.user_id == user_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="ドライバープロフィールが見つかりません")

    user, profile = result

    return DriverProfileResponse(
        name=user.name,
        initial=user.name[0] if user.name else "K",
        driveCount=profile.drive_count,
        rating=float(profile.rating),
        registeredAt=profile.reg_date.strftime("%Y/%m/%d") if profile.reg_date else "----/--/--",
        car=CarInfo(
            model=profile.car_model or "未設定",
            color=profile.car_color or "未設定",
            year=safe_int(profile.car_year), # 安全に数値変換
            number=profile.car_number or "未設定"
        ),
        rules=Rules(
            smoking=bool(profile.no_smoking),
            pet=bool(profile.pet_ok),
            food=bool(profile.food_ok),
            music=bool(profile.music_ok)
        ),
        introduction=profile.bio or ""
    )

@router.put("/mypage")
async def update_driver_mypage(request: Request, body: UpdateDriverRequest, db: Session = Depends(get_db)):
    """
    ドライバー情報の更新（自己紹介のベクトル化を含む）
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="認証が必要です")

    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="セッションが無効です")
    
    user_id = int(user_id_str)

    profile = db.query(modelDB.DriverProfile).filter(
        modelDB.DriverProfile.user_id == user_id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="更新対象のプロフィールが見つかりません")

    # 自己紹介文のベクトル化
    new_embedding = None
    try:
        text_to_embed = body.introduction if body.introduction.strip() else "未設定"
        new_embedding = get_embedding(text_to_embed)
    except Exception as e:
        logger.error(f"ベクトル化失敗: {e}")

    try:
        # DBへ保存（フロントエンドのキー名とDBのカラム名をマッピング）
        profile.bio = body.introduction
        profile.car_model = body.carModel
        profile.car_color = body.carColor
        profile.car_year = body.carYear # 文字列として保存されるためsafe_intは不要
        profile.car_number = body.carNumber
        
        # ルールの更新 (フロントの key名: smoke)
        profile.no_smoking = body.rules.get("smoke", True)
        profile.pet_ok = body.rules.get("pet", False)
        profile.food_ok = body.rules.get("food", True)
        profile.music_ok = body.rules.get("music", True)

        if new_embedding:
            profile.embedding = new_embedding

        db.commit()
        return {"ok": True, "message": "プロフィールを更新しました"}

    except Exception as e:
        db.rollback()
        logger.error(f"DB更新エラー: {e}")
        raise HTTPException(status_code=500, detail="プロフィールの更新に失敗しました")