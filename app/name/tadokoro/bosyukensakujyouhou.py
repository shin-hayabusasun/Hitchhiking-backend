from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
import json
import sys

sys.path.append('..')
from db_setting import SessionLocal
import modelDB

# % Start 田所 同乗者用ルーターの定義
router = APIRouter(prefix="/api/hitchhiker", tags=["hitchhiker"])
# % End


# DBセッション
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# % Start 田所 レスポンス・リクエストの型定義
class SearchCard(BaseModel):
    recruitment_id: int
    driver_name: str
    departure: str
    destination: str
    date: str
    money: int
    people: int
    match: float  # マッチング度
    state: str


class SearchResponse(BaseModel):
    card: List[SearchCard]
# % End


@router.get("/boshukensaku", response_model=SearchResponse)
async def search_recruitment(
    filter: Optional[str] = Header(None, description="フィルタするオブジェクトの内容"),
    credentials: str = Header("include", description="セッション"),
    db: Session = Depends(get_db)
):
    """
    募集検索情報取得

    処理:
    1. リクエストヘッダーの情報を取り出す.
    2. フィルタ情報をもとにsql文を作成. また, sql には, user テーブルとプロフィールテーブルなど
       を連結, レコードごとのログインユーザーとのベクトルを計算して, マッチング度を項目に追
       加するという処理も書く. 募集テーブルから募集中という表記のもので取り出す.
    3. 取り出したレコードをオブジェクトの配列化する.
    """
    # % Start 田所 募集検索処理
    
    # 1. ログインユーザーの特定 (セッションからユーザーIDを取得する処理を想定)
    # ここでは仮のユーザーIDを使用
    current_user_id = 1
    
    # フィルタ情報のパース
    filter_dict = {}
    if filter:
        try:
            filter_dict = json.loads(filter)
        except json.JSONDecodeError:
            pass

    # 2. クエリの構築
    # 募集(Recruitments), 経路(Routes), ユーザー(Users), 運転者プロフィール(DriverProfiles)を結合
    # 設計書 5.2.1-2 「募集中という表記のもので取り出す」
    query = db.query(
        modelDB.Recruitment,
        modelDB.Route,
        modelDB.User,
        modelDB.DriverProfile
    ).join(
        modelDB.Route,
        modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).join(
        modelDB.User,
        modelDB.Recruitment.recruiter_user_id == modelDB.User.user_id
    ).join(
        modelDB.DriverProfile,
        modelDB.Recruitment.recruiter_user_id == modelDB.DriverProfile.user_id
    ).filter(
        modelDB.Recruitment.status == 1  # 1: 募集中 (Table 4 参照)
    )

    # フィルタ条件の適用 (filter_dictの内容に応じて分岐)
    if "departure" in filter_dict and filter_dict["departure"]:
        # 出発地での絞り込み例
        query = query.filter(
            modelDB.Route.dep_point.like(f"%{filter_dict['departure']}%")
        )

    # ベクトルマッチング度の計算とソート
    # 設計書 5.2.1-2 「ベクトルを計算して, マッチング度を項目に追加」
    # 注: 実際のベクトル計算はDBの拡張機能(pgvector等)に依存するため、ここではロジックの概念記述とします
    # query = query.order_by(modelDB.DriverProfile.embedding.l2_distance(user_vector))

    results = query.all()

    # 3. レスポンスデータの作成
    cards = []
    for r, route, user, profile in results:
        # マッチング度の計算 (仮の計算式またはDB取得値)
        match_score = 0.0 
        
        cards.append(SearchCard(
            recruitment_id=r.recruitment_id,
            driver_name=user.name,
            departure=str(route.dep_point),  # 座標または地名
            destination=str(route.arr_point),
            date=str(route.dep_time),
            money=r.fare,
            people=r.capacity,
            match=match_score,
            state="募集中" if r.status == 1 else "その他"
        ))

    return SearchResponse(card=cards)
    # % End