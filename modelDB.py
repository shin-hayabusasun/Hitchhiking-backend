# models.py
# SQLAlchemyのモデル定義
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Numeric, Boolean
from sqlalchemy.dialects.postgresql import BYTEA
from db_setting import Base
from pgvector.sqlalchemy import Vector
from datetime import datetime


class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)

# ユーザーテーブル
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(100), nullable=False)
    gender = Column(Integer, nullable=False)  # 不明, 男性, 女性 等
    birth_date = Column(Date, nullable=False)
    address = Column(String(100), nullable=False)
    identity_doc = Column(BYTEA, nullable=False)  # 本人確認書類データ
    #★追加
    admin_flag = Column(Integer, nullable=False, default=0)  # 管理者権限フラグ 1:管理者,0:一般ユーザー


# 運転者情報テーブル
class DriverProfile(Base):
    __tablename__ = "driver_profiles"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True, nullable=False)
    license_id = Column(Integer, nullable=False)
    license_expiry = Column(Date, nullable=False)
    drive_count = Column(Integer, nullable=False, default=0)
    rating = Column(Numeric(2, 1), nullable=False, default=0.0)  # 例: 4.5
    reg_date = Column(Date, nullable=False)
    car_model = Column(String(20), nullable=False)
    car_color = Column(String(10), nullable=False)
    car_year = Column(String(10), nullable=False)
    car_number = Column(String(20), nullable=False)
    no_smoking = Column(Boolean, nullable=True)
    pet_ok = Column(Boolean, nullable=True)
    food_ok = Column(Boolean, nullable=True)
    music_ok = Column(Boolean, nullable=True)
    # 位置情報（緯度・経度）
    latitude = Column(Numeric(10, 8), nullable=True)   # 緯度: -90.0 ~ 90.0
    longitude = Column(Numeric(11, 8), nullable=True)  # 経度: -180.0 ~ 180.0
    bio = Column(String, nullable=True)  # text型
    embedding = Column(Vector(384), nullable=True)


# 同乗者情報テーブル
class PassengerProfile(Base):
    __tablename__ = "passenger_profiles"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True, nullable=False)
    ride_count = Column(Integer, nullable=False, default=0)
    rating = Column(Numeric(2, 1), nullable=False, default=0.0)
    reg_date = Column(Date, nullable=False)
    # 位置情報（緯度・経度）
    latitude = Column(Numeric(10, 8), nullable=True)   # 緯度: -90.0 ~ 90.0
    longitude = Column(Numeric(11, 8), nullable=True)  # 経度: -180.0 ~ 180.0
    bio = Column(String, nullable=True)  # text型
    embedding = Column(Vector(384), nullable=True)


# 経路テーブル
class Route(Base):
    __tablename__ = "routes"

    route_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recruiter_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    # 経路の形状データ（JSON文字列または経由地点のリストとして保存）
    path_data = Column(String, nullable=True)  # 経路情報をJSON等で保存
    dep_time = Column(DateTime, nullable=False)
    # 出発地点（緯度・経度）
    dep_latitude = Column(Numeric(10, 8), nullable=False)
    dep_longitude = Column(Numeric(11, 8), nullable=False)
    arr_time = Column(DateTime, nullable=False)
    # 到着地点（緯度・経度）
    arr_latitude = Column(Numeric(10, 8), nullable=False)
    arr_longitude = Column(Numeric(11, 8), nullable=False)
    #★追加
    arrname = Column(String(100), nullable=False)  # 到着地点名称
    depname = Column(String(100), nullable=False)  # 出発地点名称


# 募集管理テーブル
class Recruitment(Base):
    __tablename__ = "recruitments"

    recruitment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recruiter_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    status = Column(Integer, nullable=False)  # 募集中,募集終了,運転完了
    fare = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False)
    type = Column(Integer, nullable=False)  # 運転者or同乗者からの募集
    route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=False)


# 申請取引テーブル
class Application(Base):
    __tablename__ = "applications"

    application_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recruitment_id = Column(Integer, ForeignKey("recruitments.recruitment_id"), nullable=False)
    applicant_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    status = Column(Integer, nullable=False)  # 申請中, 承認, 否認
    chat_id = Column(Integer, ForeignKey("chats.chat_id"), nullable=False)


# チャットテーブル
class Chat(Base):
    __tablename__ = "chats"

    chat_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message = Column(String, nullable=True)  # text型
    application_id = Column(Integer, ForeignKey("applications.application_id"), nullable=False)


# 決済情報テーブル
class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    card_number = Column(Integer, nullable=False)
    transaction_id = Column(Integer, nullable=True)
    status = Column(Integer, nullable=True)  # 保留中,成功,失敗,取消
    billing_date = Column(DateTime, nullable=True)


# 売上・ポイント残高テーブル
class UserBalance(Base):
    __tablename__ = "user_balances"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True, nullable=False)
    point_balance = Column(Integer, nullable=True, default=0)
    sales_history = Column(Integer, nullable=True, default=0)


# 注文テーブル
class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    order_date = Column(DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    # ★追加: ステータス管理用 (pending, shipped, delivered)
    status = Column(String(20), nullable=False, default="pending")

# 商品テーブル
class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    reg_date = Column(DateTime, nullable=False, default=datetime.now)
    # ★追加: ポイント交換機能用
    points = Column(Integer, nullable=False, default=0)
    description = Column(String, nullable=True)

# 追加　通知設定テーブル
class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    ride_request = Column(Boolean, default=True)  # 相乗りリクエスト
    message = Column(Boolean, default=True)       # メッセージ受信
    reminder = Column(Boolean, default=True)      # リマインド
    promotion = Column(Boolean, default=False)    # お得な情報
    
class notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)








































# 追加　問い合わせテーブル
class Inquiry(Base):
    __tablename__ = "inquiries"

    inquiry_id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    # 対応状況（未対応: 0, 対応中: 1, 完了: 2 など）
    status = Column(Integer, default=0) 
    created_at = Column(DateTime, default=datetime.now)