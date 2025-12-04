import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import initialize_db
import pandas as pd
import os
from collector import collect_update
from apscheduler.schedulers.background import BackgroundScheduler
from back.services.core_service import execute_auto_return
from back.api import seat_api

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from back.api.user_api import router as user_router 
from back.api.access_api import router as access_router
from back.api.seat_api import router as seat_router 
from back.api.predict_api import router as predict_router 


@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    print("INFO: [STARTUP] 데이터베이스 초기화(스키마 검증) 시작...")
    initialize_db()
    print("INFO: [STARTUP] 데이터베이스 초기화 완료.")

    
    # 스케줄러 생성
    scheduler = BackgroundScheduler()

    # execute_auto_return 함수를 5분마다 실행
    scheduler.add_job(execute_auto_return, 'interval', minutes=5)

    # 좌석 정보 수집 
    # 매 시간 0분과 30분에 실행 (예: 12:00, 12:30, 13:00...)
    scheduler.add_job(collect_update, 'cron', minute='0,30')
    scheduler.start()
    
    yield 
    
    print("INFO: [SHUTDOWN] 애플리케이션 종료 작업 실행...")
    scheduler.shutdown()

app = FastAPI(
    title="OnePass API",
    description="도서관 출입 및 좌석/시설 예약 백엔드 시스템",
    lifespan=lifespan_handler
)


app.include_router(user_router, prefix="/user", tags=["User Management"])
app.include_router(access_router, prefix="/access", tags=["Access"])
app.include_router(seat_router, prefix="/seat", tags=["Seat Reservation"])
app.include_router(predict_router, prefix="/predict", tags=["Seat Prediction"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
