import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import initialize_db # database.py에 정의된 초기화 함수 임포트


# 이제 os.environ.get("DATABASE_URL") 등을 통해 접근 가능합니다.
# (나머지 FastAPI 코드는 그대로 유지)


# 💡 API 라우터 임포트 (back.api 폴더에서 가져온다고 가정)
from back.api.user_api import router as user_router 
from back.api.access_api import router as access_router
from back.api.seat_api import router as seat_router 


# 1. Lifespan Context Manager 정의 (on_event 대체)
@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    """
    애플리케이션 시작 및 종료 시 이벤트를 관리합니다.
    서버가 요청을 받기 직전에 DB 초기화를 수행합니다.
    """
    # [STARTUP 로직: 서버 시작 시]
    print("INFO: [STARTUP] 데이터베이스 초기화(스키마 검증) 시작...")
    initialize_db() # 💡 DB 초기화 함수 호출
    print("INFO: [STARTUP] 데이터베이스 초기화 완료.")
    
    # yield: 이 시점에서 서버가 외부 요청을 받기 시작합니다.
    yield 
    
    # [SHUTDOWN 로직: 서버 종료 시]
    print("INFO: [SHUTDOWN] 애플리케이션 종료 작업 실행...")
    # (여기에 DB 연결 풀 해제 등 종료 시 필요한 코드를 넣을 수 있습니다.)


# 2. FastAPI 인스턴스 생성 및 lifespan 연결
app = FastAPI(
    title="OnePass API",
    description="도서관 출입 및 좌석/시설 예약 백엔드 시스템",
    lifespan=lifespan_handler # 💡 FastAPI 생성자에 lifespan 연결
)


# 3. 라우터를 FastAPI 앱에 연결 (경로 접두사 설정)
app.include_router(user_router, prefix="/user", tags=["User Management"])
app.include_router(access_router, prefix="/access", tags=["Access"])
app.include_router(seat_router, prefix="/seat", tags=["Seat Reservation"])


# 4. Uvicorn 서버 실행 블록
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
