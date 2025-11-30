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

def get_status_and_color(remain: int, total: int):
    """
    잔여석 비율에 따른 혼잡도 및 색상 반환
    """
    if total == 0: return "만석", "#9e9e9e"
    
    ratio = remain / total
    if remain <= 0:
        return "만석", "#9e9e9e" # 회색
    elif ratio >= 0.5:
        return "여유", "#4caf50" # 초록
    elif ratio >= 0.2:
        return "보통", "#ff9800" # 주황
    else:
        return "혼잡", "#f44336" # 빨강

# def predict_library_seats(target_dt: datetime):
#     """
#     Prophet 모델을 사용하여 4개 열람실의 잔여석을 예측
#     """
#     results = []

#     # 예측용 DataFrame 생성 (Prophet은 ds, cap 컬럼이 필요함)
#     future = pd.DataFrame({'ds': [target_dt]})
    
#     for room_name, model in models.items():
#         try:
#             # 1. Cap(상한선) 설정 (Logistic Growth 학습 시 필수)
#             current_cap = ROOM_CAPACITY.get(room_name, 100)
#             future['cap'] = current_cap
#             future['floor'] = 0
            
#             # 2. 예측 수행
#             forecast = model.predict(future)
            
#             # 3. 결과 추출 (yhat이 예측값)
#             pred_float = forecast.iloc[0]['yhat']
            
#             # 4. 정수 변환 및 범위 보정 (0 ~ Max 사이로 가두기)
#             pred_remain = int(round(pred_float))
#             if pred_remain < 0: pred_remain = 0
#             if pred_remain > current_cap: pred_remain = current_cap
            
#             # 5. 혼잡도 라벨링
#             status, color = get_status_and_color(pred_remain, current_cap)
            
#             # 6. 결과 리스트 추가
#             results.append({
#                 "name": room_name,         # 열람실명 -> name
#                 "total": str(current_cap), # 전체좌석 -> total
#                 "remain": str(pred_remain),# 예측잔여석 -> remain
#                 "status": status,          # 혼잡도 -> status
#                 "color": color             # 색상 -> color
#             })
            
#         except Exception as e:
#             print(f"❌ 예측 에러 ({room_name}): {str(e)}")
#             # 에러 시 기본값 반환
#             results.append({
#                 "name": room_name,
#                 "total": str(ROOM_CAPACITY.get(room_name, 0)),
#                 "remain": "Error",
#                 "status": "알수없음",
#                 "color": "#9e9e9e"
#             })

#     return results


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
            
            # 3. 결과 추출
            pred_float = forecast.iloc[0]['yhat']
            
            # 4. 정수 변환 및 범위 보정
            pred_remain = int(round(pred_float))
            if pred_remain < 0: pred_remain = 0
            if pred_remain > current_cap: pred_remain = current_cap
            
            # 5. 혼잡도 라벨링
            status, color = get_status_and_color(pred_remain, current_cap)
            
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