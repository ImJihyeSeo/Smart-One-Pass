from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget,
    QGraphicsOpacityEffect, QGraphicsBlurEffect, QGraphicsDropShadowEffect,
    QCalendarWidget, QSizePolicy, QGridLayout, QSpacerItem, QFrame
) 
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, QByteArray, QDate, 
    Signal, QSize, QLocale
)
from PySide6.QtGui import QColor, QPainter, QPixmap, QMouseEvent

KOREAN_LOCALE = QLocale(QLocale.Korean, QLocale.SouthKorea)

# 타겟 해상도
TARGET_W_MAIN = 800
TARGET_H_MAIN = 1280

# 메시지 영역 고정 높이
MESSAGE_AREA_HEIGHT_REF = 100
MESSAGE_AREA_HEIGHT = 160

# 최대 재시도 횟수
TOTAL_ATTEMPTS = 3

# 웹캠 영상 크기 (ReadyPage, ProcessingPage 공통)
TARGET_W, TARGET_H = 500, 770

# 둥근 모서리 반경
BORDER_RADIUS_REF = 20
BORDER_RADIUS = 30

# 웹캠 화면 위치 조정 위한 상단 간격
TOP_SPACING_REF = 30
TOP_SPACING = 50

# 얼굴 인식 유지 시간 (초)
PROCESSING_DURATION = 3.0 

# 버튼
BUTTON_STYLE = """
    QPushButton {
        background-color: #3B6EEB;
        color: white; 
        border-radius: 30px;
        padding: 15px 25px;
        font-size: 28px; 
        font-weight: bold;
        min-height: 30px;
        min-width: 100px;
    }
    QPushButton:hover {
        background-color: #4A79F0;
    }
"""

# 취소 버튼
CANCEL_BUTTON_STYLE = """
    QPushButton {
        background-color: #7f7f7f;
        color: white; 
        border-radius: 30px;
        padding: 15px 25px;
        font-size: 28px; 
        font-weight: bold;
        min-height: 30px;
        min-width: 100px;
    }
    QPushButton:hover {
        background-color: #9f9f9f;
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
LABEL_STYLE = "color: #ffffff; font-size: 24px; margin: 0px; padding: 8px;"
# 메인 안내 메시지
TITLE_STYLE = "font-size: 42px; color: #ffffff; margin-bottom: 5px;"
# 서브 안내 메시지
GUIDE_STYLE = "font-size: 30px; color: #ffffff;"

# 입력 필드 스타일
INPUT_STYLE = """
    QLineEdit {
        background-color: #404040;
        color: #ffffff;
        border: none;
        border-radius: 25px;
        padding: 10px;
        font-size: 24px;
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
    def __init__(self, message, parent=None, buttons=None, width=None):
        super().__init__(parent)
        self.overlay = None
        
        # 기본 버튼 - 확인
        if buttons is None:
            buttons = [{'text': '확인', 'style': 'confirm', 'callback': self.accept}]
        self.button_configs = buttons

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
        
        # 너비: width 값 지정 -> 사용 / 미지정 -> 기본값 400px
        final_width = width if width is not None else 400 
        self.bg_widget.setFixedWidth(final_width) 
        
        self.bg_widget.setStyleSheet("""
            QLabel#glass {
                background-color: rgba(255, 255, 255, 0.15);    /* 유리 같은 반투명 효과 */
                border-radius: 25px;
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
        inner_layout.setContentsMargins(40, 50, 40, 50)
        inner_layout.setSpacing(20) 

        # 메시지 분리 - title / body / footer
        if isinstance(message, dict) and 'title' in message:
            dialog_title = message.get('title', '')
            dialog_body = message.get('body', '')
            dialog_footer = message.get('footer', '')
            body_font_size = message.get('body_font_size', 26)
        else:
            dialog_title = ""
            dialog_body = message
            dialog_footer = ""
            body_font_size = 26


        # 1. 상단 - title
        if dialog_title:
            title_label = QLabel(dialog_title)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("color: white; font-size: 32px; background-color: transparent;")
            inner_layout.addWidget(title_label)
            inner_layout.addSpacing(20)

        # 2. 중앙 - body
        label = QLabel(dialog_body)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet(f"color: white; font-size: {body_font_size}px; font-weight: 500; background: transparent;")
        inner_layout.addWidget(label)
        
        # 3. 하단 - footer
        if dialog_footer:
            inner_layout.addSpacing(5)
            footer_label = QLabel(dialog_footer)
            footer_label.setWordWrap(True)
            footer_label.setAlignment(Qt.AlignCenter)
            footer_label.setStyleSheet("background: transparent; font-size: 22px;")
            inner_layout.addWidget(footer_label)

        # 버튼
        button_box = QHBoxLayout()
        button_box.addStretch()
        
        for config in self.button_configs:
            btn = QPushButton(config['text'])
            
            if config['style'] == 'cancel':
                btn.setStyleSheet(self._get_cancel_button_style())
            elif config['style'] == 'confirm':
                btn.setStyleSheet(self._get_confirm_button_style())
            else:
                btn.setStyleSheet(self._get_default_button_style())

            btn.clicked.connect(self._create_button_action(config.get('callback')))
            
            button_box.addWidget(btn)

        button_box.addStretch()
        
        inner_layout.addSpacing(20)
        inner_layout.addLayout(button_box)
        layout.addWidget(self.bg_widget)

        # 팝업 창 투명도 초기화
        self.setWindowOpacity(0.0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self._fade_anim = self.fade_anim # GC 방지
        
    # ----------------------------------------------------------------------
    # 버튼 스타일
    # ----------------------------------------------------------------------

    # 기본 버튼
    def _get_default_button_style(self):
        return """
            QPushButton {
                background-color: rgba(255,255,255,0.25);
                color: white;
                border-radius: 12px;
                padding: 5px 5px;
                font-size: 14px;
                font-weight: bold;
                min-width: 40px;
                margin: 0px 5px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.35);
            }
        """
    
    # 취소/닫기 버튼
    def _get_cancel_button_style(self):
        return """
            QPushButton {
                background-color: rgba(160,160,160,0.4);
                color: white;
                border-radius: 20px;
                padding: 12px 15px;
                font-size: 26px;
                font-weight: bold;
                min-width: 90px;
                margin: 0px 5px;
            }
            QPushButton:hover {
                background-color: rgba(159,159,159,0.5);
            }
        """

    # 확인 버튼
    def _get_confirm_button_style(self):
        return """
            QPushButton {
                background-color: #3B6EEB;
                color: white;
                border-radius: 20px;
                padding: 10px 12px;
                font-size: 26px;
                font-weight: bold;
                min-width: 90px;
                margin: 0px 5px;
            }
            QPushButton:hover {
                background-color: #4A79F0;
            }
        """

    # 버튼 클릭 -> 팝업 닫고 콜백 실행
    def _create_button_action(self, callback):
        def action():
            self.close_popup()
            if callback:
                callback() 
        return action

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

    # 팝업/오버레이 닫기
    def close_popup(self):
        if self.overlay:
            self.overlay.fade_out_and_close()
        super().close()

    # 오버라이드
    def accept(self):
        self.done(QDialog.Accepted)
        self.close_popup()
    
    # 오버라이드
    def reject(self):
        self.done(QDialog.Rejected)
        self.close_popup()


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
    def __init__(self, initial_date, parent=None):
        super().__init__(parent)

        self.current_date = initial_date 
        self.selected_date = initial_date
        self.highlighted_button = None 
        
        self.setWindowTitle("달력")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(550, 600)
        
        self.main_frame = QFrame(self)
        self.main_frame.setFixedSize(self.size()) 
        self.main_frame.setObjectName("CalendarFrame") 

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(self.main_frame)
        
        main_layout = QVBoxLayout(self.main_frame)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.header_label = QLabel()
        self.calendar_grid = QGridLayout()
        
        self._setup_header_layout(main_layout)
        self._setup_calendar_grid(main_layout)
        
        self._apply_style()
        
        self._update_calendar(self.current_date)

    # --------------------------------------------------------------------------
    # 스타일 / UI
    # --------------------------------------------------------------------------

    def _get_default_base_style(self):
        return """
            QPushButton {
                color: #FFFFFF;
                background: transparent;
                border: none;
                font-size: 24px;
                border-radius: 30px;
                min-width: 60px;
                max-width: 60px;
                min-height: 60px;
                max-height: 60px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """
        
    def _get_highlight_style(self):
        """ 선택된 날짜 버튼 """
        return """
            QPushButton {
                color: #FFFFFF;
                background-color: #3B6EEB;
                border: none;
                font-size: 24px;
                border-radius: 30px;
                min-width: 60px;
                max-width: 60px;
                min-height: 60px;
                max-height: 60px;
            }
        """

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background: transparent; 
            }
            
            QFrame#CalendarFrame {
                background-color: #1A1A1A;
                border: 2px solid #505050;
                border-radius: 30px;
            }
            
            QLabel {
                color: #FFFFFF;
                background: transparent;
            }
        """)

    def _setup_header_layout(self, parent_layout):
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        
        self.prev_month_btn = QPushButton("<")
        self.prev_month_btn.setFixedWidth(80)
        self.prev_month_btn.clicked.connect(self._prev_month)
        
        self.header_label.setAlignment(Qt.AlignCenter)
        self.header_label.setStyleSheet("font-size: 30px; font-weight: bold; padding: 10px 0;")

        self.next_month_btn = QPushButton(">")
        self.next_month_btn.setFixedWidth(80)
        self.next_month_btn.clicked.connect(self._next_month)
        
        arrow_style = """
            QPushButton {
                color: #FFFFFF;
                background: transparent;
                border: none;
                font-size: 32px;
            }
            QPushButton:hover {
                color: #3B6EEB;
            }
        """
        self.prev_month_btn.setStyleSheet(arrow_style)
        self.next_month_btn.setStyleSheet(arrow_style)
        
        header_layout.addWidget(self.prev_month_btn)
        header_layout.addWidget(self.header_label)
        header_layout.addWidget(self.next_month_btn)
        
        parent_layout.addWidget(header_widget)

    def _setup_calendar_grid(self, parent_layout):
        
        days = ["S", "M", "T", "W", "T", "F", "S"]
        day_style = "font-size: 28px; font-weight: bold; color: #3B6EEB;"
        for i, day in enumerate(days):
            day_label = QLabel(day)
            day_label.setAlignment(Qt.AlignCenter)
            day_label.setStyleSheet(day_style)
            self.calendar_grid.addWidget(day_label, 0, i)
        
        parent_layout.addLayout(self.calendar_grid)
        parent_layout.addItem(QSpacerItem(0, 5, QSizePolicy.Minimum, QSizePolicy.Expanding))

    # --------------------------------------------------------------------------
    # 날짜 로직
    # --------------------------------------------------------------------------

    def _update_calendar(self, date):
        """ 현재 월 기준으로 달력 업데이트 """
        
        # 기존 날짜 버튼 제거
        for i in reversed(range(self.calendar_grid.count())): 
            item = self.calendar_grid.itemAt(i) 
            position = self.calendar_grid.getItemPosition(i)

            if position[0] > 0 and item.widget() is not None:
                item.widget().deleteLater()
        
        self.highlighted_button = None

        try:
            month_name = KOREAN_LOCALE.toString(date, "MMM") 
        except NameError:
            month_name = date.toString("MMM") 
            
        self.header_label.setText(f"{month_name}")

        first_day_of_month = QDate(date.year(), date.month(), 1)
        day_of_week = first_day_of_month.dayOfWeek() % 7 

        # 달력 시작 날짜 (이전 달 마지막 주)
        current_day = first_day_of_month.addDays(-day_of_week)
        
        row = 1 
        for _ in range(42):
            if row > 6: break

            col = current_day.dayOfWeek() % 7 
            
            date_button = QPushButton(str(current_day.day()))
            date_button.setProperty("date", current_day.toString("yyyy-MM-dd"))
            date_button.clicked.connect(self._date_clicked)

            self._style_date_button(date_button, current_day, date)
            
            self.calendar_grid.addWidget(date_button, row, col)
            
            if col == 6:
                row += 1
                
            current_day = current_day.addDays(1)

    def _style_date_button(self, button, date_to_style, current_month_date):
        """ 날짜 버튼 """
        is_in_current_month = date_to_style.month() == current_month_date.month()
        is_selected = date_to_style == self.selected_date
        
        if not is_in_current_month:
            gray_style = self._get_default_base_style().replace("#FFFFFF", "#777777")
            button.setStyleSheet(gray_style)
            button.setEnabled(False) 
            return

        button.setEnabled(True) 

        if is_selected:
            # 선택된 날짜 -> 파란색 원형
            button.setStyleSheet(self._get_highlight_style())
            self.highlighted_button = button 
        else:
            button.setStyleSheet(self._get_default_base_style())

    def _date_clicked(self):
        """ 날짜 버튼 클릭 -> 하이라이트 이동, 팝업창 닫기 """
        sender_button = self.sender()
        if sender_button:
            new_date_str = sender_button.property("date")
            new_date = QDate.fromString(new_date_str, "yyyy-MM-dd")

            if self.highlighted_button and self.highlighted_button != sender_button:
                self.highlighted_button.setStyleSheet(self._get_default_base_style())

            self.selected_date = new_date

            sender_button.setStyleSheet(self._get_highlight_style())
            self.highlighted_button = sender_button
            
            self.accept()
        
    def _prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self._update_calendar(self.current_date)

    def _next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self._update_calendar(self.current_date)
        
    def get_selected_date(self):
        date_str = self.selected_date.toString("yyyy-MM-dd")
        try:
            display_str = KOREAN_LOCALE.toString(self.selected_date, "MM월 dd일 (ddd)")
        except NameError:
            display_str = self.selected_date.toString("MM월 dd일 (ddd)")

        return date_str, display_str