import time
from database import get_db_connection

# 1. 좌석 상태 수집
def collect_update():
    
    print(f"\n[📡 {time.strftime('%H:%M:%S')}] 실시간 좌석 상태 수집 시작...")
    
    conn = get_db_connection()
    if conn is None:
        print("❌ DB 연결 실패")
        return
    cursor = conn.cursor()

    try:
        query = """
            WITH TotalSeats AS (
                SELECT room_id, COUNT(*) as total
                FROM study_room_seat
                GROUP BY room_id
            ),
            UsedSeats AS (
                SELECT room_id, COUNT(*) as used
                FROM seat_reservation
                WHERE start_time <= NOW() 
                  AND end_time > NOW() 
                  AND return_time IS NULL
                GROUP BY room_id
            )
            SELECT 
                T.room_id,
                T.total,
                COALESCE(U.used, 0) as used  -- 예약이 하나도 없으면 0으로 처리
            FROM TotalSeats T
            LEFT JOIN UsedSeats U ON T.room_id = U.room_id;
        """
        
        cursor.execute(query)
        current_status_list = cursor.fetchall()

        if not current_status_list:
            print("[경고] 'study_room_seat' 테이블이 비어있거나 데이터가 없습니다.")

    except Exception as e:
        print(f"❌ 좌석 데이터 집계 중 에러 발생: {e}")
        conn.close()
        return
    
    # 조회된 정보를 study_room_status 테이블에 저장 (Log)
    inserted_count = 0
    try:
        for status in current_status_list:
            room_id = status['room_id']
            total = status['total']
            used = status['used']
            
            if used > total:
                used = total

            cursor.execute("""
                INSERT INTO study_room_status 
                (room_id, record_time, total_seat, used_seat)
                VALUES (%s, NOW(), %s, %s)
            """, (room_id, total, used))
            
            print(f"  ✅ {room_id.ljust(10)} : {str(used).rjust(3)} / {str(total).rjust(3)} 명 (기록됨)")
            inserted_count += 1
            
        conn.commit()
        
    except Exception as e:
        print(f"❌ DB 저장(INSERT) 중 에러: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
    print(f"[수집 완료] 총 {inserted_count}개 열람실 상태 기록됨.")