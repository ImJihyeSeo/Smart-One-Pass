import time
import schedule
from database import get_db_connection

# --- 설정: 가중치 1 ---
# span=1 -> alpha=1 -> 이전 값 무시, 현재 값 100% 반영
SPAN_SHORT = 1
SPAN_PERIODIC = 1 

def calculate_next_ema(prev_ema, current_usage_rate, span):
    """
    EMA 계산 함수
    span=1일 경우: alpha = 2/(1+1) = 1
    결과 = (current * 1) + (prev * 0) = current
    """
    alpha = 2 / (span + 1)
    # 이전 데이터가 없으면 현재 값 사용
    if prev_ema is None:
        return current_usage_rate
    return (current_usage_rate * alpha) + (prev_ema * (1 - alpha))

def job_30min_real():
    print("\n[📡 수집 시작] 실시간 좌석 정보를 기록합니다...")
    
    conn = get_db_connection()
    if conn is None:
        print("❌ DB 연결 실패")
        return
    cursor = conn.cursor()

    # 1. 실제 좌석 테이블(study_room_seat) 조회
    # (예약 시스템에 의해 is_occupied가 실시간으로 변하는 테이블)
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
    
    # 2. 각 열람실별로 로그 저장
    for status in real_status_list:
        room_id = status['room_id']
        total = status['total']
        used = status['used'] if status['used'] is not None else 0
        remain = total - used
        current_rate = used / total if total > 0 else 0

        # --- 가중치가 1이므로 굳이 이전 EMA를 조회할 필요가 없음 ---
        # 하지만 코드의 일관성을 위해 조회 로직은 유지하되, 계산 결과는 current_rate와 같아짐
        
        # 3. 직전 EMA 조회 (가중치 1이라 계산엔 영향 없지만 로직 유지)
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
        
        # 4. EMA 계산 (결국 current_rate가 됨)
        new_short = calculate_next_ema(last_short, current_rate, SPAN_SHORT)
        new_periodic = calculate_next_ema(last_periodic, current_rate, SPAN_PERIODIC)
        
        # 5. AWS DB에 저장 (Feature Log)
        cursor.execute("""
            INSERT INTO study_room_feature_log 
            (room_id, record_time, total_seat, used_seat, remain_seat, 
             ema_short, ema_periodic, exam_flag, holiday_flag)
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, 0, 0)
        """, (room_id, total, used, remain, new_short, new_periodic))
        
        print(f"  ✅ {room_id}: 잔여 {remain}석 저장완료 (EMA: {new_periodic:.2f})")

    conn.commit()
    cursor.close()
    conn.close()
    print("[💤 수집 종료] 다음 30분 뒤에 실행됩니다.")

# --- 실행 스케줄러 ---
# 1. 켜자마자 테스트로 한 번 실행
job_30min_real()

# 2. 30분마다 반복 실행 예약
schedule.every(30).minutes.do(job_30min_real)

print("🚀 크롤러(수집기)가 가동되었습니다. (종료하려면 Ctrl+C)")

while True:
    schedule.run_pending()
    time.sleep(1)