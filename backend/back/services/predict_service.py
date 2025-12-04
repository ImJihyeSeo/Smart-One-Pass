import os
import pandas as pd
from datetime import datetime
from prophet.serialize import model_from_json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

models = {}
room_files = {
    '제1열람실': 'model_room_1.json',
    '제2-1열람실': 'model_room_2_1.json',
    '제2-2열람실': 'model_room_2_2.json',
    '제2-2열람실 (대학원생 전용)': 'model_room_graduate.json'
}

print("[Prophet] 모델 로딩 시작...")
for room_name, filename in room_files.items():
    file_path = os.path.join(os.getcwd(), filename) 
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as fin:
            models[room_name] = model_from_json(fin.read())
        print(f"✅ 모델 로드 완료: {room_name}")
    else:
        print(f"❌ 모델 파일을 찾을 수 없음: {filename}")

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
        return "에러", "gray"

    
    usage_ratio = used / total
    
    if usage_ratio < 0.3: # 사용률 30% 미만
        return "여유", "4caf50"      
    
    elif usage_ratio < 0.7: # 사용률 30% 이상 ~ 70% 미만
        return "보통", "ff9800"      
        
    else: # 사용률 70% 이상
        return "혼잡", "f44336"      


def predict_library_seats(target_dt: datetime):
    """
    Prophet 모델을 사용하여 4개 열람실의 잔여석을 예측하고, 터미널에 로그를 출력합니다.
    """
    results = []

    future = pd.DataFrame({'ds': [target_dt]})
    
    print(f"\n[예측 요청] 타겟 시간: {target_dt}")
    print("-" * 50)

    for room_name, model in models.items():
        try:
            current_cap = ROOM_CAPACITY.get(room_name, 100)
            future['cap'] = current_cap
            future['floor'] = 0
            
            forecast = model.predict(future)

            pred_used_float = forecast.iloc[0]['yhat']
            
            pred_used = int(round(pred_used_float))
            
            if pred_used < 0: pred_used = 0
            if pred_used > current_cap: pred_used = current_cap

            status, color = get_status_and_color(pred_used, current_cap)

            pred_remain = current_cap - pred_used
            
            print(f"{room_name.ljust(15)} | 잔여: {str(pred_remain).rjust(3)}석 / {current_cap}석 | 상태: {status}")

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
            
    print("-" * 50 + "\n")
    return results