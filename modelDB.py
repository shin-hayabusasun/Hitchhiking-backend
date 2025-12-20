# models.py
# SQLAlchemyのモデル定義
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from db_setting import Base
from pgvector.sqlalchemy import Vector
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)
    documents = relationship("Document", back_populates="user_rel")
    cash = relationship("cash", back_populates="user_rel")
    recruitment = relationship("recruitment", back_populates="user_rel")
    root = relationship("root", back_populates="user_rel")

class Document(Base):
    __tablename__ = "profile_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    gps = Column(String)
    content = Column(String)
    embedding = Column(Vector(384))
    user_rel = relationship("User", back_populates="documents")

class cash(Base):
    __tablename__ = "cash"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    cash = Column(Integer)
    point = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    user_rel = relationship("User", back_populates="cash")

class recruitment(Base):
    __tablename__ = "recruitment"
    id = Column(Integer, primary_key=True, index=True)
    re_user_id = Column(Integer, ForeignKey("users.id"))
    re_re_user_id = Column(Integer, ForeignKey("users.id"))
    re_created_at = Column(DateTime, default=datetime.now)
    cash = Column(Integer)
    accept = Column(String)
    finish = Column(String)
    root_id = Column(ForeignKey("root.id"))
    user_rel = relationship("User", back_populates="recruitment")
    root_rel = relationship("root", back_populates="recruitment")

class root(Base):
    __tablename__ = "root"
    id = Column(Integer, primary_key=True, index=True)
    root_user_id = Column(Integer, ForeignKey("users.id"))
    root = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    user_rel = relationship("User", back_populates="root")