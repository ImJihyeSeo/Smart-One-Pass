from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget,
    QGraphicsOpacityEffect, QGraphicsBlurEffect, QGraphicsDropShadowEffect,
    QCalendarWidget, QFrame
) 
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, QByteArray, QDate, 
    Signal, QSize
)
from PySide6.QtGui import QColor, QPainter, QPixmap, QMouseEvent

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
        background-color: #3B6EEB;
        color: white; 
        border-radius: 20px;
        padding: 12px 25px;
        font-size: 16px; 
        font-weight: bold;
        min-height: 20px;
        min-width: 100px;
    }
    QPushButton:hover {
        background-color: #5F5F5F;
    }
"""

# 아이콘 버튼
ICON_BUTTON_STYLE = """
    QPushButton {
        background: transparent;
        color: #ffffff;
        border: none;
        font-size: 14px;
        padding: 5px;
    }
    QPushButton:hover {
        color: #007bff;
    }
"""

# 기본 라벨 스타일
LABEL_STYLE = "color: #ffffff; font-size: 14px; margin: 0px; padding: 8px;"
# 메인 안내 메시지
TITLE_STYLE = "font-size: 24px; color: #ffffff; margin-bottom: 5px;"
# 서브 안내 메시지
GUIDE_STYLE = "font-size: 14px; color: #ffffff;"

# 입력 필드 스타일
INPUT_STYLE = """
    QLineEdit {
        background-color: #333333;
        color: #ffffff;
        border: none;
        border-radius: 18px;
        padding: 10px;
        font-size: 12px;
    }
    QLineEdit:focus {
        border: 1px solid #4A90E2;
    }
"""

# 메인 화면 스타일
IDLE_PAGE_STYLE = """
#IdlePage {
    background-color: #1a1a1a;
    color: #ffffff;
    border-radius: 20px;
}
QLabel {
    background: transparent;
    color: #ffffff;
}
"""

# 메인 화면 버튼 스타일
class ImageButtonWidget(QLabel):
    clicked = Signal()

    def __init__(self, image_path, size, parent=None):
        super().__init__(parent)
        self.setFixedSize(size)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)

        # 이미지 로드
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.setPixmap(pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.setText(f"{image_path} Missing")
            self.setStyleSheet("color: red; font-size: 14px;")
            
        self.original_style = "QLabel { background: transparent; }"
        self.setStyleSheet(self.original_style)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


# 팝업창 띄울 때 부모 창 위 덮는 오버레이 클래스
class OverlayWidget(QWidget):
    def __init__(self, parent=None, color=QColor(0, 0, 0, 230)):
        super().__init__(parent.window() if parent else None)
        self.parent_widget = parent
        self.color = color

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("border: none;")

        self._align_to_parent()

        # 페이드 인 애니메이션
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(200)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    # 오버레이 위치 정확히 맞추기 위한 함수
    def _align_to_parent(self):
        if not self.parent_widget:
            return
        geo = self.parent_widget.window().frameGeometry()
        self.setGeometry(geo)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.color)

    def fade_out_and_close(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.windowOpacity())
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.close)
        self.anim.start()

    # 화면 바뀔 때 자동 재정렬
    def showEvent(self, event):
        self._align_to_parent()
        super().showEvent(event)

# 경고 팝업창
class CustomAlertDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.overlay = None

        # 오버레이 생성
        if parent:
            self.overlay = OverlayWidget(parent)
            self.overlay.show()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)  # 투명 배경 허용

        # 팝업 스타일
        self.setStyleSheet("""
            QDialog { background: transparent; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 메인 위젯
        self.bg_widget = QLabel()
        self.bg_widget.setObjectName("glass")
        self.bg_widget.setFixedWidth(400)
        self.bg_widget.setStyleSheet("""
            QLabel#glass {
                background-color: rgba(255, 255, 255, 0.15);    /* 유리 같은 반투명 효과 */
                border-radius: 25px;
                border: 1px solid rgba(255,255,255,0.3);
            }
        """)
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(20)
        self.bg_widget.setGraphicsEffect(blur)

        # 그림자
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.setGraphicsEffect(shadow)

        # 내부 레이아웃
        inner_layout = QVBoxLayout(self.bg_widget)
        inner_layout.setContentsMargins(25, 20, 25, 20)
        inner_layout.setSpacing(15)

        # 메시지 분리 - title / body / footer
        # 딕셔너리 형태로 전달받으면 분리, 아니면 단일 메시지 처리
        if isinstance(message, dict) and 'title' in message:
            dialog_title = message.get('title', '')
            dialog_body = message.get('body', '')
            dialog_footer = message.get('footer', '')
        else:
            dialog_title = ""
            dialog_body = message
            dialog_footer = ""


        # 1. 상단 - title
        if dialog_title:
            title_label = QLabel(dialog_title)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("color: white; font-size: 16px; margin-bottom: 5px;")
            inner_layout.addWidget(title_label)
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setStyleSheet("color: rgba(255, 255, 255, 0.4);")
            inner_layout.addWidget(line)


        # 2. 중앙 - body
        label = QLabel(dialog_body)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: white; font-size: 14px; font-weight: 500;")
        inner_layout.addWidget(label)
        
        # 3. 하단 - footer
        if dialog_footer:
            inner_layout.addSpacing(5)
            footer_label = QLabel(dialog_footer)
            footer_label.setWordWrap(True)
            footer_label.setAlignment(Qt.AlignCenter)
            footer_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
            inner_layout.addWidget(footer_label)

        # 버튼
        button_box = QHBoxLayout()
        button_box.addStretch()
        ok_button = QPushButton("확인")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.25);
                border: 1px solid rgba(255,255,255,0.4);
                color: white;
                border-radius: 12px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.35);
            }
            QPushButton:pressed {
                background-color: rgba(255,255,255,0.5);
            }
        """)
        ok_button.clicked.connect(self.accept)
        button_box.addWidget(ok_button)
        button_box.addStretch()
        inner_layout.addLayout(button_box)

        layout.addWidget(self.bg_widget)

        # 팝업 창 투명도 초기화
        self.setWindowOpacity(0.0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)

    # 중앙 정렬 + 페이드 인
    def showEvent(self, event):
        super().showEvent(event)

        # 중앙 위치 계산
        if self.parent():
            parent_geo = self.parent().window().frameGeometry()
            center = parent_geo.center()
            self.adjustSize()
            self.move(center.x() - self.width() // 2,
                      center.y() - self.height() // 2)

        # 페이드 인 시작
        self.fade_anim.start()

    def accept(self):
        if self.overlay:
            self.overlay.fade_out_and_close()
        super().accept()


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


def blinking_effect(widget: QWidget, duration: int = 2000):
    # Opacity effect
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    # Animation 생성
    anim = QPropertyAnimation(effect, QByteArray(b"opacity"))
    anim.setDuration(duration)
    anim.setStartValue(0.4)
    anim.setEndValue(0.9)
    anim.setEasingCurve(QEasingCurve.InOutQuad)
    anim.setLoopCount(-1)
    anim.setDirection(QPropertyAnimation.Forward)
    anim.start()
    
    # GC 방지
    widget._blink_anim = anim

    return effect, anim


# 달력 팝업창
class DateSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 오버레이 생성 및 표시
        self.overlay = None
        if parent:
            self.overlay = OverlayWidget(parent)
            self.overlay.show()
            
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(220, 280)

        # 그림자 효과
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 배경 위젯
        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("glass_frame")
        self.bg_frame.setStyleSheet("""
            QFrame#glass_frame {
                background-color: rgba(255, 255, 255, 0.15);
                border-radius: 25px;
                border: 1px solid rgba(255,255,255,0.3);
            }
        """)
        # 블러 효과
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(15)
        self.bg_frame.setGraphicsEffect(blur)
        
        # 내부 콘텐츠 레이아웃
        inner_layout = QVBoxLayout(self.bg_frame)
        inner_layout.setContentsMargins(20, 20, 20, 20)
        
        # 달력 위젯 스타일
        calendar_style = """
            QCalendarWidget { 
                alternate-background-color: #3a3a3a;
                color: #ffffff;
                font-size: 14px;
                border-radius: 10px;
                padding: 5px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar { 
                background-color: #2e2e2e; 
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QCalendarWidget QToolButton { 
                color: #ffffff; 
                icon-size: 20px;
            }
            /* 오늘 날짜 */
            QCalendarWidget QAbstractItemView:!enabled {
                color: #aaaaaa;
            }
            /* 선택 가능한 날짜 */
            QCalendarWidget QAbstractItemView:enabled {
                color: #ffffff;
            }
            /* 선택된 날짜 */
            QCalendarWidget QAbstractItemView::item:selected {
                background-color: #007bff; /* 파란색 배경으로 강조 */
                color: #ffffff;
                border-radius: 5px;
            }
            /* 마우스 오버 시 */
            QCalendarWidget QAbstractItemView::item:hover {
                background-color: #4a4a4a;
                border-radius: 5px;
            }
        """

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setMinimumDate(QDate.currentDate())
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader) 
        self.calendar.setStyleSheet(calendar_style)
        
        inner_layout.addWidget(self.calendar)
        
        # 확인 버튼
        confirm_btn = QPushButton("선택")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.25);
                border: 1px solid rgba(255,255,255,0.4);
                color: white;
                border-radius: 12px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.35);
            }
            QPushButton:pressed {
                background-color: rgba(255,255,255,0.5);
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        inner_layout.addWidget(confirm_btn)
        
        main_layout.addWidget(self.bg_frame)
        
        # 팝업 창 투명도 초기화 및 애니메이션 설정
        self.setWindowOpacity(0.0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)


    def showEvent(self, event):
        super().showEvent(event)
        
        # 중앙 위치 계산 및 이동
        if self.parent():
            parent_geo = self.parent().window().frameGeometry()
            center = parent_geo.center()
            self.adjustSize()
            self.move(center.x() - self.width() // 2,
                      center.y() - self.height() // 2)

        # 페이드 인 시작
        self.fade_anim.start()

    def accept(self):
        # 팝업 닫을 때 오버레이도 닫기
        if self.overlay:
            self.overlay.fade_out_and_close()
        super().accept()
        
    def get_selected_date(self):
        """ 선택된 날짜 반환 """
        date = self.calendar.selectedDate()
        display_str = date.toString("MM월 dd일 (ddd)")
        return date.toString("yyyy-MM-dd"), display_str