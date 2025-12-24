# プロジェクト構造

## ディレクトリ構成

```
fastAPI/
├── app/
│   ├── __init__.py
│   ├── api/                    # API エンドポイント
│   │   ├── __init__.py
│   │   ├── user.py            # /api/user/* (ログイン、登録、ログアウト)
│   │   ├── hitchhiker.py      # /api/hitchhiker/* (同乗者用)
│   │   ├── driver.py          # /api/driver/* (運転者用)
│   │   ├── drives.py          # /api/drives (ドライブ管理)
│   │   └── applications.py    # /api/applications (申請管理)
│   ├── admin/                  # 管理者用 エンドポイント
│   │   ├── __init__.py
│   │   ├── customers.py       # admin/customers (顧客管理)
│   │   └── orders.py          # admin/orders (注文管理)
│   └── schemas/                # Pydanticスキーマ
│       ├── __init__.py
│       └── common.py          # 共通スキーマ
├── main.py                     # エントリポイント
├── db_setting.py              # データベース設定
├── modelDB.py                 # SQLAlchemyモデル
├── ai_model.py                # AI埋め込みモデル
├── docker-compose.yml         # Docker構成
├── Dockerfile.dev             # 開発用Dockerfile
└── requirement.txt            # Python依存パッケージ
```

## API エンドポイント一覧

### ユーザー認証 (`/api/user/*`)
- `POST /api/user/login` - ログイン
- `POST /api/user/regist` - ユーザー登録
- `GET /api/user/logout` - ログアウト
- `GET /api/user/IsLogin` - ログイン状態確認

### 同乗者用 (`/api/hitchhiker/*`)
- `GET /api/hitchhiker/boshukensaku` - 募集検索

### 運転者用 (`/api/driver/*`)
- `GET /api/driver/drives` - マイドライブ一覧取得
- `GET /api/driver/requests` - 申請一覧取得

### ドライブ管理 (`/api/drives`)
- `POST /api/drives/` - ドライブ新規登録
- `GET /api/drives/{id}` - ドライブ詳細取得
- `PUT /api/drives/{id}` - ドライブ情報更新
- `DELETE /api/drives/{id}` - ドライブ削除

### 申請管理 (`/api/applications`)
- `POST /api/applications/` - 申請作成
- `POST /api/applications/{id}/approve` - 申請承認
- `POST /api/applications/{id}/reject` - 申請拒否

### 管理者：顧客管理 (`admin/customers`)
- `GET /admin/customers/` - 顧客一覧取得
- `GET /admin/customers/stats` - 顧客統計情報取得
- `POST /admin/customers/{id}/warn` - 顧客警告送信
- `DELETE /admin/customers/{id}` - 顧客アカウント削除

### 管理者：注文管理 (`admin/orders`)
- `GET /admin/orders/` - 注文一覧取得
- `GET /admin/orders/stats` - 注文統計情報取得
- `PUT /admin/orders/{id}/status` - 注文ステータス更新

## 今後追加予定のエンドポイント

以下のエンドポイントは、API.mdに定義されていますが、まだ実装されていません：

- `/api/passenger-requests/*` - 同乗者リクエスト管理
- `/api/point/*` - ポイント管理
- `/api/points/*` - ポイント関連
- `/api/inquiry` - 問い合わせ
- `/api/users/me` - ユーザー情報取得・更新
- `/api/settings/*` - 設定
- `/api/payment/*` - 決済
- `admin/products` - 商品管理
- `admin/stocks` - 在庫管理

## 開発の進め方

1. **新しいエンドポイントの追加**
   ```python
   # app/api/新しいファイル.py
   from fastapi import APIRouter
   router = APIRouter(prefix="/api/新しいパス", tags=["タグ名"])
   
   @router.get("/")
   async def example():
       return {"message": "example"}
   ```

2. **main.pyに登録**
   ```python
   from app.api import 新しいファイル
   app.include_router(新しいファイル.router)
   ```

3. **テスト**
   ```bash
   docker-compose up -d
   # http://localhost:8000/docs でAPIドキュメント確認
   ```

## 実装状況

- ✅ プロジェクト構造作成
- ✅ 基本エンドポイント実装（TODOコメント付き）
- ⬜ 各エンドポイントの詳細実装
- ⬜ 認証・セッション管理
- ⬜ データベース操作の実装
- ⬜ バリデーションとエラーハンドリング
- ⬜ テストコード作成

## 次のステップ

1. 各ルーターの TODO 部分を実装
2. 認証ミドルウェアの追加
3. データベース操作の実装
4. エラーハンドリングの強化
5. 残りのエンドポイントの追加

