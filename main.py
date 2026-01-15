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
    allow_origins=["http://localhost:3000"],  # 本番環境では適切に設定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

################################
####以降を記述する
################################

#ユーザー関連エンドポイントインポート 稗田start 30行

from app.name.hieda import user  # ユーザー関連エンドポイントインポート
from app.name.hieda import hitchsearch
# ルーター登録
app.include_router(user.router)
app.include_router(hitchsearch.router)
from app.name.hieda import drive
app.include_router(drive.router)
from app.name.hieda import driverreq
app.include_router(driverreq.router)
from app.name.tadokoro import mypagekaito
app.include_router(mypagekaito.router)
from app.name.tadokoro import createboshu
app.include_router(createboshu.router)
from app.name.koroboshi import product
from app.name.koroboshi import testproduct
app.include_router(product.router)
app.include_router(testproduct.router)

#ユーザー関連エンドポイントインポート 稗田end　50行

#ユーザー関連エンドポイントインポート 田所start 52行

from app.name.tadokoro import driverdetail, apply_drive  # ← ここに apply_drive を追加
app.include_router(driverdetail.router)
app.include_router(apply_drive.router)
from app.name.tadokoro import my_requests
app.include_router(my_requests.router)
from app.name.tadokoro import create_drive # ← ファイル名と一致しているか
app.include_router(create_drive.router)     # ← router変数を読み込んでいるか
from app.name.tadokoro import driverhensyu # ← ファイル名と一致しているか
app.include_router(driverhensyu.router)  







#ユーザー関連エンドポイントインポート 田所end 70行

#ユーザー関連エンドポイントインポート 黒星start 72行 
from app.name.koroboshi import mypage
app.include_router(mypage.router)
from app.name.koroboshi import driver 
app.include_router(driver.router)





from app.name.koroboshi import pointsshutoku  # ユーザー関連エンドポイントインポート
app.include_router(pointsshutoku.router)
from app.name.koroboshi import tyumon  # ユーザー関連エンドポイントインポート
app.include_router(tyumon.router)
from app.name.koroboshi import orderhis  # ユーザー関連エンドポイントインポート
app.include_router(orderhis.router)

#ユーザー関連エンドポイントインポート 黒星end 89行


#ユーザー関連エンドポイントインポート ひかるstart 92行
from app.name.komastuhikaru import drives # このパスは実際のファイル構成に合わせてください
app.include_router(drives.router)
from app.name.komastuhikaru import driver_requests
app.include_router(driver_requests.router)
from app.name.komastuhikaru import applications
app.include_router(applications.router)
from app.name.komastuhikaru import drivedetail # ファイル名に合わせて
app.include_router(drivedetail.router)
from app.name.komastuhikaru import driver_nearby 
app.include_router(driver_nearby.router)
from app.name.komastuhikaru import request_detail
app.include_router(request_detail.router)
from app.name.komastuhikaru import driver_search
app.include_router(driver_search.router)





#ユーザー関連エンドポイントインポート ヒカルend 109行




#ユーザー関連エンドポイントインポート のりstart 114行

from app.name.nori import Products  # ユーザー関連エンドポイントインポート
# 商品・在庫・注文管理API
app.include_router(Products.router)

from app.name.nori import Stocks  # ★追加: Stockをインポート
# ★追加: 在庫管理API
app.include_router(Stocks.router)
 
from app.name.nori import Orders  # ★追加: Ordersをインポート

app.include_router(Orders.router) # ★追加: ルーターを登録




#ユーザー関連エンドポイントインポート のりend 131行

#ユーザー関連エンドポイントインポート 五藤start 133行
from app.name.goto import settings
app.include_router(settings.router)

from app.name.koroboshi import reviews
app.include_router(reviews.router)









#ユーザー関連エンドポイントインポート 五藤end 150行

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




from app.name.nori import adminmg
app.include_router(adminmg.router)
from app.name.nori import adminuser
app.include_router(adminuser.router)
from app.name.nori import deleteuser
app.include_router(deleteuser.router)

from app.name.koroboshi import sukejuru
app.include_router(sukejuru.router)
from app.name.koroboshi import shinkou
app.include_router(shinkou.router)
from app.name.koroboshi import kanryou
app.include_router(kanryou.router)
from app.name.koroboshi import Delyotei
app.include_router(Delyotei.router)
from app.name.goto import inquiry   # ★追加
app.include_router(inquiry.router) # ★追加
