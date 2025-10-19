from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, 
    QGridLayout, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, QRectF
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor

from .base_page import BasePage
from ui_style import BUTTON_STYLE, ICON_BUTTON_STYLE, CustomAlertDialog

class CircleProgressWidget(QFrame):
    """ 좌석 현황을 원형 도넛 차트로 표시하고 텍스트 포함하는 커스텀 위젯 """
    def __init__(self, name, current, total, callback):
        super().__init__()
        self.current = current
        self.total = total
        self.name = name
        self.callback = callback
        
        # 전체 위젯
        self.CARD_WIDTH = 130
        self.CARD_HEIGHT = 130 
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT) 
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent;")
        
        # 원형 차트 관련 변수
        self.chart_size = 80 
        self.ring_width = 10
        self.progress_percent = (self.current / self.total) if self.total > 0 else 0
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self) 
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter) 
        
        # 중앙 컨텐츠 - 좌석 사용현황 표시
        self.center_content = QWidget(self) 
        self.center_content.setStyleSheet("background: transparent;")
        self.center_content.setFixedHeight(90) 
        
        # 중앙 컨텐츠 내부 레이아웃
        center_v_layout = QVBoxLayout(self.center_content)
        center_v_layout.setAlignment(Qt.AlignCenter)
        center_v_layout.setContentsMargins(0, 0, 0, 0)
        center_v_layout.setSpacing(5) 
        
        # 1. 잔여 좌석
        self.num_label = QLabel(f"{total - current}")
        self.num_label.setAlignment(Qt.AlignCenter)
        self.num_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff; background: transparent;")
        center_v_layout.addWidget(self.num_label, alignment=Qt.AlignCenter)
        
        # 2. 사용 좌석 / 전체 좌석
        self.usage_label = QLabel(f"{current}/{total}")
        self.usage_label.setAlignment(Qt.AlignCenter)
        self.usage_label.setStyleSheet("font-size: 10px; color: #aaaaaa; background: transparent;")
        center_v_layout.addWidget(self.usage_label, alignment=Qt.AlignCenter)
        
        # 3. 열람실명
        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("font-size: 12px; font-weight: 500; color: #ffffff; background: transparent;")
        
        main_layout.addWidget(self.center_content, 0, alignment=Qt.AlignHCenter)
        
        # 이름 레이블을 담을 컨테이너
        self.name_container = QWidget(self)
        self.name_container.setStyleSheet("background: transparent;")
        self.name_container.setFixedHeight(40)
        name_layout = QHBoxLayout(self.name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.addWidget(self.name_label, alignment=Qt.AlignCenter)
        
        main_layout.addWidget(self.name_container, 0, alignment=Qt.AlignHCenter) 

    def paintEvent(self, event):
        """ 원형 차트 그리는 로직 """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        center_x = self.width() // 2
        center_y = self.center_content.height() // 2 
        
        # 사각형 경계
        rect = QRectF(center_x - self.chart_size / 2, 
                      center_y - self.chart_size / 2, 
                      self.chart_size, self.chart_size)
        
        # 배경 도넛
        pen_bg = QPen(QColor(40, 40, 40), self.ring_width)
        pen_bg.setCapStyle(Qt.FlatCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect, 0 * 16, 360 * 16)

        # 진행률 도넛
        pen_fg = QPen(QColor(0, 123, 255), self.ring_width)
        pen_fg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_fg)
        
        span_angle = int(360 * self.progress_percent)

        painter.drawArc(rect, (90 + 360) * 16, -span_angle * 16) 

    def mousePressEvent(self, event):
        """ 위젯 클릭 시 콜백 함수 호출 """
        self.callback(self.name)

class ReservationPage(BasePage):
    def __init__(self, switch_callback):
        super().__init__(switch_callback)
        self.switch_callback = switch_callback

        self.set_header_spacing(-30)
        self.setObjectName("ReservationPage")
        self.setStyleSheet("""
            #ReservationPage {
                background-color: #1a1a1a; 
                color: #ffffff; 
                border-radius: 20px; 
            }
            QLabel {
                background: transparent;
                color: #ffffff;
            }
        """)
        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)

        today = QDate.currentDate()
        self.selected_date = today.toString("yyyy-MM-dd")
        self.selected_date_display = today.toString("MM월 dd일 (ddd)")

        self._setup_action_buttons(main_layout)
        self._setup_status_cards(main_layout)
        main_layout.addSpacing(40)

    def _setup_action_buttons(self, layout):
        # 좌석 확인, 반납, 연장, Info 버튼 그룹
        icon_layout = QHBoxLayout()
        icon_layout.setAlignment(Qt.AlignCenter)
        icon_layout.setSpacing(0)
        
        icon_layout.addWidget(self._create_icon_button("좌석확인", "simple_check.png", self._show_popup, "좌석 확인"))
        icon_layout.addWidget(self._create_icon_button("좌석반납", "return.png", self._go_to_return_page, None))
        icon_layout.addWidget(self._create_icon_button("좌석연장", "more_time.png", self._show_popup, "좌석 연장"))
        icon_layout.addWidget(self._create_icon_button("Info", "info.png", self._show_popup, "안내사항"))
        
        layout.addLayout(icon_layout)
        layout.addSpacing(40)

    def _setup_status_cards(self, layout):
        grid_container = QFrame()
        GRID_WIDTH = 260    # 컨테이너 너비 고정 -> 중앙 공백 제거
        grid_container.setFixedWidth(GRID_WIDTH)
        grid_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        grid_container.setStyleSheet("background: transparent; border: none;")

        status_grid = QGridLayout(grid_container)
        status_grid.setContentsMargins(0, 0, 0, 0)
        status_grid.setSpacing(10)  # 카드 간 간격 조정

        room_data = [
            ("제1열람실", 371, 375, "제1열람실"),
            ("제2-1열람실", 55, 270, "제2-1열람실"),
            ("제2-2열람실", 102, 136, "제2-2열람실"),
            ("제2-3열람실\n(대학원생 전용)", 15, 62, "제2-3열람실"),
        ]
        
        for i, (name, current, total, key) in enumerate(room_data):
            row = i // 2
            col = i % 2
            status_card = self._create_status_card(name, current, total, lambda checked, k=key: self._go_to_seat_map(k))
            status_grid.addWidget(status_card, row, col) 

        layout.addWidget(grid_container, alignment=Qt.AlignHCenter)
        layout.addSpacing(40)
    

    def _create_icon_button(self, text, icon_path, callback, popup_title=None):
        """ 이미지와 텍스트를 위아래로 배치하는 버튼 생성 """
        btn = QPushButton()
        btn.setStyleSheet(ICON_BUTTON_STYLE.replace("font-size: 14px;", "")) 
        btn.setFixedSize(65, 60)

        v_layout = QVBoxLayout(btn)
        v_layout.setAlignment(Qt.AlignCenter)
        v_layout.setSpacing(1) 
        v_layout.setContentsMargins(0, 5, 0, 5)

        # 1. 이미지
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(24, 24)
        
        try:
            pixmap = QPixmap(f"resources/{icon_path}")
            if pixmap.isNull():
                 icon_label.setText("")
                 icon_label.setStyleSheet("font-size: 25px; color: #007bff;")
            else:
                 scaled_pixmap = pixmap.scaled(icon_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                 icon_label.setPixmap(scaled_pixmap)
        except Exception:
            icon_label.setText("")
            icon_label.setStyleSheet("font-size: 25px; color: #007bff;")

        # 2. 텍스트
        text_label = QLabel(text)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("font-size: 9px; color: #ffffff;")
        
        v_layout.addWidget(icon_label, alignment=Qt.AlignCenter)
        v_layout.addWidget(text_label, alignment=Qt.AlignCenter)

        if callback == self._show_popup:
            btn.clicked.connect(lambda: callback(popup_title))
        else:
            btn.clicked.connect(callback)
            
        return btn

    def _create_status_card(self, name, current, total, callback):
        return CircleProgressWidget(name, current, total, lambda room_name: self._go_to_seat_map(room_name))

    
    def _show_popup(self, title):
        
        if title == "안내사항":
            info_message = {
                "title": "이용 완료 시 좌석 반납 필수",
                "body": "기본 이용 시간: 6시간\n"
                        "좌석 연장: 이용 종료 1시간 전부터 연장 가능, 3회 가능\n"
                        "30일간 좌석 미반납 3회시 5일 일반열람실 이용불가",
                "footer": "문의: 032-860-9032"
            }
        else:
            info_message = {
                "title": title, # 제목은 "좌석 확인", "좌석 연장"으로 사용
                "body": {
                    "좌석 확인": "배정된 좌석 정보 표시(DB 연동 필요)",
                    "좌석 연장": "좌석 연장 가능 여부 확인 및 처리(DB 연동 필요)"
                }.get(title, "팝업 기능 임시 구현"),
                "footer": ""
            }

        dialog = CustomAlertDialog(info_message, self) # CustomAlertDialog에 딕셔너리 전달
        dialog.exec()

    def _go_to_return_page(self):
        self.switch_callback("return_seat")

    def _go_to_seat_map(self, room_name):
        self.switch_callback("seat_map", room_name)

# 임시 열람실 배치도 페이지
class SeatMapPage(QWidget):
    def __init__(self, switch_callback, room_name=None):
        super().__init__()
        self.setStyleSheet("background-color: #1a1a1a; color: #ffffff;")
        layout = QVBoxLayout(self)
        label = QLabel(f"'{room_name}' 배치도 페이지 (구현예정)")
        label.setStyleSheet("color: #007bff; font-size: 24px;")
        layout.addWidget(label, alignment=Qt.AlignCenter)
        back_btn = QPushButton("메인으로")
        back_btn.setStyleSheet(BUTTON_STYLE)
        back_btn.clicked.connect(lambda: switch_callback("reservation"))
        layout.addWidget(back_btn, alignment=Qt.AlignCenter)