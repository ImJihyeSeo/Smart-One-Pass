# init_db_with_csv.py

import pandas as pd
from database import get_db_connection, initialize_db

# 📂 코랩에서 생성한 최종 CSV 파일명
FILE_PATH = 'final_features_with_ema.csv'

# 🚨 [중요] 코랩의 숫자 ID -> DB의 문자열 ID 매핑
# 코랩 코드: pd.factorize(df['열람실명'])[0] + 1
# 일반적으로 데이터 등장 순서대로 번호가 매겨집니다.
# 만약 DB 에러(FK 제약 조건)가 발생하면 이 숫자를 서로 바꿔보세요.
ID_MAPPING = {
    1: "1",         # 제1열람실
    2: "2-1",       # 제2-1열람실
    3: "2-2",       # 제2-2열람실
    4: "2-2_grad"   # 대학원열람실
}

def migrate_features_to_db():
    print(f"🚀 [데이터 적재] '{FILE_PATH}' 파일의 처리된 데이터를 DB로 전송합니다...")
    
    # 1. DB 테이블 초기화 (테이블이 없으면 생성)
    initialize_db()
    
    conn = get_db_connection()
    if conn is None:
        print("❌ DB 연결 실패")
        return
    cursor = conn.cursor()

    # 2. CSV 파일 읽기
    try:
        df = pd.read_csv(FILE_PATH)
        print(f"📂 CSV 로드 성공: {len(df)}행")
    except FileNotFoundError:
        print(f"❌ 오류: '{FILE_PATH}' 파일이 없습니다. 폴더에 파일을 넣어주세요.")
        return

    # 3. 데이터 변환 (Colab 형식 -> DB 형식)
    print("⚙️ 데이터 변환 중 (Time reconstruction & ID Mapping)...")

    # (1) 시간 정보 복원: 년,월,일,시간 컬럼을 합쳐서 datetime 객체로 변환
    try:
        df['record_time'] = pd.to_datetime({
            'year': df['년'],
            'month': df['월'],
            'day': df['일'],
            'hour': df['시간']
        })
    except Exception as e:
        print(f"❌ 시간 변환 오류: {e}")
        return

    # (2) Room ID 매핑 (숫자 -> 문자열)
    # 맵핑에 없는 번호가 나오면 에러가 날 수 있으므로 확인 필요
    # # 2. 🚨 표준 ID로 변환 (여기서 통일됨)
    # '열람실 ID' 컬럼이 있으면 그걸 쓰고, 없으면 '열람실명' 등 다른 컬럼 사용
    target_col = '열람실 ID' if '열람실 ID' in df.columns else 'room_id'
    df['room_id_str'] = df[target_col].map(ID_MAPPING)

    # 매핑 실패 확인
    if df['room_id_str'].isnull().any():
        print("⚠️ 경고: 매핑되지 않은 열람실 ID가 있습니다. ID_MAPPING을 확인하세요.")
        print(df[df['room_id_str'].isnull()]['열람실 ID'].unique())
        return

    # 4. DB에 저장 (Bulk Insert)
    print("💾 PostgreSQL DB에 저장 시작...")

    # DB 스키마 순서:
    # room_id, record_time, total_seat, used_seat, remain_seat, 
    # ema_short, ema_periodic, exam_flag, holiday_flag, post_holiday_flag
    
    query = """
        INSERT INTO study_room_feature_log 
        (room_id, record_time, total_seat, used_seat, remain_seat, 
         ema_short, ema_periodic, exam_flag, holiday_flag, post_holiday_flag)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    data_to_insert = []
    
    for _, row in df.iterrows():
        data_to_insert.append((
            row['room_id_str'],      # DB용 문자열 ID (FK)
            row['record_time'],      # 복원된 Timestamp
            int(row['전체좌석']),
            int(row['사용중']),
            int(row['잔여좌석']),
            float(row['EMA_Short']),    # 코랩에서 계산한 값
            float(row['EMA_Periodic']), # 코랩에서 계산한 값
            int(row['Exam_Flag']),
            int(row['Holiday_Flag']),
            int(row['Post_Holiday_Flag'])
        ))

    try:
        cursor.executemany(query, data_to_insert)
        conn.commit()
        print(f"🎉 성공! 총 {len(data_to_insert)}개의 전처리된 데이터가 DB에 저장되었습니다.")
    except Exception as e:
        print(f"❌ 저장 중 오류 발생: {e}")
        print("💡 힌트: 'insert or update on table ... violates foreign key constraint' 에러라면")
        print("   1. init_data.py를 먼저 실행해서 열람실 정보를 생성했는지 확인하세요.")
        print("   2. ID_MAPPING 딕셔너리가 정확한지 확인하세요.")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # 이 파일을 실행하기 전에 반드시 init_data.py를 먼저 실행해야 합니다!
    migrate_features_to_db()