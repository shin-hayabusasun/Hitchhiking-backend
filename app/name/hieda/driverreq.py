from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import json
import requests
import httpx
import asyncio

# 自作モジュール（既存の環境に合わせてインポートしてください）
import modelDB
from db_setting import SessionLocal
# get_current_user 等の認証が必要な場合はここに追加

router = APIRouter(prefix="/api/test/req", tags=["testdrive"])

# --- データベースセッション設定 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- リクエストモデル定義 ---
class CreateRecruitmentRequest(BaseModel):
    user_id: int
    departure: str
    destination: str
    departuretime: str  # "2026-01-02 18:00" 形式
    capacity: int
    fee: int
    message: str

# --- ヘルパー関数 ---

async def get_coordinates(address: str):
    """LocationIQ APIを使用して座標を取得（非同期版）"""
    import logging
    import asyncio
    import os
    
    logger = logging.getLogger(__name__)
    
    if not address or not address.strip():
        return None, None
    
    api_key = os.getenv("LOCATIONIQ_API_KEY", "pk.4c89f676c0053659bd58a6708715b00e")
    
    max_retries = 3
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                url = "https://us1.locationiq.com/v1/search.php"
                params = {
                    "key": api_key,
                    "q": f"{address}, Japan",
                    "format": "json",
                    "limit": 1
                }
                
                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                if data and len(data) > 0:
                    return float(data[0]['lat']), float(data[0]['lon'])
                    
            except Exception as e:
                logger.error(f"Geocoding error: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
    
    return None, None

async def get_actual_route(start_lat, start_lon, end_lat, end_lon):
    """OSRM APIを使用して実際の道路に沿った経路と所要時間を取得（非同期版）"""
    async with httpx.AsyncClient() as client:
        try:
            # 経緯度の順序 [lon, lat] に注意
            url = f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
            response = await client.get(url, timeout=30.0)
            data = response.json()
            
            if data.get('code') == 'Ok':
                # 経路の座標リスト [[lat, lon], ...]
                coords = data['routes'][0]['geometry']['coordinates']
                path_points = [[c[1], c[0]] for c in coords]
                # 予測所要時間（秒）
                duration = data['routes'][0]['duration']
                return path_points, duration
        except Exception as e:
            print(f"経路探索エラー: {e}")
    
        # API失敗時は直線距離を返す（デフォルト3時間）
        return [[start_lat, start_lon], [end_lat, end_lon]], 10800

# --- APIエンドポイント ---

@router.post("/create_recruitment")
async def create_recruitment(
    req: CreateRecruitmentRequest, 
    db: Session = Depends(get_db)
):
    # 1. 出発地・目的地の座標を特定（ジオコーディング・並列実行）
    dep_coords, arr_coords = await asyncio.gather(
        get_coordinates(req.departure),
        get_coordinates(req.destination)
    )
    dep_lat, dep_lon = dep_coords
    arr_lat, arr_lon = arr_coords

    if dep_lat is None or arr_lat is None:
        raise HTTPException(status_code=400, detail="住所から座標を特定できませんでした。")

    # 2. 実際の走行ルート（道路沿い）を探索
    path_points, travel_duration = await get_actual_route(dep_lat, dep_lon, arr_lat, arr_lon)

    try:
        # 3. 経路テーブル (Route) への登録
        dep_dt = datetime.strptime(req.departuretime, '%Y-%m-%d %H:%M')
        # 到着時刻を予測所要時間から計算
        arr_dt = dep_dt + timedelta(seconds=travel_duration)

        new_route = modelDB.Route(
            recruiter_user_id=req.user_id,
            path_data=json.dumps(path_points),  # 道路沿いの全座標を保存
            dep_time=dep_dt,
            dep_latitude=dep_lat,
            dep_longitude=dep_lon,
            arr_time=arr_dt,
            arr_latitude=arr_lat,
            arr_longitude=arr_lon
        )
        db.add(new_route)
        db.flush()  # 新しく生成された route_id を取得するために実行

        # 4. 募集管理テーブル (Recruitment) への登録
        new_recruitment = modelDB.Recruitment(
            recruiter_user_id=req.user_id,
            status=1,           # 1: 募集中
            fare=req.fee,
            capacity=req.capacity,
            type=0,             # 0: 運転者からの募集
            route_id=new_route.route_id
        )
        db.add(new_recruitment)
        
        # 5. ドライバープロフィールの補足メッセージ (bio) を更新
        driver_profile = db.query(modelDB.DriverProfile).filter(
            modelDB.DriverProfile.user_id == req.user_id
        ).first()
        
        if driver_profile:
            # message を bio（自己紹介・備考欄）に保存
            driver_profile.bio = req.message
        
        db.commit()
        
        return {
            "id": new_recruitment.recruitment_id,
            "message": "ドライブの登録が正常に完了しました。",
            "route_summary": {
                "points": len(path_points),
                "estimated_arrival": arr_dt.strftime('%Y-%m-%d %H:%M')
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"データベース登録エラー: {str(e)}")