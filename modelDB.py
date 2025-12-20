# models.py
# SQLAlchemyのモデル定義
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from db_setting import Base
from pgvector.sqlalchemy import Vector
from datetime import datetime

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

class root(Base):
    __tablename__ = "root"
    id = Column(Integer, primary_key=True, index=True)
    root_user_id = Column(Integer, ForeignKey("users.id"))
    root = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    user_rel = relationship("User", back_populates="root")
    recruitment = relationship("recruitment", back_populates="root_rel")

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
    # recruitment 側でどの外部キーを使うかを明示（User は後で定義）
    user_rel = relationship("User", foreign_keys=[re_user_id], back_populates="recruitment_sent")
    re_user_rel = relationship("User", foreign_keys=[re_re_user_id], back_populates="recruitment_received")
    root_rel = relationship("root", back_populates="recruitment")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)
    documents = relationship("Document", back_populates="user_rel")
    cash = relationship("cash", back_populates="user_rel")
    # recruitment は送信/受信で 2 つに分ける
    # recruitment クラス定義が先にあるため、下の recruitment.re_user_id 参照が有効
    recruitment_sent = relationship(
        "recruitment",
        back_populates="user_rel",
        foreign_keys=[recruitment.re_user_id]
    )
    recruitment_received = relationship(
        "recruitment",
        back_populates="re_user_rel",
        foreign_keys=[recruitment.re_re_user_id]
    )
    root = relationship("root", back_populates="user_rel")