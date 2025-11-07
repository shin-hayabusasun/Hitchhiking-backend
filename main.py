# FastAPIをインポート

from db_setting import engine, Base,SessionLocal#db_setting.pyからエンジンとベースクラスをインポート
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import modelDB#models.pyをインポート(DBモデル定義)


# テーブル作成
modelDB.Base.metadata.create_all(bind=engine)

# FastAPIのインスタンス作成
app = FastAPI()

# DBセッションをリクエストごとに生成・破棄する
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GETメソッドでルートURLにアクセスされたときの処理
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/users/")
def create_user(name: str, email: str, db: Session = Depends(get_db)):
    user = modelDB.User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.get("/users/")
def get_users(db: Session = Depends(get_db)):
    return db.query(modelDB.User).all()
