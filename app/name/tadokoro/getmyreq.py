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
    # 1. セッションチェック
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Session not found")
    
    user_id = get_current_user(session_id=session_id, db=db)
    if user_id == "no":
        raise HTTPException(status_code=401, detail="Invalid session")

    # 文字列のuser_idを整数に変換（DB定義がIntegerの場合）
    u_id = int(user_id)

    # --- データの取得ロジック ---

    # A. 自分が応募したケース (Application.applicant_user_id == u_id)
    # B. 自分が募集を出して誰かが応募してきたケース (Recruitment.recruiter_user_id == u_id かつ Recruitment.type == 1)
    
    # 全ての関連する申請を取得
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
        "requesting": [],
        "approved": [],
        "completed": []
    }

    for app, rec, route in my_applications:
        # 相手（運転者）の情報を特定する
        # 自分が応募者の場合：募集主が相手
        # 自分が募集主の場合：応募者が相手
        other_party_id = rec.recruiter_user_id if app.applicant_user_id == u_id else app.applicant_user_id
        
        other_user = db.query(modelDB.User).filter(modelDB.User.user_id == other_party_id).first()
        driver_prof = db.query(modelDB.DriverProfile).filter(modelDB.DriverProfile.user_id == other_party_id).first()

        # ステータス判定（リクエストの要件に基づく）
        # app.status -> 0: 申請中, 1: 承認, 2: 完了/評価
        if app.status == 0:
            response_data["requesting"].append(format_item(app, rec, route, other_user, driver_prof, "pending"))
        elif app.status == 1:
            response_data["approved"].append(format_item(app, rec, route, other_user, driver_prof, "approved"))
        elif app.status == 2:
            response_data["completed"].append(format_item(app, rec, route, other_user, driver_prof, "completed"))

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
        # --- 循環参照を完全に断ち切る手順 ---

        # 手順A: Chatテーブル側が持っている application_id を全て NULL にする
        db.query(modelDB.Chat).filter(
            modelDB.Chat.application_id == application_id
        ).update({modelDB.Chat.application_id: None}, synchronize_session=False)

        # 手順B: 今から消そうとしている Application 自身が持っている chat_id も NULL にする
        # これにより Application 側からの参照も消える
        app.chat_id = None
        
        # 一度 DB に反映（フラッシュ）させて制約を緩める
        db.flush()

        # 手順C: どこからも参照されなくなったので、削除を実行
        db.delete(app)

        # 全て確定
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"致命的エラー: {e}")
        raise HTTPException(status_code=500, detail="データベースの制約により削除できませんでした")

    return {"success": True}