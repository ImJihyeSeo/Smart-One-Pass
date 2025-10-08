from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from config import ALERT_STYLE

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
