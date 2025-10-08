from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer

# 설정 상수

# 메시지 영역의 고정 높이 (픽셀)
MESSAGE_AREA_HEIGHT = 100

# 최대 재시도 횟수
TOTAL_ATTEMPTS = 3

# 웹캠 영상 크기 (ReadyPage, ProcessingPage 공통)
TARGET_W, TARGET_H = 270, 400

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
        min-width: 100px;
    }
    QPushButton:hover {
        background-color: #5F5F5F;
    }
"""

# 입력 필드 스타일
INPUT_STYLE = """
    QLineEdit {
        background-color: rgba(255, 255, 255, 0.4);
        color: #ffffff; 
        border: 2px solid #ffffff; 
        border-radius: 20px; 
        padding: 6px 12px; 
        font-size: 15px; 
        min-height: 25px; 
    }
"""

# 경고창 스타일
ALERT_STYLE = f"""
    QDialog {{
        background-color: #1e1e1e;
        border-radius: 30px;
    }}
    QLabel {{
        color: white;
        font-size: 15px;
        font-weight: medium;
        background: transparent;
    }}
    QPushButton {{
        background-color: #005BAC;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: #5F5F5F;
    }}
"""

# 경고창 팝업
class CustomAlertDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)

        self.setStyleSheet(ALERT_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)

        label = QLabel(message)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        button_box = QHBoxLayout()
        button_box.addStretch()

        ok_button = QPushButton("확인")
        ok_button.clicked.connect(self.accept)
        button_box.addWidget(ok_button)

        button_box.addStretch()
        layout.addLayout(button_box)

# 지정된 위젯에 페이드 인 → 유지 → 페이드 아웃 애니메이션 적용
def fade_in_out(widget, duration_in=300, duration_out=500, visible_ms=2000, finished_callback=None):
    # 투명도 효과(effect) 확보 / 초기화
    try:
        effect = widget.graphicsEffect()
        if effect is None:
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        
        # 애니메이션 시작점 - 투명도 초기화 및 위젯 표시
        effect.setOpacity(0.0)
        widget.show()
    except RuntimeError:
        return

    # 페이드 인 애니메이션
    try:
        fade_in = QPropertyAnimation(effect, b"opacity")
        fade_in.setDuration(duration_in)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.InOutQuad)
        
        # GC 방지를 위해 애니메이션 객체를 위젯 속성에 저장
        widget._fade_in_anim = fade_in 
        
        # 페이드 아웃 예약 및 연결
        fade_in.finished.connect(lambda: QTimer.singleShot(visible_ms, start_fade_out))
        fade_in.start()

    except RuntimeError:
        return

    # 페이드 아웃 애니메이션 함수
    def start_fade_out():
        try:
            # effect 유효성 확인
            if effect.parent() is None and widget.graphicsEffect() is None:
                 return

            fade_out = QPropertyAnimation(effect, b"opacity")
            fade_out.setDuration(duration_out)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setEasingCurve(QEasingCurve.InOutQuad)
            fade_out.finished.connect(widget.hide)  # 애니메이션 완료 후 위젯 숨김

            if finished_callback:
                fade_out.finished.connect(finished_callback)
                 
            # GC 방지를 위해 애니메이션 객체를 위젯 속성에 저장
            widget._fade_out_anim = fade_out
            fade_out.start()
            
        except RuntimeError:
            return
