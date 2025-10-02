# 설정 상수

# 메시지 영역의 고정 높이 (픽셀)
MESSAGE_AREA_HEIGHT = 100

# 최대 재시도 횟수
TOTAL_ATTEMPTS = 3

# 웹캠 영상 크기 (ReadyPage, ProcessingPage 공통)
TARGET_W, TARGET_H = 300, 450

# 둥근 모서리 반경
BORDER_RADIUS = 20

# 웹캠 화면 위치 조정 위한 상단 간격
TOP_SPACING = 30

# 얼굴 인식 유지 시간 (초)
PROCESSING_DURATION = 3.0 

# 버튼
BUTTON_STYLE = """
    QPushButton {
        background-color: #005BAC; 
        color: white; 
        border-radius: 8px; 
        padding: 8px 5px; 
        font-size: 16px; 
        font-weight: bold;
        min-height: 20px;
    }
    QPushButton:hover {
        background-color: #5F5F5F;
    }
"""