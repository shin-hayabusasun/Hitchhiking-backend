# FastAPIをインポート

from db_setting import engine, Base,SessionLocal#db_setting.pyからエンジンとベースクラスをインポート
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import modelDB#models.pyをインポート(DBモデル定義)
import ai_model#ai-model.pyをインポート(埋め込み生成モデル)
from pydantic import BaseModel
from typing import List


# テーブル作成
modelDB.Base.metadata.create_all(bind=engine)

# FastAPIのインスタンス作成
app = FastAPI()

# Pydantic レスポンスモデル
class UserOut(BaseModel):
    id: int
    name: str
    email: str
    
    class Config:
        orm_mode = True

class DocumentOut(BaseModel):
    id: int
    user_id: int
    content: str
    embedding: List[float]
    
    class Config:
        orm_mode = True
        arbitrary_types_allowed = True
    
    @classmethod
    def from_orm(cls, obj):
        # pgvector の Vector 型を list に変換
        embedding_list = []
        if obj.embedding is not None:
            # numpy配列やpgvector型を確実にリストに変換
            if hasattr(obj.embedding, 'tolist'):
                embedding_list = obj.embedding.tolist()
            else:
                embedding_list = [float(x) for x in obj.embedding]
        
        data = {
            'id': obj.id,
            'user_id': obj.user_id,
            'content': obj.content,
            'embedding': embedding_list
        }
        return cls(**data)

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


@app.post("/users/", response_model=UserOut)
def create_user(name: str, email: str, db: Session = Depends(get_db)):
    user = modelDB.User(name=name, email=email)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")
    db.refresh(user)
    return user

@app.get("/users/", response_model=List[UserOut])
def get_users(db: Session = Depends(get_db)):
    return db.query(modelDB.User).all()

@app.post("/documents/", response_model=DocumentOut)
def create_document(user: int, content: str, db: Session = Depends(get_db)):
    # userをuser_idとして扱う
    # ユーザー存在チェック（外部キー違反の事前防止）
    user_obj = db.query(modelDB.User).filter(modelDB.User.id == user).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail=f"User {user} not found")
    
    embedding = ai_model.get_embedding(content)
    document = modelDB.Document(user_id=user, content=content, embedding=embedding)
    db.add(document)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Foreign key violation")
    db.refresh(document)
    return document

@app.post("/documents/search/")
def search_documents(query: str, top_k: int = 5, db: Session = Depends(get_db)):
    query_embedding = ai_model.get_embedding(query)
    # query_embeddingをvector型の文字列表現に変換
    embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
    # SQLクエリの修正（user_idに合わせる、text()でラップ、vector型にキャスト）
    results = db.execute(
        text("""
        SELECT id, user_id, content, embedding <-> CAST(:query_embedding AS vector) AS distance
        FROM profile_documents
        ORDER BY embedding <-> CAST(:query_embedding AS vector)
        LIMIT :top_k
        """),
        {"query_embedding": embedding_str, "top_k": top_k}
    ).fetchall()
    return [{"id": r.id, "user_id": r.user_id, "content": r.content, "distance": r.distance} for r in results]