import time
# import schedule  <-- 이 라이브러리는 이제 필요 없습니다. main.py의 APScheduler를 쓸 것이기 때문입니다.
from database import get_db_connection

# --- 설정: 가중치 1 ---
SPAN_SHORT = 1
SPAN_PERIODIC = 1 

def calculate_next_ema(prev_ema, current_usage_rate, span):
    alpha = 2 / (span + 1)
    if prev_ema is None:
        return current_usage_rate
    return (current_usage_rate * alpha) + (prev_ema * (1 - alpha))

# 이 함수를 main.py에서 가져다 쓸 것입니다.
def collect_update():
    print(f"\n[📡 {time.strftime('%H:%M:%S')}] 실시간 좌석 정보를 수집합니다...")
    
    conn = get_db_connection()
    if conn is None:
        print("❌ DB 연결 실패")
        return
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT 
                room_id, 
                COUNT(*) as total,
                SUM(CASE WHEN is_occupied = TRUE THEN 1 ELSE 0 END) as used
            FROM study_room_seat
            GROUP BY room_id
        """)
        real_status_list = cursor.fetchall()
    except Exception as e:
        print(f"❌ 좌석 정보 조회 실패: {e}")
        conn.close()
        return
    
    for status in real_status_list:
        room_id = status['room_id']
        total = status['total']
        used = status['used'] if status['used'] is not None else 0
        remain = total - used
        current_rate = used / total if total > 0 else 0

        cursor.execute("""
            SELECT ema_short, ema_periodic 
            FROM study_room_feature_log 
            WHERE room_id = %s 
            ORDER BY record_time DESC 
            LIMIT 1
        """, (room_id,))
        last_record = cursor.fetchone()
        
        last_short = last_record['ema_short'] if last_record else 0.0
        last_periodic = last_record['ema_periodic'] if last_record else 0.0
        
        new_short = calculate_next_ema(last_short, current_rate, SPAN_SHORT)
        new_periodic = calculate_next_ema(last_periodic, current_rate, SPAN_PERIODIC)
        
        cursor.execute("""
            INSERT INTO study_room_feature_log 
            (room_id, record_time, total_seat, used_seat, remain_seat, 
             ema_short, ema_periodic, exam_flag, holiday_flag)
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, 0, 0)
        """, (room_id, total, used, remain, new_short, new_periodic))
        
        print(f"  ✅ {room_id}: 잔여 {remain}석 저장완료")

    conn.commit()
    cursor.close()
    conn.close()
    print("[💤 수집 완료] 대기 모드로 전환합니다.")

# 하단의 while True, schedule.every... 부분은 모두 삭제하세요!