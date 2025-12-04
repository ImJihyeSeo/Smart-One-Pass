# back/services/predict_service.py

import os
import pandas as pd
from datetime import datetime
from prophet.serialize import model_from_json

# 1. 모델 파일들이 있는 경로 설정 (main.py와 같은 위치라고 가정)
# 만약 파일 위치가 다르면 경로를 수정해주세요.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # back 폴더 상위 등 경로 확인 필요
# 혹은 그냥 절대 경로로 지정해도 됩니다.

# 2. 4개 모델 로드 (서버 켜질 때 한 번만 실행됨)
models = {}
room_files = {
    '제1열람실': 'model_room_1.json',
    '제2-1열람실': 'model_room_2_1.json',
    '제2-2열람실': 'model_room_2_2.json',
    '제2-2열람실 (대학원생 전용)': 'model_room_graduate.json'
}

print("🔄 [Prophet] 모델 로딩 시작...")
for room_name, filename in room_files.items():
    # 파일 경로: 현재 폴더 혹은 상위 폴더 등 실제 json 파일 위치에 맞게 조정
    # 예시: main.py랑 같은 위치에 json 파일들이 있다면:
    file_path = os.path.join(os.getcwd(), filename) 
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as fin:
            models[room_name] = model_from_json(fin.read())
        print(f"✅ 모델 로드 완료: {room_name}")
    else:
        print(f"❌ 모델 파일을 찾을 수 없음: {filename}")

# 3. [중요] 각 열람실 총 좌석 수 (Cap 설정용)
# 아까 코드 돌려서 나온 ROOM_CAPACITY 값을 참고해서 정확히 적어주세요.
ROOM_CAPACITY = {
    '제1열람실': 375,
    '제2-1열람실': 270, 
    '제2-2열람실': 136,
    '제2-2열람실 (대학원생 전용)': 62
}

    
def get_status_and_color(used: int, total: int):
    """
    사용 중인 좌석 비율(점유율)에 따른 혼잡도 및 색상 반환
    """
    if total == 0:
        return "에러", "gray" # 0으로 나누기 방지

    
    # 2. 점유율(Usage Ratio) 계산
    usage_ratio = used / total
    
    # 3. 조건 적용 (사용률 기준)
    if usage_ratio < 0.3:           # 사용률 30% 미만 (사람이 거의 없음)
        return "여유", "4caf50"      # Green
    
    elif usage_ratio < 0.7:         # 사용률 30% 이상 ~ 70% 미만 (적당함)
        return "보통", "ff9800"      # Orange
        
    else:                           # 사용률 70% 이상 (꽉 참)
        return "혼잡", "f44336"      # Red


def predict_library_seats(target_dt: datetime):
    """
    Prophet 모델을 사용하여 4개 열람실의 잔여석을 예측하고, 터미널에 로그를 출력합니다.
    """
    results = []

    # 예측용 DataFrame 생성
    future = pd.DataFrame({'ds': [target_dt]})
    
    # 터미널 출력용 헤더 (구분선)
    print(f"\n🔮 [예측 요청] 타겟 시간: {target_dt}")
    print("-" * 50)

    for room_name, model in models.items():
        try:
            # 1. Cap(상한선) 설정
            current_cap = ROOM_CAPACITY.get(room_name, 100)
            future['cap'] = current_cap
            future['floor'] = 0
            
            # 2. 예측 수행
            forecast = model.predict(future)

            # 3. 결과 추출 (모델은 '사용 중인 좌석'을 예측함)
            pred_used_float = forecast.iloc[0]['yhat']
            
            # 4. ★ [수정 2] 잔여좌석 계산 (전체 - 사용중)
            # 사용 중인 좌석을 정수로 반환
            pred_used = int(round(pred_used_float))
            
            # 범위 보정 (사용 좌석이 0보다 작거나 전체보다 클 수 없음)
            if pred_used < 0: pred_used = 0
            if pred_used > current_cap: pred_used = current_cap

            status, color = get_status_and_color(pred_used, current_cap)

            # 잔여석 계산
            pred_remain = current_cap - pred_used

            # # 5. 혼잡도 라벨링
            # status, color = get_status_and_color(pred_remain, current_cap)
            
            # ✅ [추가된 부분] 터미널에 예측값 출력
            print(f"🏫 {room_name.ljust(15)} | 잔여: {str(pred_remain).rjust(3)}석 / {current_cap}석 | 상태: {status}")

            # 6. 결과 리스트 추가
            results.append({
                "name": room_name,
                "total": str(current_cap),
                "remain": str(pred_remain),
                "status": status,
                "color": color
            })
            
        except Exception as e:
            print(f"❌ 예측 에러 ({room_name}): {str(e)}")
            results.append({
                "name": room_name,
                "total": str(ROOM_CAPACITY.get(room_name, 0)),
                "remain": "Error",
                "status": "알수없음",
                "color": "#9e9e9e"
            })
            
    print("-" * 50 + "\n") # 하단 구분선
    return results