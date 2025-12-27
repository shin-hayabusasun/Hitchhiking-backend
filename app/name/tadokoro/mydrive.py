from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
import sys

sys.path.append('..')
from db_setting import SessionLocal
import modelDB

# % Start 田所 運転者用ルーターの定義
router = APIRouter(prefix="/api/driver", tags=["driver"])
# % End


# DBセッション
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# % Start 田所 レスポンスの型定義
class DriveInfo(BaseModel):
    recruitment_id: int
    departure: str
    destination: str
    dep_time: str
    status: str


class MyDrivesResponse(BaseModel):
    drives: List[DriveInfo]
# % End


@router.get("/drives", response_model=MyDrivesResponse)
async def get_my_drives(
    token: str = Header(..., description="認証トークン"),
    status: Optional[str] = Query(None, description="ステータスフィルタ"),
    db: Session = Depends(get_db)
):
    """
    マイドライブ情報取得

    処理:
    1. リクエストヘッダーのtokenを検証し，運転者のユーザー IDを特定する.
    2. 「募集のテーブル」から，特定したユーザーIDが作成したレコードを検索する.
    3. クエリパラメータstatus が指定されている場合，募集状況カラムでフィルタリングを行う.
    4. 取得した募集リストを最新の出発時間順にソートして返却する.
    """
    # % Start 田所 マイドライブ取得処理

    # 1. トークン検証とユーザーID特定
    # 実際の実装ではトークンからユーザーIDを復号・検証する処理が入ります
    if not token:
        raise HTTPException(status_code=401, detail="認証トークンが必要です")
    current_user_id = 1  # 仮のID

    # 2. 募集テーブルの検索
    # 日時順ソートのために経路テーブル(Routes)も結合します
    query = db.query(
        modelDB.Recruitment,
        modelDB.Route
    ).join(
        modelDB.Route,
        modelDB.Recruitment.route_id == modelDB.Route.route_id
    ).filter(
        modelDB.Recruitment.recruiter_user_id == current_user_id
    )

    # 3. ステータスフィルタリング
    if status:
        # 設計書 Table 4: status (募集中, 募集終了, 運転完了)
        # 文字列のstatusをDBのコード値に変換して検索する想定
        status_map = {"recruiting": 1, "closed": 2, "completed": 3}
        if status in status_map:
            query = query.filter(modelDB.Recruitment.status == status_map[status])

    # 4. ソート (最新の出発時間順)
    query = query.order_by(desc(modelDB.Route.dep_time))

    results = query.all()

    # レスポンスの構築
    drives_list = []
    for r, route in results:
        # ステータスコードの文字列表現への変換
        status_str = "募集中"
        if r.status == 2:
            status_str = "募集終了"
        elif r.status == 3:
            status_str = "運転完了"

        drives_list.append(DriveInfo(
            recruitment_id=r.recruitment_id,
            departure=str(route.dep_point),
            destination=str(route.arr_point),
            dep_time=str(route.dep_time),
            status=status_str
        ))

    return MyDrivesResponse(drives=drives_list)
    # % End

