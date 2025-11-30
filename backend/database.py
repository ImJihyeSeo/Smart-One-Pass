# database.py


import psycopg2
from psycopg2 import extras
import os
from typing import Optional

from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv() 

# AWS로 전환하기 쉽도록 DATABASE_URL 환경 변수를 사용합니다.
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    """PostgreSQL DB에 연결하고 Connection 객체를 반환합니다."""
    if not DATABASE_URL:
        print("FATAL: DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        return None
    try:
        # PostgreSQL 연결 문자열을 사용하여 접속
        conn = psycopg2.connect(DATABASE_URL)
        # 결과를 딕셔너리처럼 가져오기 위한 설정
        # (SQLite의 conn.row_factory = sqlite3.Row 역할)
        # conn.row_factory = extras.RealDictCursor 를 사용하려면 cursor를 만들 때 지정합니다.

        conn.cursor_factory = psycopg2.extras.RealDictCursor

        cursor = conn.cursor()
        cursor.execute("SET timezone = 'Asia/Seoul';")
        cursor.close()
        
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def initialize_db():
    """PostgreSQL 서버에 접속하여 테이블을 생성하고 초기화합니다."""
    conn = get_db_connection()
    if conn is None:
        return

    # PostgreSQL용 SQL 문법으로 테이블을 정의합니다.
    # PRIMARY KEY가 필요한 테이블은 INTEGER 대신 SERIAL을 사용해 자동 증가를 설정합니다.
    CREATE_TABLES_SQL = """
        -- students 테이블 (face: BLOB -> BYTEA)
        CREATE TABLE IF NOT EXISTS students (
            sid VARCHAR(50) PRIMARY KEY, 
            name VARCHAR(100),
            face BYTEA
        );

        -- log 테이블 (log_id: INTEGER -> SERIAL)
        CREATE TABLE IF NOT EXISTS log (
            log_id SERIAL PRIMARY KEY, 
            sid VARCHAR(50), 
            enter TIMESTAMP WITH TIME ZONE NOT NULL, 
            exit TIMESTAMP WITH TIME ZONE, 
            FOREIGN KEY (sid) REFERENCES students(sid)
        );

        -- study_room 테이블
        CREATE TABLE IF NOT EXISTS study_room (
            room_id VARCHAR(50) PRIMARY KEY, 
            room_name VARCHAR(100) NOT NULL, 
            location VARCHAR(100),
            open TIME NOT NULL,
            close TIME NOT NULL
        );

        # -- study_room_seat 테이블
        # CREATE TABLE IF NOT EXISTS study_room_seat (
        #     room_id VARCHAR(50) NOT NULL, 
        #     seat_number INTEGER NOT NULL, 
        #     PRIMARY KEY (room_id, seat_number), 
        #     FOREIGN KEY (room_id) REFERENCES study_room(room_id)
        # );

        -- seat_reservation 테이블 (reservation_id: INTEGER -> SERIAL, 날짜/시간 타입 변경)
        CREATE TABLE IF NOT EXISTS seat_reservation (
            reservation_id SERIAL PRIMARY KEY,
            sid VARCHAR(50) NOT NULL, 
            room_id VARCHAR(50) NOT NULL, 
            seat_number INTEGER NOT NULL, 
            date DATE NOT NULL, 
            start_time TIMESTAMP NOT NULL, 
            end_time TIMESTAMP NOT NULL, 
            return_time TIMESTAMP WITH TIME ZONE,
            FOREIGN KEY (sid) REFERENCES students(sid), 
            FOREIGN KEY (room_id, seat_number) REFERENCES study_room_seat(room_id, seat_number)
        );

        -- study_room_status 테이블 (status_id: INTEGER -> SERIAL, record_time 타입 변경)
        CREATE TABLE IF NOT EXISTS study_room_status (
            status_id SERIAL PRIMARY KEY, 
            room_id VARCHAR(50) NOT NULL, 
            record_time TIMESTAMP WITH TIME ZONE NOT NULL, 
            total_seat INTEGER NOT NULL, 
            used_seat INTEGER NOT NULL, 
            FOREIGN KEY (room_id) REFERENCES study_room(room_id)
        );

        --Random Forest용 로그
        CREATE TABLE IF NOT EXISTS study_room_feature_log (
            log_id SERIAL PRIMARY KEY,
            
            -- 1. 기본 식별 정보
            room_id VARCHAR(50) NOT NULL,    -- CSV의 '열람실 ID' (매핑 필요 시 주의)
            record_time TIMESTAMP WITH TIME ZONE NOT NULL, -- '년','월','일','시간'을 하나로 합침
            
            -- 2. 좌석 정보 (CSV: 잔여좌석, 전체좌석, 사용중)
            total_seat INTEGER NOT NULL,     -- 전체좌석
            used_seat INTEGER NOT NULL,      -- 사용중
            remain_seat INTEGER NOT NULL,    -- 잔여좌석 (Target)
            
            -- 3. EMA 피처 (핵심 모델 재료)
            ema_short DOUBLE PRECISION DEFAULT 0.0,    -- CSV: EMA_Short (단기)
            ema_periodic DOUBLE PRECISION DEFAULT 0.0, -- CSV: EMA_Periodic (장기)
            
            -- 4. 날짜/시즌 특성 플래그 (CSV 피처 반영)
            exam_flag INTEGER DEFAULT 0,          -- CSV: Exam_Flag
            holiday_flag INTEGER DEFAULT 0,       -- CSV: Holiday_Flag
            post_holiday_flag INTEGER DEFAULT 0,  -- CSV: Post_Holiday_Flag
            
            -- 5. 메타 정보 (언제 수집했는지)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- 외래 키 (필요한 경우만 사용, room_id가 study_room 테이블과 일치한다는 가정)
            FOREIGN KEY (room_id) REFERENCES study_room(room_id)
        );
        
        -- (선택) 빠른 조회를 위한 인덱스 생성 (시간순 정렬 조회 시 속도 향상)
        CREATE INDEX IF NOT EXISTS idx_feature_log_time ON study_room_feature_log (record_time);
        CREATE INDEX IF NOT EXISTS idx_feature_log_room ON study_room_feature_log (room_id);
    """
    
    cursor = conn.cursor()
    try:
        # 모든 테이블 생성 SQL을 한 번에 실행합니다.
        cursor.execute(CREATE_TABLES_SQL)
        conn.commit()
        print("PostgreSQL 테이블 구조가 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"Database initialization error: {e}")
        conn.rollback() # 오류 발생 시 작업을 되돌립니다.
    finally:
        cursor.close()
        conn.close()

    # Note: main.py에서 initialize_db()를 서버 시작 전에 호출해야 합니다.