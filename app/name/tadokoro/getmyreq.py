from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Any
from datetime import datetime

import modelDB
from db_setting import SessionLocal
from app.name.hieda.user import get_current_user # パスは適宜調整してください

router = APIRouter(prefix="/api/hitchhiker", tags=["my-requests"])

# DBセッション
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ヘルパー関数：DBモデルをフロントエンド用の辞書形式に変換
def format_item(app: modelDB.Application, recruitment: modelDB.Recruitment, route: modelDB.Route, other_user: modelDB.User, driver_profile: modelDB.DriverProfile, status_label: str):
    return {
        "id": app.application_id,
        "name": other_user.name,
        "rating": float(driver_profile.rating) if driver_profile else 0.0,
        "reviews": driver_profile.drive_count if driver_profile else 0,
        "from": route.depname,
        "to": route.arrname,
        "date": route.dep_time.strftime('%Y-%m-%d'),
        "time": route.dep_time.strftime('%Y-%m-%d %H:%M'),
        "price": recruitment.fare,
        "status": status_label,
        "carinfo": f"{driver_profile.car_model} ({driver_profile.car_color})" if driver_profile else "情報なし"
    }

@router.get("/my-requests")
async def get_my_requests(request: Request, db: Session = Depends(get_db)):
    # 1. セッション・ユーザー取得（中略）
    session_id = request.cookies.get("session_id")
    user_id = get_current_user(session_id=session_id, db=db)
    if user_id == "no":
        raise HTTPException(status_code=401)
    u_id = int(user_id)

    # データの取得
    my_applications = db.query(
        modelDB.Application, 
        modelDB.Recruitment, 
        modelDB.Route
    ).join(
        modelDB.Recruitment, modelDB.Application.recruitment_id == modelDB.Recruitment.recruitment_id
    ).join(
        modelDB.Route, modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).filter(
        or_(
            modelDB.Application.applicant_user_id == u_id,
            modelDB.Recruitment.recruiter_user_id == u_id
        )
    ).all()

    response_data = {
        "requesting": [],  # 申請中 (Pending)
        "approved": [],    # 承認済み・進行中
        "completed": [],   # 完了 (rec.status == 2)
        "rejected": []     # 拒否 (app.status == 2) ★追加
    }

    for app, rec, route in my_applications:
        # 相手情報の取得
        other_party_id = rec.recruiter_user_id if app.applicant_user_id == u_id else app.applicant_user_id
        other_user = db.query(modelDB.User).filter(modelDB.User.user_id == other_party_id).first()
        driver_prof = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == other_party_id).first()

        # --- ステータス判定の修正 ---
        
        # 1. まずドライブ自体が完了しているか確認
        if rec.status == 2:
            response_data["completed"].append(format_item(app, rec, route, other_user, driver_prof, "completed"))
        
        # 2. 申請が拒否（否認）された場合
        elif app.status == 2:
            response_data["rejected"].append(format_item(app, rec, route, other_user, driver_prof, "no"))
        
        # 3. 申請が承認されている場合
        elif app.status == 1:
            response_data["approved"].append(format_item(app, rec, route, other_user, driver_prof, "approved"))
        
        # 4. まだ申請中の場合
        elif app.status == 0:
            response_data["requesting"].append(format_item(app, rec, route, other_user, driver_prof, "pending"))

    return {
        "success": True,
        "data": response_data
    }

# --- キャンセルAPI（フロントエンドのhandleCancel用） ---
@router.delete("/cancel-request/{application_id}")
async def cancel_request(application_id: int, request: Request, db: Session = Depends(get_db)):
    # 1. ユーザー認証
    session_id = request.cookies.get("session_id")
    user_id_str = get_current_user(session_id=session_id, db=db)
    if user_id_str == "no":
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = int(user_id_str)

    # 2. 削除対象の申請(Application)をまず取得
    app = db.query(modelDB.Application).filter(
        modelDB.Application.application_id == application_id,
        modelDB.Application.applicant_user_id == user_id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="リクエストが見つかりません")

    try:
        # Application削除前に、関連するChatのapplication_idをNULLにする
        db.query(modelDB.Chat).filter(
            modelDB.Chat.application_id == application_id
        ).update({modelDB.Chat.application_id: None}, synchronize_session=False)
        
        # Applicationを削除
        db.delete(app)
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"致命的エラー: {e}")
        raise HTTPException(status_code=500, detail="データベースの制約により削除できませんでした")

    return {"success": True}