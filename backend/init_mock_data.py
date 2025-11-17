# init_mock_data.py
import pandas as pd
from database import get_db_connection, initialize_db

def load_csv_to_mock_table():
    # 1. 테이블 생성
    initialize_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 2. CSV 읽기
    df = pd.read_csv('library_seats.csv')
    
    # 날짜 변환 (CSV 형식에 맞춰 수정 필요)
    # 예: '2025-09-25 06:00:00' 포맷이라고 가정
    if '날짜' in df.columns:
        df['record_time'] = pd.to_datetime(df['날짜'])
    
    print(f"🚀 가상 데이터 {len(df)}개를 'raw_library_seats' 테이블에 적재합니다...")

    # 3. DB에 넣기
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO raw_library_seats 
                (record_time, room_name, total_seat, used_seat)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (row['record_time'], row['열람실명'], int(row['전체좌석']), int(row['사용중'])))
        except Exception as e:
            print(f"에러 발생 (무시): {e}")

    conn.commit()
    conn.close()
    print("✅ 가상 홈페이지 구축 완료! (Mock Data Load Complete)")

if __name__ == "__main__":
    load_csv_to_mock_table()