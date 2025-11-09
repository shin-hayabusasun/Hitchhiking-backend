# models.py
# SQLAlchemyのモデル定義
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db_setting import Base
from pgvector.sqlalchemy import Vector

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    documents = relationship("Document", back_populates="user_rel")

class Document(Base):
    __tablename__ = "profile_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    embedding = Column(Vector(384))
    user_rel = relationship("User", back_populates="documents")