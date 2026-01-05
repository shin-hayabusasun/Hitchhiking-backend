# FastAPI メインアプリケーション
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db_setting import engine
import modelDB

# テーブル作成
modelDB.Base.metadata.create_all(bind=engine)

# FastAPIアプリケーション作成
app = FastAPI(
    title="Rideshare API",
    description="ライドシェアアプリケーションのAPI",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 本番環境では適切に設定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

################################
####以降を記述する
################################

#ユーザー関連エンドポイントインポート 稗田start 30行

from app.name.hieda import user  # ユーザー関連エンドポイントインポート
from app.name.hieda import hitchsearch
# ルーター登録
app.include_router(user.router)
app.include_router(hitchsearch.router)
from app.name.hieda import drive
app.include_router(drive.router)
from app.name.hieda import driverreq
app.include_router(driverreq.router)









#ユーザー関連エンドポイントインポート 稗田end　50行

#ユーザー関連エンドポイントインポート 田所start 52行

from app.name.tadokoro import mydrive  # 1. 作成したファイルをインポート（パスは実際の場所に合わせる）
app.include_router(mydrive.router)     # 2. ルーターをアプリに登録


 










#ユーザー関連エンドポイントインポート 田所end 69行

#ユーザー関連エンドポイントインポート 黒星start 71行 



 












#ユーザー関連エンドポイントインポート 黒星end 88行


#ユーザー関連エンドポイントインポート ひかるstart 91行



 












#ユーザー関連エンドポイントインポート ヒカルend 108行




#ユーザー関連エンドポイントインポート のりstart 113行



 












#ユーザー関連エンドポイントインポート のりend 130行

#ユーザー関連エンドポイントインポート 五藤start 132行



 












#ユーザー関連エンドポイントインポート 五藤end 149行

@app.get("/")
async def root():
    return {
        "message": "Rideshare API - Successfully Running",
        "status": "ok",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy"}


@app.get("/debug/tables")
def list_tables():
    """作成されたテーブル一覧を取得（デバッグ用）"""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return {"tables": tables}
