# データベース構成図

## ER図（Entity Relationship Diagram）

```mermaid
erDiagram
    %% ユーザー関連
    users ||--o| driver_profiles : "1:0..1"
    users ||--o| passenger_profiles : "1:0..1"
    users ||--o| user_balances : "1:0..1"
    users ||--o{ routes : "作成"
    users ||--o{ recruitments : "募集"
    users ||--o{ applications : "申請"
    users ||--o{ payments : "決済"
    users ||--o{ orders : "注文"

    %% 募集・マッチング関連
    routes ||--o{ recruitments : "1:N"
    recruitments ||--o{ applications : "1:N"
    applications ||--|| chats : "1:1"

    %% 商品・注文関連
    products ||--o{ orders : "1:N"

    %% ユーザーテーブル
    users {
        int user_id PK "ユーザーID"
        varchar(20) name "氏名"
        varchar(255) email UK "メールアドレス"
        varchar(100) password "パスワード"
        int gender "性別"
        date birth_date "生年月日"
        varchar(100) address "住所"
        bytea identity_doc "本人確認書類"
    }

    %% 運転者情報テーブル
    driver_profiles {
        int user_id PK "ユーザーID(FK)"
        int license_id "運転免許証ID"
        date license_expiry "免許証有効期限"
        int drive_count "運転回数"
        numeric rating "評価"
        date reg_date "登録日"
        varchar car_model "車種"
        varchar car_color "車の色"
        varchar car_year "車の年式"
        varchar car_number "車のナンバー"
        boolean no_smoking "禁煙車"
        boolean pet_ok "ペット可"
        boolean food_ok "飲食可"
        boolean music_ok "音楽可"
        numeric latitude "緯度"
        numeric longitude "経度"
        text bio "プロフィール"
        vector embedding "埋め込みベクトル"
    }

    %% 同乗者情報テーブル
    passenger_profiles {
        int user_id PK "ユーザーID(FK)"
        int ride_count "同乗回数"
        numeric rating "評価"
        date reg_date "登録日"
        numeric latitude "緯度"
        numeric longitude "経度"
        text bio "プロフィール"
        vector embedding "埋め込みベクトル"
    }

    %% 経路テーブル
    routes {
        int route_id PK "経路ID"
        int recruiter_user_id FK "募集者ユーザーID"
        varchar path_data "経路データ(JSON)"
        datetime dep_time "出発時間"
        numeric dep_latitude "出発地点:緯度"
        numeric dep_longitude "出発地点:経度"
        datetime arr_time "到着時間"
        numeric arr_latitude "到着地点:緯度"
        numeric arr_longitude "到着地点:経度"
    }

    %% 募集管理テーブル
    recruitments {
        int recruitment_id PK "募集ID"
        int recruiter_user_id FK "募集者ユーザーID"
        int status "募集状況"
        int fare "運賃"
        int capacity "募集人数"
        int type "募集タイプ"
        int route_id FK "経路ID"
    }

    %% 申請取引テーブル
    applications {
        int application_id PK "申請取引ID"
        int recruitment_id FK "募集ID"
        int applicant_user_id FK "申請者ユーザーID"
        int status "成立状況"
        int chat_id FK "チャットID"
    }

    %% チャットテーブル
    chats {
        int chat_id PK "チャットID"
        text message "メッセージ"
        int application_id FK "申請取引ID"
    }

    %% 決済情報テーブル
    payments {
        int payment_id PK "決済情報ID"
        int user_id FK "ユーザーID"
        int card_number "カード番号"
        int transaction_id "トランザクションID"
        int status "支払い状況"
        datetime billing_date "請求日時"
    }

    %% 売上・ポイント残高テーブル
    user_balances {
        int user_id PK "ユーザーID(FK)"
        int point_balance "ポイント残高"
        int sales_history "売上履歴"
    }

    %% 注文テーブル
    orders {
        int order_id PK "注文ID"
        int product_id FK "商品ID"
        datetime order_date "注文日時"
        int user_id FK "ユーザーID"
    }

    %% 商品テーブル
    products {
        int product_id PK "商品ID"
        varchar(50) name "商品名"
        int stock "在庫数"
        datetime reg_date "登録日時"
    }
```

## テーブル一覧

### 1. ユーザー管理系
| テーブル名 | 説明 | 主キー |
|-----------|------|--------|
| `users` | ユーザー基本情報 | `user_id` |
| `driver_profiles` | 運転者プロフィール | `user_id` (FK) |
| `passenger_profiles` | 同乗者プロフィール | `user_id` (FK) |
| `user_balances` | ユーザー残高 | `user_id` (FK) |

### 2. 募集・マッチング系
| テーブル名 | 説明 | 主キー |
|-----------|------|--------|
| `routes` | 経路情報 | `route_id` |
| `recruitments` | 募集管理 | `recruitment_id` |
| `applications` | 申請取引 | `application_id` |
| `chats` | チャット | `chat_id` |

### 3. 決済・商品系
| テーブル名 | 説明 | 主キー |
|-----------|------|--------|
| `payments` | 決済情報 | `payment_id` |
| `orders` | 注文 | `order_id` |
| `products` | 商品 | `product_id` |

## リレーションシップの説明

### ユーザーとプロフィール
- 1人のユーザーは、運転者プロフィールと同乗者プロフィールのどちらか（または両方）を持つことができる
- `users` ← `driver_profiles` (1:0..1)
- `users` ← `passenger_profiles` (1:0..1)

### 募集フロー
1. ユーザーが経路を作成 (`routes`)
2. 経路に対して募集を作成 (`recruitments`)
3. 他のユーザーが募集に申請 (`applications`)
4. 申請に対してチャットが紐付く (`chats`)

```
users → routes → recruitments → applications → chats
  ↓                                ↑
  └────────────────────────────────┘
         (申請者として)
```

### 決済フロー
- ユーザーが決済情報を登録 (`payments`)
- ユーザーの残高を管理 (`user_balances`)

### 商品購入フロー
- 商品が存在 (`products`)
- ユーザーが注文 (`orders`)

## 特殊な型の説明

### 位置情報（緯度・経度）
| カラム | 型 | 説明 | 範囲 |
|--------|-----|------|------|
| `latitude` | `NUMERIC(10, 8)` | 緯度 | -90.0 ~ 90.0 |
| `longitude` | `NUMERIC(11, 8)` | 経度 | -180.0 ~ 180.0 |

**使用例:**
```python
# 東京タワーの位置
latitude = 35.65858154
longitude = 139.74543476
```

### AI・機械学習用
| 型 | 説明 | 使用箇所 |
|----|------|---------|
| `vector(384)` | 埋め込みベクトル | プロフィールの意味的検索用 |

## インデックス戦略

### 主キー（自動インデックス）
- すべてのテーブルで主キーに自動的にインデックスが作成される

### ユニークキー
- `users.email` - メールアドレスの重複を防ぐ

### 外部キー
- すべての外部キー列にインデックスが推奨される（JOIN性能向上）

### 推奨される追加インデックス
```sql
-- 検索頻度が高い列
CREATE INDEX idx_recruitments_status ON recruitments(status);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_routes_dep_time ON routes(dep_time);

-- 位置情報検索用（緯度・経度の複合インデックス）
CREATE INDEX idx_driver_location ON driver_profiles(latitude, longitude);
CREATE INDEX idx_passenger_location ON passenger_profiles(latitude, longitude);
CREATE INDEX idx_routes_dep_location ON routes(dep_latitude, dep_longitude);
CREATE INDEX idx_routes_arr_location ON routes(arr_latitude, arr_longitude);

-- ベクトル検索用（IVFFlatインデックス）
CREATE INDEX idx_driver_embedding ON driver_profiles 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_passenger_embedding ON passenger_profiles 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## データフロー例

### 例1: 運転者が同乗者を募集
```
1. 運転者ユーザーがログイン (users)
2. 運転者プロフィール確認 (driver_profiles)
3. 経路を作成 (routes)
4. 募集を作成 (recruitments, type=運転者募集)
5. 同乗者が検索・申請 (applications)
6. チャットでやり取り (chats)
7. 決済 (payments)
```

### 例2: 同乗者が運転者を募集
```
1. 同乗者ユーザーがログイン (users)
2. 同乗者プロフィール確認 (passenger_profiles)
3. 経路を作成 (routes)
4. 募集を作成 (recruitments, type=同乗者募集)
5. 運転者が検索・申請 (applications)
6. チャットでやり取り (chats)
7. 決済 (payments)
```

## 制約と整合性

### NOT NULL制約
- 必須項目には`nullable=False`を設定
- ユーザーの基本情報、決済の重要情報など

### 外部キー制約
- すべての外部キーに`ForeignKey`を設定
- 参照整合性を保証

### デフォルト値
- `drive_count`, `ride_count`: 0
- `rating`: 0.0
- `point_balance`, `sales_history`: 0
- `stock`: 0

### チェック制約（推奨）
```sql
-- 評価は0.0〜5.0の範囲
ALTER TABLE driver_profiles ADD CONSTRAINT check_driver_rating 
  CHECK (rating >= 0.0 AND rating <= 5.0);

ALTER TABLE passenger_profiles ADD CONSTRAINT check_passenger_rating 
  CHECK (rating >= 0.0 AND rating <= 5.0);

-- 運賃は正の値
ALTER TABLE recruitments ADD CONSTRAINT check_fare 
  CHECK (fare >= 0);

-- 募集人数は正の値
ALTER TABLE recruitments ADD CONSTRAINT check_capacity 
  CHECK (capacity > 0);
```

## スケーラビリティの考慮

### パーティショニング（将来的な最適化）
大量データが予想されるテーブル:
- `applications` - 申請日時でパーティション
- `chats` - 作成日時でパーティション
- `payments` - 請求日時でパーティション

### キャッシュ戦略
- ユーザープロフィール: Redis等でキャッシュ
- 募集情報: TTL付きキャッシュ
- 商品在庫: リアルタイム性が必要

---

**作成日**: 2024年12月24日  
**バージョン**: 1.0  
**対応モデル**: `modelDB.py`

