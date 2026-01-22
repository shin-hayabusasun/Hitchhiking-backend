# database.py
# SQLAlchemy関連の設定(DB接続、セッション、ベースクラス定義など)

# ...existing code...
import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 環境変数で上書き可能にする
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:shunya@localhost:5432/testdb"
)

# エンジン作成（接続プール設定を追加）
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,        # 常に保持する接続数
    max_overflow=10,    # 必要に応じて追加できる接続数
    pool_pre_ping=True, # 接続の健全性チェック
    pool_recycle=3600   # 1時間後に接続をリサイクル
)

@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cursor.close()

# セッション
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデル定義用ベースクラス
Base = declarative_base()
# ...existing code...