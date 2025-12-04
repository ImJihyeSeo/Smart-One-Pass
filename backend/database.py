import psycopg2
import os

from dotenv import load_dotenv

load_dotenv() 

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        print("FATAL: DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL)

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
        
        -- study_room_seat 테이블
        CREATE TABLE IF NOT EXISTS study_room_seat (
            room_id VARCHAR(50) NOT NULL, 
            seat_number INTEGER NOT NULL, 
            PRIMARY KEY (room_id, seat_number), 
            FOREIGN KEY (room_id) REFERENCES study_room(room_id)
        );

        -- seat_reservation 테이블
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

        -- study_room_status 테이블
        CREATE TABLE IF NOT EXISTS study_room_status (
            status_id SERIAL PRIMARY KEY, 
            room_id VARCHAR(50) NOT NULL, 
            record_time TIMESTAMP WITH TIME ZONE NOT NULL, 
            total_seat INTEGER NOT NULL, 
            used_seat INTEGER NOT NULL, 
            FOREIGN KEY (room_id) REFERENCES study_room(room_id)
        );
    """
    
    cursor = conn.cursor()
    try:
        cursor.execute(CREATE_TABLES_SQL)
        conn.commit()
        print("PostgreSQL 테이블 구조가 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"Database initialization error: {e}")
        conn.rollback() 
    finally:
        cursor.close()
        conn.close()
