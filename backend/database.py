# database.py

import sqlite3
from typing import Optional

# 🚨 DB 파일 경로는 라즈베리파이의 실제 경로로 설정하세요.
DATABASE_PATH = './assets/OnePassDB.db' 

def get_db_connection() -> Optional[sqlite3.Connection]:
    """SQLite DB에 연결하고 Connection 객체를 반환합니다."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        # 결과를 딕셔너리(JSON)처럼 '이름표: 값' 형태로 가져오기 위해 설정
        conn.row_factory = sqlite3.Row 
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def initialize_db():
    """DB 파일이 없으면 테이블을 생성하고 초기화합니다."""
    conn = get_db_connection()
    if conn is None:
        print("FATAL: DB connection failed during initialization.")
        return

    cursor = conn.cursor()
    try:
        # 🚨 당신이 설계한 CREATE TABLE SQL 문들을 여기에 순서대로 넣습니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                sid TEXT PRIMARY KEY,
                face BLOB NOT NULL,
                card TEXT NOT NULL
            )
                       
            CREATE TABLE IF NOT EXISTS log (
                log_id INTEGER PRIMARY KEY, 
                sid TEXT, 
                enter TEXT NOT NULL, 
                exit TEXT, 
                FOREIGN KEY (sid) REFERENCES students(sid)
            );

            CREATE TABLE IF NOT EXISTS study_room (
                room_id TEXT PRIMARY KEY, 
                room_name TEXT NOT NULL, 
                location TEXT,
                open TEXT, 
                close TEXT
            );

            CREATE TABLE IF NOT EXISTS study_room_seat (
                room_id TEXT NOT NULL, 
                seat_number INTEGER NOT NULL, 
                PRIMARY KEY (room_id, seat_number), 
                FOREIGN KEY (room_id) REFERENCES study_room(room_id)
            );

            CREATE TABLE IF NOT EXISTS seat_reservation (
                reservation_id INTEGER PRIMARY KEY,
                sid TEXT NOT NULL, 
                room_id TEXT NOT NULL, 
                seat_number INTEGER NOT NULL, 
                date TEXT NOT NULL, 
                start_time TEXT NOT NULL, 
                end_time TEXT NOT NULL, 
                FOREIGN KEY (sid) REFERENCES students(sid), 
                FOREIGN KEY (room_id, seat_number) REFERENCES study_room_seat(room_id, seat_number)
            );

            CREATE TABLE IF NOT EXISTS study_room_status (
                status_id INTEGER PRIMARY KEY, 
                room_id TEXT NOT NULL, 
                record_time TEXT NOT NULL, 
                total_seat INTEGER NOT NULL, 
                used_seat INTEGER NOT NULL, 
                FOREIGN KEY (room_id) REFERENCES study_room(room_id)
            );
        """)
        # ... (log, facilities, facility_reservation 등 나머지 테이블 생성 쿼리)
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
    finally:
        conn.close()

# Note: main.py에서 initialize_db()를 서버 시작 전에 호출해야 합니다.
