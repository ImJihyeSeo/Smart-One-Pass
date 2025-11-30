# back/services/predict_service.py

import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from database import get_db_connection

# 모델 파일 경로 (main.py 옆에 있다고 가정)
MODEL_PATH = "final_library_model.pkl"
try:
    model = joblib.load(MODEL_PATH)
    print("✅ [Service] 예측 모델 로드 완료")
except:
    print("❌ [Service] 모델 파일을 찾을 수 없습니다.")
    model = None

def get_status_and_color(remain: int, total: int):
    """
    ★ 프론트엔드 디자인 규칙을 여기서 정의합니다 ★
    잔여석 비율에 따라 텍스트와 색상 코드를 반환합니다.
    """
    if total == 0: return "만석", "#9e9e9e" # 회색
    
    ratio = remain / total
    
    if remain <= 0:
        return "만석", "#9e9e9e" # 회색
    elif ratio >= 0.5:
        return "여유", "#00c853" # 초록색
    elif ratio >= 0.2:
        return "보통", "#ff9100" # 주황색
    else:
        return "혼잡", "#ff3d00" # 빨간색

def predict_library_seats(target_dt: datetime):
    """
    특정 시간(target_dt)에 대한 모든 열람실의 상태를 예측합니다.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 예측 대상 열람실 정의 (DB의 study_room 테이블에서 가져와도 됨)
    room_list = [
        {"id": "제1열람실", "total": 375},
        {"id": "제2-1열람실", "total": 270},
        {"id": "제2-2열람실", "total": 136},
        {"id": "제2-2열람실 (대학원생 전용)", "total": 62}
    ]
    
    results = []

    for room in room_list:
        room_id = room['id']
        total = room['total']

        # 2. DB에서 가장 최신 EMA 값 조회 (Feature Log 테이블)
        cursor.execute("""
            SELECT ema_short, ema_periodic 
            FROM study_room_feature_log 
            WHERE room_id = %s 
            ORDER BY record_time DESC 
            LIMIT 1
        """, (room_id,))
        
        last_log = cursor.fetchone()
        ema_short = last_log['ema_short'] if last_log else 0.0
        ema_periodic = last_log['ema_periodic'] if last_log else 0.0

        # ==========================================================
        # [수정] 시험 기간 여부 자동 판단 로직 추가
        # ==========================================================
        
        # 예측하려는 날짜(target_dt)의 연도, 날짜만 추출
        target_date = target_dt.date() 
        current_year = target_dt.year

        # 시험 기간 설정: 11월 17일 ~ 12월 7일
        exam_start = datetime(current_year, 11, 17).date()
        exam_end = datetime(current_year, 12, 7).date()

        # 해당 날짜가 범위 내에 있으면 1, 아니면 0
        is_exam_period = 1 if exam_start <= target_date <= exam_end else 0
        
        # ==========================================================
        # 3. 모델 입력 데이터 생성
        # (학습 때 사용한 피처 순서와 구성을 맞춰야 함)
        input_data = {
            '전체좌석': [total],
            '년': [target_dt.year],
            '월': [target_dt.month],
            '일': [target_dt.day],
            '시간': [target_dt.hour],
            '요일코드': [target_dt.weekday()],
            'Exam_Flag': [is_exam_period],
            'Holiday_Flag': [0],
            'Post_Holiday_Flag': [0],
            'EMA_Periodic': [ema_periodic],
            'EMA_Short': [ema_short],
            
            # One-Hot Encoding 처리 (수동)
            '열람실 ID_제2-1열람실': [1 if room_id == "제2-1열람실" else 0],
            '열람실 ID_제2-2열람실': [1 if room_id == "제2-2열람실" else 0],
            '열람실 ID_제2-2열람실 (대학원생 전용)': [1 if room_id == "제2-2열람실 (대학원생 전용)" else 0]
            # 제1열람실은 학습 시 drop_first=True로 제거되었을 가능성이 큼 (확인 필요)
        }
        
        # 4. 예측 수행
        try:
            df_input = pd.DataFrame(input_data)
            
            # 모델의 feature_names_in_ 을 이용해 컬럼 순서 강제 정렬 (에러 방지)
            if hasattr(model, 'feature_names_in_'):
                 df_input = df_input.reindex(columns=model.feature_names_in_, fill_value=0)

            pred_remain = int(model.predict(df_input)[0])
        except Exception as e:
            print(f"⚠️ 예측 실패 ({room_id}): {e}")
            pred_remain = 0 # 에러 시 보수적으로 0 처리

        # 5. 프론트엔드용 데이터 가공 (★ 핵심 ★)
        status, color = get_status_and_color(pred_remain, total)

        results.append({
            "name": room_id,
            "status": status,  # 예: "여유"
            "color": color,    # 예: "#00c853"
            "seats": f"{pred_remain}/{total}" # 상세 숫자 (선택 사항)
        })

    conn.close()
    return results