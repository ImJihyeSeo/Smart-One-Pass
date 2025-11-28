from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, 
    QGridLayout, QFrame, QSizePolicy, QSpacerItem, QComboBox, QDialog
)
from PySide6.QtCore import Qt, QDate, QRectF, QRect, QTime, QSize, QPoint
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor

from .base_page import BasePage
from ui_style import KOREAN_LOCALE, BUTTON_STYLE, ICON_BUTTON_STYLE, OverlayWidget, CustomAlertDialog, DateSelectionDialog

# 예측 모델 연동
# 순환 참조 방지를 위해 함수 안에서 import 하거나, 
# 파일 상단 try-except 구문으로 처리하는 것이 좋습니다.
from .prediction_result_page import PredictionResultPage

# 백엔드 API 연동
import sys
import os
import requests
from PySide6.QtCore import QTimer

# 상위 폴더의 session_manager 불러오기
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
try:
    from session_manager import UserSession  # 👈 여기가 핵심입니다.
except ImportError:
    print("Warning: session_manager not found")

API_BASE_URL = "http://34.213.241.165:8000"


class CircleProgressWidget(QFrame):
    """ 좌석 현황을 원형 도넛 차트로 표시하고 텍스트 포함하는 커스텀 위젯 """
    def __init__(self, name, current, total, callback):
        super().__init__()
        self.current = current
        self.total = total
        self.name = name
        self.callback = callback
        
        # 전체 위젯
        self.CARD_WIDTH = 250
        self.CARD_HEIGHT = 250
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT) 
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent;")
        
        # 원형 차트 관련 변수
        self.chart_size = 140
        self.ring_width = 16

        # 기존 코드 주석 처리
        # self.progress_percent = (self.current / self.total) if self.total > 0 else 0
        
        # # 텍스트 위젯
        # self.num_text = f"{total - current}"
        # self.usage_text = f"{current}/{total}"
        # self.name_text = name

        # 백엔드 API 연동
        # [수정] 변수 계산 로직을 별도 함수로 분리하여 초기화 시 호출
        self._recalc_variables()

        # 메인 레이아웃
        main_layout = QVBoxLayout(self) 
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addItem(QSpacerItem(0, 110, QSizePolicy.Fixed, QSizePolicy.Fixed))
    
    # 백엔드 API 연동
    # 👇 [추가 1] 내부 변수 재계산 함수
    def _recalc_variables(self):
        """ 현재 값(current)과 전체 값(total)을 기반으로 퍼센트와 텍스트를 다시 계산 """
        self.progress_percent = (self.current / self.total) if self.total > 0 else 0
        self.num_text = f"{self.total - self.current}" # 잔여 좌석
        self.usage_text = f"{self.current}/{self.total}"
        self.name_text = self.name

    # 👇 [추가 2] 외부에서 데이터를 갱신할 때 호출하는 함수 (필수!)
    def update_status(self, current, total):
        """ API에서 받아온 새로운 데이터로 UI 갱신 """
        self.current = current
        self.total = total
        self._recalc_variables() # 텍스트와 퍼센트 다시 계산
        self.update() # 화면 다시 그리기 (paintEvent 자동 호출)



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
        font_num.setPointSize(28)
        font_num.setBold(True)
        painter.setFont(font_num)
        painter.setPen(BLUE)

        num_rect_center_y = text_center_y - (USAGE_HEIGHT / 2) - CENTER_SHIFT_ADJUSTMENT        
        num_rect_start_y = num_rect_center_y - (NUM_HEIGHT / 2)
        num_rect = QRect(0, int(num_rect_start_y), self.width(), NUM_HEIGHT) 
        painter.drawText(num_rect, Qt.AlignCenter, self.num_text)
        
        # 사용 좌석/전체 좌석
        font_usage = painter.font()
        font_usage.setPointSize(16)
        font_usage.setBold(False)
        painter.setFont(font_usage)
        painter.setPen(QColor(170, 170, 170))

        usage_rect_center_y = text_center_y + (NUM_HEIGHT / 2) + CENTER_SHIFT_ADJUSTMENT
        usage_rect_start_y = usage_rect_center_y - (USAGE_HEIGHT / 2)
        usage_rect = QRect(0, int(usage_rect_start_y), self.width(), USAGE_HEIGHT)
        painter.drawText(usage_rect, Qt.AlignCenter, self.usage_text)

        # 열람실명
        font_name = painter.font()
        font_name.setPointSize(20)
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
        self.selected_date_display = KOREAN_LOCALE.toString(today, "MM월 dd일 (ddd)")

        self.selected_date_pred = self.selected_date 
        self.selected_date_display_pred = self.selected_date_display
        self.selected_time_pred = "시간대"

        self._setup_action_buttons(main_layout)
        self._setup_status_cards(main_layout)
        self._setup_prediction_section(main_layout)

        main_layout.addSpacing(40)

        # 백엔드 API 연동

        # 👇 이 부분이 있어야 앱 켜자마자 DB 값을 가져옵니다.
        self.fetch_room_stats()
        
        # 5초마다 자동 갱신
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.fetch_room_stats)
        self.timer.start()

        QTimer.singleShot(100, self.fetch_room_stats)

    # 기존 코드 주석 처리
    # def _get_user_reservation_data(self):
    #     """ DB 연동 필요 """
    #     # 예약 없는 경우
    #     # return None 
        
    #     # 임시 데이터
    #     return {
    #         "room": "제1열람실",
    #         "seat_id": 142,
    #         "start_time": "11:00",
    #         "end_time": "17:00",
    #         "extend_count": 0
    #     }



    # 백엔드 API 연동

    def _get_user_reservation_data(self):
        """ [API 연동] 현재 사용자의 예약 정보를 서버에서 가져옵니다. """
        
        # 1. 세션에서 현재 로그인한 학번 가져오기
        current_sid = UserSession.instance().get_user_id()
        
        # 로그인이 안 되어 있으면 예약 정보도 없음
        if not current_sid:
            return None

        try:
            # 2. API 호출 (GET /seat/status?sid=학번)
            response = requests.get(f"{API_BASE_URL}/seat/status", params={"sid": current_sid})
            
            if response.status_code == 200:
                data_list = response.json().get("data", [])
                
                # 예약 데이터가 없으면 None 반환 (팝업에서 "예약 없음" 뜸)
                if not data_list:
                    return None
                
                # 3. 데이터 파싱 (가장 최근/활성화된 예약 1개만 가져옴)
                res = data_list[0]
                
                # 서버의 room_id("1", "2-1")를 화면용 이름("제1열람실")으로 변환
                ROOM_NAME_MAP = {
                    "1": "제1열람실", 
                    "2-1": "제2-1열람실", 
                    "2-2": "제2-2열람실", 
                    "2-2_grad": "제2-2열람실\n(대학원생 전용)"
                }
                # 매핑된 이름이 없으면 서버 값 그대로 사용
                room_name = ROOM_NAME_MAP.get(res['room_id'], res['room_id'])

                # 4. UI에 표시할 딕셔너리 반환
                return {
                    "room": room_name,
                    "seat_id": res['seat_number'],
                    # 시간 문자열에서 초 단위 제거 (예: "11:00:00" -> "11:00")
                    "start_time": str(res['start_time'])[:5], 
                    "end_time": str(res['end_time'])[:5],
                    "extend_count": 0 # (API에 연장 횟수 정보가 없다면 0으로 고정)
                }
                
            else:
                print(f"Error getting reservation: {response.text}")
                return None

        except Exception as e:
            print(f"Network Error (Get My Reservation): {e}")
            return None

    def fetch_room_stats(self):
        """ [API 연동] 열람실별 통계 조회 """
        try:
            # 방금 만든 API 호출
            response = requests.get(f"{API_BASE_URL}/seat/stats", timeout=3)
            
            if response.status_code == 200:
                # res_json = response.json().get("data", {})

                # # 1. 타입 확인 및 데이터 추출
                # if isinstance(res_json, dict):
                #     # 예상대로 딕셔너리인 경우 ('data' 키 확인)
                #     data = res_json.get("data", {})
                # elif isinstance(res_json, list):
                #     # 만약 리스트로 왔다면, 그대로 사용하거나 첫 번째 요소 사용 (상황에 맞게)
                #     # 여기서는 데이터가 없다고 가정하고 빈 딕셔너리 처리하여 에러 방지
                #     print("Warning: Stats API returned a list, expected dict.")
                #     data = {}
                # else:
                #     data = {}

                res_json = response.json()
                
                # 2. 데이터 추출 (리스트/딕셔너리 안전 처리)
                if isinstance(res_json, list):
                    res_json = res_json[0] # 리스트면 첫 번째 요소 꺼냄
                
                # 'data' 키에서 실제 통계 정보 가져오기
                data = res_json.get("data", {})

                # 2. 데이터가 딕셔너리가 아니면 처리 중단 (방어 코드)
                if not isinstance(data, dict):
                    print(f"Error: 'data' is not a dict. Type: {type(data)}")
                    return
                
                # 매핑: 백엔드 room_id -> 프론트엔드 표시 이름
                ID_TO_NAME = {
                    "1": "제1열람실",
                    "2-1": "제2-1열람실",
                    "2-2": "제2-2열람실",
                    "2-2_grad": "제2-2열람실\n(대학원생 전용)"
                }
                
                for room_id, info in data.items():
                    display_name = ID_TO_NAME.get(room_id)
                    if display_name and display_name in self.room_widgets:
                        current = info.get('current', 0)
                        total = info.get('total', 0)
                        
                        # 카드 위젯의 update_status 메서드 호출
                        self.room_widgets[display_name].update_status(current, total)

                        # # 위젯 업데이트
                        # self.room_widgets[display_name].update_status(info['current'], info['total'])
                        
        except Exception as e:
            print(f"Stats API Error: {e}")
    



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
        grid_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_container.setStyleSheet("background: transparent; border: none;")

        status_grid = QGridLayout(grid_container)
        status_grid.setContentsMargins(0, 0, 0, 0)
        status_grid.setSpacing(20)  # 카드 간 간격 조정

        status_grid.setColumnStretch(0, 1) 
        status_grid.setColumnStretch(1, 1)

        room_data = [
            ("제1열람실", 1, 376, "제1열람실"),
            ("제2-1열람실", 2, 270, "제2-1열람실"),
            ("제2-2열람실", 3, 136, "제2-2열람실"),
            ("제2-2열람실\n(대학원생 전용)", 4, 62, "제2-2열람실\n(대학원생 전용)"),
        ]
        # 🚨 [수정 2] 나중에 업데이트하기 위해 위젯을 저장할 딕셔너리 초기화
        self.room_widgets = {}

        for i, (name, current, total, key) in enumerate(room_data):
            row = i // 2
            col = i % 2
            status_card = self._create_status_card(
                name, current, total, 
                lambda checked, k=key: self._go_to_seat_map(k)
            )
            # 🚨 [수정 3] 생성된 카드를 딕셔너리에 저장! (나중에 fetch_room_stats가 이걸 씀)
            # 줄바꿈 문자(\n)가 있으면 매칭이 안 될 수 있으니 주의해야 하지만,
            # 여기서는 name 그대로 키로 씁니다. (fetch_room_stats의 ID_TO_NAME과 일치해야 함)
            self.room_widgets[name] = status_card

            status_grid.addWidget(status_card, row, col, alignment=Qt.AlignCenter) 



        # 테두리
        outer_frame = QFrame()
        
        outer_frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: 2px solid #505050; /* 연한 회색 테두리 */
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
            current_reservation = self._get_user_reservation_data() # 예약 정보 가져오기
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

    def _setup_prediction_section(self, layout):
        prediction_container = QWidget()
        prediction_container.setFixedSize(700, 150)
        prediction_container.setStyleSheet("""
            QWidget {
                background-color: #242424; 
                border-radius: 12px;
                padding: 10px 15px;
            }
            QLabel {
                background: transparent;
            }
        """)
        vbox = QVBoxLayout(prediction_container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        input_hbox = QHBoxLayout()
        input_hbox.setSpacing(0)
        input_hbox.setAlignment(Qt.AlignCenter)

        # 제목
        header_label = QLabel("혼잡도 예측하기")
        header_label.setStyleSheet("font-size: 24px; color: #ffffff; margin: 0px;")

        # 날짜 선택
        date_vbox = QVBoxLayout()
        date_vbox.setContentsMargins(0, 0, 0, 0)
        date_vbox.setSpacing(3)
        date_vbox.setAlignment(Qt.AlignCenter)

        icon_button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 0px; 
                min-width: 50px; 
                max-width: 50px;
                min-height: 50px;
                max-height: 50px;
            }
            QPushButton:pressed {
                background-color: transparent;
            }
        """

        date_select_btn = QPushButton() 
        date_select_btn.setIcon(QPixmap("resources/calendar.png"))
        date_select_btn.setIconSize(QSize(30, 30))
        date_select_btn.setStyleSheet(icon_button_style)
        date_select_btn.clicked.connect(self._show_calendar_dialog)
        date_vbox.addWidget(date_select_btn, alignment=Qt.AlignCenter)
        
        self.date_label = QLabel(self.selected_date_display_pred)
        self.date_label.setStyleSheet("font-size: 16px; color: #ffffff;")
        self.date_label.setAlignment(Qt.AlignCenter)
        date_vbox.addWidget(self.date_label)

        # 시간 선택
        self.selected_time_pred = "시간대"
        self.time_combo = QComboBox()
        self.time_combo.setObjectName("TimeCombo")
        self.time_combo.setStyleSheet(self._get_combo_box_style())
        self._populate_time_combo()
        self.time_combo.currentIndexChanged.connect(self._update_selected_time)

        # 확인 버튼
        confirm_btn = QPushButton("확인")
        confirm_btn_style = f"""
            {BUTTON_STYLE}
            QPushButton {{
                border-radius: 25px;
                padding: 0; 
                min-width: 50px; 
                max-width: 50px;
                min-height: 50px; 
                max-height: 50px;
                font-size: 20px;
            }}
        """
        confirm_btn.setStyleSheet(confirm_btn_style) 
        confirm_btn.clicked.connect(self._show_prediction_result) 

        # 배치
        input_hbox.addStretch(1)
        input_hbox.addWidget(header_label)
        input_hbox.addStretch(1)
        input_hbox.addLayout(date_vbox)
        input_hbox.addStretch(1)
        input_hbox.addWidget(self.time_combo)
        input_hbox.addStretch(1)
        input_hbox.addWidget(confirm_btn)
        input_hbox.addStretch(1)

        vbox.addLayout(input_hbox)
        layout.addWidget(prediction_container, alignment=Qt.AlignHCenter)

    def _get_combo_box_style(self):
        """ 시간대 콤보박스 스타일 """
        COMBO_BG_COLOR = "#383838" 
        
        return f"""
            QComboBox#TimeCombo {{
                background-color: {COMBO_BG_COLOR};
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 20px;
                min-height: 40px;
                min-width: 120px;
            }}

            QComboBox#TimeCombo::drop-down {{
                border: none; 
                width: 25px; 
            }}

            QComboBox#TimeCombo::down-arrow {{
                image: url(resources/down_arrow.png); 
                width: 15px; 
                height: 15px;
                margin-right: 5px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {COMBO_BG_COLOR}; 
                color: #ffffff;
                border: 1px solid #444444; 
                border-top-left-radius: 4px;      
                border-top-right-radius: 4px;     
                border-bottom-left-radius: 0px;   
                border-bottom-right-radius: 0px;  
                selection-background-color: #3263ed;
                outline: none;
            }}
            
            QComboBox QAbstractItemView::item {{
                min-height: 45px;
                padding: 5px 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.15); 
            }}

            QComboBox QAbstractItemView::item:last {{
                border-bottom: none;
            }}
                        
            QScrollBar:vertical {{
                width: 40px; /* 스크롤바 너비 */
                background: {COMBO_BG_COLOR}; 
                margin: 0px;
            }}

            /* Thumb */
            QScrollBar::handle:vertical {{
                background: #ffffff;
                min-height: 50px;
                border-radius: 8px; 
                border: none;
            }}
            
            /* 상/하 화살표 버튼 제거 */
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                subcontrol-position: none; 
            }}
        """

    def _populate_time_combo(self):
        """ 06:00 ~ 00:00 시간대 목록 """
        time_list = []
        time_list.append("시간대") 

        time_list.append(QTime(0, 0).toString("hh:mm")) # 자정
        
        for hour in range(6, 24):
            time_list.append(QTime(hour, 0).toString("hh:mm"))
        
        self.time_combo.addItems(time_list)
        self.time_combo.setCurrentIndex(0)
        
    def _update_selected_time(self, index):
        """ 콤보박스 선택 -> 시간 업데이트 """
        self.selected_time_pred = self.time_combo.currentText()
        
    def _show_calendar_dialog(self):
        """ 달력 팝업창 표시 """
        
        # 오버레이
        overlay = OverlayWidget(self) 
        overlay.show()
        overlay.setGeometry(self.rect())

        # 달력 팝업창 생성 / 초기 날짜 설정
        initial_date = QDate.fromString(self.selected_date_pred, "yyyy-MM-dd") 
        dialog = DateSelectionDialog(initial_date, overlay) 
        dialog.setWindowFlags(Qt.Window | Qt.FramelessWindowHint) 

        dialog_width = 550 
        dialog_height = 600
        dialog.setFixedSize(dialog_width, dialog_height) 
        
        # 중앙 좌표 계산
        parent_center = self.rect().center()
        dialog_x = parent_center.x() - dialog_width // 2
        dialog_y = parent_center.y() - dialog_height // 2
        dialog.move(self.mapToGlobal(QPoint(dialog_x, dialog_y)))

        result = dialog.exec()
        
        # 오버레이 숨기기 / 메모리에서 해제
        overlay.hide()
        overlay.deleteLater()

        # 결과 처리
        if result == QDialog.Accepted:
            selected_date_str, display_str = dialog.get_selected_date() 
            self.selected_date_pred = selected_date_str
            self.selected_date_display_pred = display_str
            self.date_label.setText(display_str)

    def _show_prediction_result(self):
        # 기존 코드 주석 처리
        # date_display = self.selected_date_display_pred
        # time_str = self.selected_time_pred

        # # 시간 선택 유효성 검사
        # if time_str == "시간대":
        #     error_msg = {
        #         "title": "입력 오류",
        #         "body": "원하는 시간을 선택해주세요.",
        #         "footer": ""
        #     }
        #     dialog = CustomAlertDialog(error_msg, self, width=450) 
        #     dialog.exec()
        #     return

        # # 페이지 전환 및 데이터 전달
        # prediction_info = {
        #     'date_str': self.selected_date_pred, 
        #     'date_display': date_display, 
        #     'time_str': time_str
        # }
        # self.switch_callback("prediction_result", data=prediction_info)
        

        # 예측 모델 연동
        """
        [조회하기] 버튼 클릭 시 실행되는 함수
        백엔드 API를 호출하여 예측 결과를 가져오고, 결과 페이지로 이동합니다.
        """
        # 1. 사용자가 선택한 날짜와 시간 가져오기
        # (self.selected_date_pred는 '2025-11-26', self.selected_time_pred는 '14:00' 형태라고 가정)
        date_str = getattr(self, 'selected_date_pred', None)
        time_str = getattr(self, 'selected_time_pred', None)
        
        # 유효성 검사: 날짜나 시간을 선택하지 않았을 경우
        if not date_str or not time_str or time_str == "시간대":
            error_msg = {
                "title": "입력 오류",
                "body": "원하는 날짜와 시간을 모두 선택해주세요.",
                "footer": ""
            }
            dialog = CustomAlertDialog(error_msg, self, width=450)
            dialog.exec()
            return

        # 2. 백엔드 전송용 날짜 포맷 만들기 ("YYYY-MM-DD HH:MM:SS")
        # 예: "2025-11-26 14:00:00"
        target_datetime = f"{date_str} {time_str}:00"
        print(f"📡 예측 요청 시간: {target_datetime}")

        # 3. 백엔드 API 호출
        try:
            # 로딩 중 표시가 필요하다면 여기서 애니메이션 시작 등을 처리
            
            response = requests.post(
                f"{API_BASE_URL}/predict/results", # /seat을 제거하고 /predict로 요청
                json={"target_time": target_datetime},
                timeout=5 # 5초 타임아웃 설정 (앱 멈춤 방지)
            )
            
            if response.status_code == 200:
                api_response = response.json()
                results = api_response["results"] 
                # results 예시: [{'name': '제1열람실', 'status': '여유', 'color': '#00c853'}, ...]

                # 4. 페이지 전환 및 데이터 전달
                
                # 결과 페이지에 표시할 날짜 텍스트 (예: self.selected_date_display_pred 사용)
                display_info = {
                    'date_display': getattr(self, 'selected_date_display_pred', date_str),
                    'time_str': time_str
                }

                # (1) 결과 페이지 객체 생성 (import 필요!)
                # 파일 상단에: from .prediction_result_page import PredictionResultPage 추가 필요
                
                result_page = PredictionResultPage(self.switch_callback, display_info)
                
                # (2) ★ 핵심: 백엔드 데이터 주입
                # (prediction_result_page.py에 update_ui 메서드가 있어야 함)
                if hasattr(result_page, 'update_ui'):
                    result_page.update_ui(results)
                else:
                    print("⚠️ Warning: update_ui 메서드가 PredictionResultPage에 없습니다.")

                # (3) 화면 전환 (메인 윈도우의 스택 위젯을 제어해야 함)
                # self.parent()는 보통 StackedWidget이나 MainWindow입니다.
                # 구조상 switch_callback을 통해 페이지를 바꾸는 것이 더 안전할 수 있습니다.
                # 하지만 '새로운 페이지 인스턴스'를 띄워야 하므로, 아래 방식을 사용합니다.
                
                # 메인 윈도우 찾기 (parent를 타고 올라감)
                main_window = self.window() 
                if main_window and hasattr(main_window, 'stacked_widget'):
                    main_window.stacked_widget.addWidget(result_page)
                    main_window.stacked_widget.setCurrentWidget(result_page)
                else:
                    print("❌ Error: 메인 윈도우의 stacked_widget을 찾을 수 없습니다.")

            else:
                # 서버 에러 처리
                error_msg = {
                    "title": "예측 실패",
                    "body": f"서버에서 오류가 발생했습니다.\n(Code: {response.status_code})",
                    "footer": "잠시 후 다시 시도해주세요."
                }
                CustomAlertDialog(error_msg, self).exec()

        except requests.exceptions.ConnectionError:
            error_msg = {
                "title": "연결 오류",
                "body": "서버와 연결할 수 없습니다.\n백엔드가 켜져 있는지 확인해주세요.",
                "footer": ""
            }
            CustomAlertDialog(error_msg, self).exec()
            
        except Exception as e:
            print(f"Error: {e}")
            error_msg = {
                "title": "오류",
                "body": f"알 수 없는 오류가 발생했습니다.\n{str(e)}",
                "footer": ""
            }
            CustomAlertDialog(error_msg, self).exec()