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
    allow_origins=["*"],  # 本番環境では適切に設定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

################################
####以降を記述する
################################

#ユーザー関連エンドポイントインポート 稗田start

from app.name.hieda import user  # ユーザー関連エンドポイントインポート

# ルーター登録
app.include_router(user.router)














#ユーザー関連エンドポイントインポート 稗田end

#ユーザー関連エンドポイントインポート 田所start



 












#ユーザー関連エンドポイントインポート 田所end

#ユーザー関連エンドポイントインポート 黒星start



 












#ユーザー関連エンドポイントインポート 黒星end


#ユーザー関連エンドポイントインポート ひかるstart



 












#ユーザー関連エンドポイントインポート ヒカルend




#ユーザー関連エンドポイントインポート のりstart



 












#ユーザー関連エンドポイントインポート のりend

#ユーザー関連エンドポイントインポート 五藤start



 












#ユーザー関連エンドポイントインポート 五藤end

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
