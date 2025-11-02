from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, 
    QGridLayout, QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QDate, QRectF, QRect
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
        self.CARD_WIDTH = 270
        self.CARD_HEIGHT = 270
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT) 
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent;")
        
        # 원형 차트 관련 변수
        self.chart_size = 160
        self.ring_width = 18
        self.progress_percent = (self.current / self.total) if self.total > 0 else 0
        
        # 텍스트 위젯
        self.num_text = f"{total - current}"
        self.usage_text = f"{current}/{total}"
        self.name_text = name

        # 메인 레이아웃
        main_layout = QVBoxLayout(self) 
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addItem(QSpacerItem(0, 110, QSizePolicy.Fixed, QSizePolicy.Fixed))
    
    def paintEvent(self, event):
        """ 원형 차트 그리는 로직 """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        center_x = int(self.width() / 2)
        BOTTOM_TEXT_SPACE = 90 
        chart_area_height = self.height() - BOTTOM_TEXT_SPACE
        chart_center_y = int(chart_area_height / 2) + 10
        
        # 사각형 경계
        rect = QRectF(
            int(center_x - self.chart_size / 2), 
            int(chart_center_y - self.chart_size / 2), 
            self.chart_size, 
            self.chart_size
        )
        
        # 배경 도넛
        pen_bg = QPen(QColor(40, 40, 40), self.ring_width)
        pen_bg.setCapStyle(Qt.FlatCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect, 0 * 16, 360 * 16)

        # 진행률 도넛
        BLUE = QColor(59, 110, 235)
        pen_fg = QPen(BLUE, self.ring_width)
        pen_fg.setCapStyle(Qt.FlatCap)
        painter.setPen(pen_fg)
        span_angle = int(360 * self.progress_percent)
        painter.drawArc(rect, (90 + 360) * 16, span_angle * 16)

        # 도넛 안쪽 경계선
        donut_radius = self.chart_size / 2.0
        inner_radius = donut_radius - (self.ring_width / 2.0)
        
        # 안쪽 경계선 그릴 사각형 경계
        INNER_BORDER_RECT = QRectF(
            center_x - inner_radius, 
            chart_center_y - inner_radius, 
            inner_radius * 2, 
            inner_radius * 2
        )
        
        BORDER_WIDTH = 2
        inner_pen = QPen(BLUE, BORDER_WIDTH, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(inner_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(INNER_BORDER_RECT)

        # ---------------------------------------------
        # 텍스트
        # ---------------------------------------------

        text_center_y = chart_center_y
        donut_bottom_y = chart_center_y + (self.chart_size / 2.0)   # 도넛 가장 아래쪽 Y좌표
        VERTICAL_GAP = 15
        TEXT_START_Y = int(donut_bottom_y + VERTICAL_GAP)   # 텍스트 시작 Y좌표
        NUM_HEIGHT = 50
        USAGE_HEIGHT = 25
        CENTER_SHIFT_ADJUSTMENT = 2

        # 잔여 좌석
        font_num = painter.font()
        font_num.setPointSize(30)
        font_num.setBold(True)
        painter.setFont(font_num)
        painter.setPen(BLUE)

        num_rect_center_y = text_center_y - (USAGE_HEIGHT / 2) - CENTER_SHIFT_ADJUSTMENT        
        num_rect_start_y = num_rect_center_y - (NUM_HEIGHT / 2)
        num_rect = QRect(0, int(num_rect_start_y), self.width(), NUM_HEIGHT) 
        painter.drawText(num_rect, Qt.AlignCenter, self.num_text)
        
        # 사용 좌석/전체 좌석
        font_usage = painter.font()
        font_usage.setPointSize(18)
        font_usage.setBold(False)
        painter.setFont(font_usage)
        painter.setPen(QColor(170, 170, 170))

        usage_rect_center_y = text_center_y + (NUM_HEIGHT / 2) + CENTER_SHIFT_ADJUSTMENT
        usage_rect_start_y = usage_rect_center_y - (USAGE_HEIGHT / 2)
        usage_rect = QRect(0, int(usage_rect_start_y), self.width(), USAGE_HEIGHT)
        painter.drawText(usage_rect, Qt.AlignCenter, self.usage_text)

        # 열람실명
        font_name = painter.font()
        font_name.setPointSize(22)
        font_name.setBold(False) 
        painter.setFont(font_name)
        painter.setPen(QColor(255, 255, 255))

        name_rect = QRect(0, TEXT_START_Y, self.width(), self.height() - TEXT_START_Y)

        painter.drawText(name_rect, Qt.AlignTop | Qt.AlignHCenter | Qt.TextWordWrap, self.name_text)
        painter.end()

    def mousePressEvent(self, event):
        """ 위젯 클릭 시 콜백 함수 호출 """
        self.callback(self.name)

class ReservationPage(BasePage):
    def __init__(self, switch_callback):
        super().__init__(switch_callback)
        self.switch_callback = switch_callback

        self.set_header_spacing(-20)
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

    def _get_user_reservation_data(self):
        """ DB 연동 필요 """
        # 예약 없는 경우
        # return None 
        
        # 임시 데이터
        return {
            "room": "제1열람실",
            "seat_id": 142,
            "start_time": "11:00",
            "end_time": "17:00",
            "extend_count": 0
        }
    
    def _setup_action_buttons(self, layout):
        # 좌석 확인, 반납, 연장, Info 버튼 그룹
        icon_layout = QHBoxLayout()
        icon_layout.setAlignment(Qt.AlignCenter)
        icon_layout.setSpacing(0)
        
        icon_layout.addWidget(self._create_icon_button("좌석확인", "simple_check.png", self._show_popup, "좌석확인"))
        icon_layout.addWidget(self._create_icon_button("좌석반납", "return.png", self._go_to_return_page, None))
        icon_layout.addWidget(self._create_icon_button("좌석연장", "more_time.png", self._go_to_extend_page, None))        
        icon_layout.addWidget(self._create_icon_button("Info", "info.png", self._show_popup, "안내사항"))
        
        layout.addLayout(icon_layout)
        layout.addSpacing(40)

    def _setup_status_cards(self, layout):
        grid_container = QFrame()
        GRID_WIDTH = 600   # 컨테이너 너비 고정 -> 중앙 공백 제거
        grid_container.setFixedWidth(GRID_WIDTH)
        grid_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        grid_container.setStyleSheet("background: transparent; border: none;")

        status_grid = QGridLayout(grid_container)
        status_grid.setContentsMargins(0, 0, 0, 0)
        status_grid.setSpacing(20)  # 카드 간 간격 조정

        room_data = [
            ("제1열람실", 8, 375, "제1열람실"),
            ("제2-1열람실", 55, 270, "제2-1열람실"),
            ("제2-2열람실", 102, 136, "제2-2열람실"),
            ("제2-2열람실\n(대학원생 전용)", 15, 62, "제2-2열람실\n(대학원생 전용)"),
        ]
        
        for i, (name, current, total, key) in enumerate(room_data):
            row = i // 2
            col = i % 2
            status_card = self._create_status_card(name, current, total, lambda checked, k=key: self._go_to_seat_map(k))
            status_grid.addWidget(status_card, row, col) 

        # 테두리
        outer_frame = QFrame()
        
        outer_frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: 1px solid #444444; /* 연한 회색 테두리 */
                border-radius: 32px;
                padding: 32px;
                margin: 0px;
            }}
        """)
        
        outer_layout = QVBoxLayout(outer_frame)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.addWidget(grid_container, alignment=Qt.AlignCenter) 
        
        layout.addWidget(outer_frame, alignment=Qt.AlignHCenter)
        layout.addSpacing(60)
    
    def _create_icon_button(self, text, icon_path, callback, popup_title=None):
        """ 이미지와 텍스트를 위아래로 배치하는 버튼 생성 """
        btn = QPushButton()
        btn.setStyleSheet(ICON_BUTTON_STYLE.replace("font-size: 14px;", "")) 
        btn.setFixedSize(130, 120)
        v_layout = QVBoxLayout(btn)
        v_layout.setAlignment(Qt.AlignCenter)
        v_layout.setContentsMargins(0, 0, 0, 0)

        # 1. 이미지
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(50, 50)
        
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
        text_label.setStyleSheet("font-size: 18px; color: #ffffff;")
        
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
        dialog_buttons = None
        info_message = {}
        dialog_width = None
        current_reservation = self._get_user_reservation_data() # 예약 정보 가져오기

        if title == "안내사항":
            dialog_width = 650
            info_message = {
                "title": "이용 완료 시 좌석 반납 필수",
                "body": "기본 이용 시간: 6시간<br>" 
                        "좌석 연장: 이용 종료 1시간 전부터 연장 가능, 3회 가능<br>"
                        "30일간 좌석 미반납 3회시 5일 일반열람실 이용 불가",
                "footer": "문의: 032-860-9032",
                "body_font_size": 23
            }
            dialog_buttons = [{'text': '닫기', 'style': 'cancel', 'callback': None}]
            
        elif title == "좌석확인":
            if current_reservation:
                res = current_reservation
                styled_seat = f'<span style="color:#3B6EEB;">{res["seat_id"]}</span>'
                body_content = (f"{res['room']} {styled_seat}번")
                info_message = {"title": "좌석확인", "body": body_content, "footer": ""}
            else:
                info_message = {
                    "title": "좌석확인",
                    "body": "예약된 좌석이 없습니다.",
                    "footer": "좌석 배정 후 이용해 주세요."
                }
            dialog_buttons = [{'text': '닫기', 'style': 'cancel', 'callback': None}]
        
        else:
            info_message = {
                "title": title,
                "body": "팝업 내용이 정의되지 않았습니다.",
                "footer": ""
            }
            dialog_buttons = [{'text': '확인', 'style': 'confirm', 'callback': None}]

        if not isinstance(info_message.get("body"), str):
            info_message["body"] = str(info_message.get("body"))

        dialog = CustomAlertDialog(info_message, self, buttons=dialog_buttons, width=dialog_width) 
        dialog.exec()

    def _go_to_return_page(self):
        self.switch_callback("return_seat")

    def _go_to_extend_page(self):
        self.switch_callback("extend_seat")

    def _go_to_seat_map(self, room_name):
        self.switch_callback("seat_map", room_name)
