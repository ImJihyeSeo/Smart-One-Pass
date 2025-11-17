import pandas as pd
import numpy as np
from database import get_db_connection, initialize_db

# --- 설정: 가중치 1 (과거 반영 안 함 = 현재 값 그대로) ---
# span=1로 설정하면 EMA는 현재 사용률과 100% 동일해집니다.
SPAN_SHORT = 1
SPAN_PERIODIC = 1
FILE_PATH = 'library_seats.csv'

def migrate_csv_to_db():
    print(f"🚀 [AWS 전송] '{FILE_PATH}' 데이터를 DB로 업로드합니다...")
    
    # 1. 테이블 생성 (혹시 없으면 생성)
    initialize_db()
    conn = get_db_connection()
    if conn is None:
        print("❌ DB 연결 실패. .env 파일을 확인해주세요.")
        return
    cursor = conn.cursor()

    # 2. CSV 파일 읽기
    try:
        df = pd.read_csv(FILE_PATH)
        print(f"📂 CSV 로드 성공: {len(df)}행")
    except FileNotFoundError:
        print(f"❌ 오류: '{FILE_PATH}' 파일이 없습니다. 폴더에 넣어주세요.")
        return

    # 3. 데이터 전처리
    # 날짜 컬럼 인식 (CSV 형식에 따라 '날짜' 또는 다른 이름일 수 있음)
    if '날짜' in df.columns:
        df['record_time'] = pd.to_datetime(df['날짜'])
    elif 'record_time' in df.columns:
        df['record_time'] = pd.to_datetime(df['record_time'])
    
    # 시간순 정렬
    df = df.sort_values(by=['열람실명', 'record_time'])

    # 사용률 계산 (분모가 0이면 0으로 처리)
    df['usage_rate'] = df.apply(lambda x: x['사용중'] / x['전체좌석'] if x['전체좌석'] > 0 else 0, axis=1)

    # 4. EMA 계산 (가중치 1 적용 -> 사실상 usage_rate와 동일)
    print("📊 EMA 가중치 1 적용 중...")
    df['ema_short'] = df.groupby('열람실명')['usage_rate'].transform(
        lambda x: x.ewm(span=SPAN_SHORT, adjust=False).mean()
    )
    df['ema_periodic'] = df.groupby('열람실명')['usage_rate'].transform(
        lambda x: x.ewm(span=SPAN_PERIODIC, adjust=False).mean()
    )
    
    # 잔여좌석 계산
    df['remain_seat'] = df['전체좌석'] - df['사용중']

    # 5. DB에 저장 (Bulk Insert)
    print("💾 AWS DB에 저장 시작 (시간이 조금 걸립니다)...")
    
    query = """
        INSERT INTO study_room_feature_log 
        (room_id, record_time, total_seat, used_seat, remain_seat, 
         ema_short, ema_periodic, exam_flag, holiday_flag)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0)
    """
    
    # 데이터프레임을 리스트로 변환하여 저장
    data_to_insert = []
    for _, row in df.iterrows():
        data_to_insert.append((
            row['열람실명'], 
            row['record_time'], 
            int(row['전체좌석']), 
            int(row['사용중']), 
            int(row['remain_seat']), 
            float(row['ema_short']), 
            float(row['ema_periodic'])
        ))
    
    try:
        # executemany로 한 번에 처리 (속도 향상)
        cursor.executemany(query, data_to_insert)
        conn.commit()
        print(f"🎉 성공! 총 {len(data_to_insert)}개의 데이터가 AWS에 저장되었습니다.")
    except Exception as e:
        print(f"❌ 저장 중 오류 발생: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_csv_to_db()