from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QFrame, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from .base_page import BasePage
from ui_style import BUTTON_STYLE, CANCEL_BUTTON_STYLE, TITLE_STYLE, CustomAlertDialog
import sys
import requests
from datetime import datetime, timedelta
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QMessageBox
)
import os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from session_manager import UserSession

API_BASE_URL = "http://34.213.241.165:8000/seat"

class ExtendSeatPage(BasePage):
    """좌석 연장 페이지"""

    def __init__(self, switch_callback):
        super().__init__(switch_callback)
        self.setObjectName("ExtendSeatPage")

        # 현재 예약 정보를 담을 변수 초기화
        self.current_reservation_id = None
        self.seat_data = {
            "seat_room": "-",
            "seat_number": "-",
            "assigned_time_start": "-",
            "assigned_time_end": "-",
            "extend_duration": "3",
            "new_end_time": "-"
        }
        
        self.value_labels = {}
        
        CARD_BG = "#242424"
        BLUE = "#2e6cff"
        WHITE = "#ffffff"
        
        self.setStyleSheet(f"""
            #ExtendSeatPage {{
                background-color: #1a1a1a;
                color: {WHITE};
            }}
            #QuestionText {{
                font-size: 24px;
                font-weight: 500;
                color: {WHITE};
            }}
        """)

        # 메인 레이아웃
        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.setSpacing(50)
        main_layout.addSpacing(70)

        # 질문 문구
        question_label = QLabel("좌석을 연장하시겠습니까?")
        question_label.setAlignment(Qt.AlignCenter)
        question_label.setObjectName("QuestionText")
        question_label.setStyleSheet(TITLE_STYLE)
        main_layout.addWidget(question_label)
        main_layout.addSpacing(25)

        # 카드 프레임
        card_frame = QFrame()
        card_frame.setFixedSize(680, 450)
        card_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum) 
        card_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD_BG};
                border-radius: 18px;
            }}
        """)
        main_layout.addWidget(card_frame, alignment=Qt.AlignHCenter)

        # 카드 내부 레이아웃
        card_h_layout = QHBoxLayout(card_frame)
        card_h_layout.setContentsMargins(50, 40, 50, 40)
        card_h_layout.setSpacing(40)

        # 왼쪽 라벨
        key_container = QWidget()
        key_container.setFixedWidth(180)
        key_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum) 
        key_layout = QVBoxLayout(key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(30)

        for text in ["좌석", "배정일시", "연장시간", "종료시간"]: 
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size: 28px; color: {WHITE}; font-weight: 800;")
            key_layout.addWidget(lbl, alignment=Qt.AlignLeft)

        # 중앙 세로선
        line_frame = QFrame()
        line_frame.setStyleSheet(f"border-left: 1px solid {WHITE};") 
        line_frame.setFixedWidth(1) 
        line_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)


        # 오른쪽 값 라벨
        value_container = QWidget()
        value_layout = QVBoxLayout(value_container)
        value_layout.setSpacing(30)
        value_layout.setContentsMargins(0, 0, 0, 0)

        value_htmls = [
            # 좌석
            f'<span style="font-size:28px; color:{WHITE};">'
            f'제{self.seat_data["seat_room"]}열람실 {self.seat_data["seat_number"]}번'
            f'</span>',

            # 배정일시
            f'<span style="font-size:28px; color:{WHITE};">'
            f'오후 {self.seat_data["assigned_time_start"]} ~ 오후 {self.seat_data["assigned_time_end"]}'
            f'</span>',
            
            # 연장시간
            f'<span style="font-size:28px; color:{BLUE}; font-weight:bold;">'
            f'{self.seat_data["extend_duration"]}'  # 파란색
            f'</span>'
            f'<span style="font-size:28px; color:{WHITE};">시간</span>',
            
            # 종료시간
            f'<span style="font-size:28px; color:{WHITE};">'
            f'오후 {self.seat_data["new_end_time"]}'
            f'</span>'
        ]

        # create_value_label 메서드를 사용해 라벨을 생성하고 딕셔너리에 저장
        self.create_value_label("seat_info", value_layout, WHITE)
        self.create_value_label("time_info", value_layout, WHITE)
        self.create_value_label("extend_time", value_layout, BLUE, is_bold=True, suffix="시간")
        self.create_value_label("end_time", value_layout, WHITE)

        # 레이아웃 배치
        card_h_layout.addWidget(key_container)
        card_h_layout.addWidget(line_frame)
        card_h_layout.addWidget(value_container)

        # 연장 버튼
        extend_btn = QPushButton("연장")
        extend_btn.setFixedSize(200, 100)
        extend_btn.setStyleSheet(BUTTON_STYLE)
        extend_btn.clicked.connect(self._handle_extend)

        # 취소 버튼
        cancel_btn = QPushButton("취소")
        cancel_btn.setFixedSize(200, 100)
        cancel_btn.setStyleSheet(CANCEL_BUTTON_STYLE)
        cancel_btn.clicked.connect(lambda: self.switch_callback("reservation"))

        # 버튼 그룹 레이아웃
        btn_h_layout = QHBoxLayout()
        btn_h_layout.addWidget(extend_btn)
        btn_h_layout.addWidget(cancel_btn)
        btn_h_layout.setAlignment(Qt.AlignCenter)

        main_layout.addSpacing(50)
        main_layout.addLayout(btn_h_layout)
        main_layout.addStretch(1)

        QTimer.singleShot(100, self.fetch_seat_info)

    def create_value_label(self, key, layout, color, is_bold=False, suffix=""):
        """라벨을 생성하고 나중에 업데이트할 수 있도록 저장"""
        font_weight = "bold" if is_bold else "normal"
        lbl = QLabel("-")
        lbl.setStyleSheet(f"font-size: 28px; color: {color}; font-weight: {font_weight};")
        lbl.setTextFormat(Qt.RichText)
        layout.addWidget(lbl, alignment=Qt.AlignLeft)
        self.value_labels[key] = {"label": lbl, "color": color, "suffix": suffix}

        # 딕셔너리에 저장 (업데이트 때 사용)
        self.value_labels[key] = {"label": lbl, "color": color, "suffix": suffix}

    def update_ui_labels(self):
        """self.seat_data를 바탕으로 UI 텍스트 갱신"""

        if not hasattr(self, 'value_labels') or not self.value_labels:
            return

        try:
            # 1. 좌석 정보
            if "seat_info" in self.value_labels:
                self.value_labels["seat_info"]["label"].setText(
                    f'제{self.seat_data["seat_room"]}열람실 {self.seat_data["seat_number"]}번'
                )
            # 2. 배정 일시
            if "time_info" in self.value_labels:
                start_str = self._format_time_str(self.seat_data["assigned_time_start"])
                end_str = self._format_time_str(self.seat_data["assigned_time_end"])
                self.value_labels["time_info"]["label"].setText(f'{start_str} ~ {end_str}')
            # 3. 연장 시간
            if "extend_time" in self.value_labels:
                self.value_labels["extend_time"]["label"].setText(
                    f'{self.seat_data["extend_duration"]}{self.value_labels["extend_time"]["suffix"]}'
                )
            # 4. 예상 종료 시간
            if "end_time" in self.value_labels:
                end_time_str = self._format_time_str(self.seat_data["new_end_time"])
                self.value_labels["end_time"]["label"].setText(f'{end_time_str}')

        except RuntimeError:
            print("Warning: UI 업데이트 중 위젯이 삭제됨")
        except Exception as e:
            print(f"UI Update Error: {e}")

    def fetch_seat_info(self):
        """[API 연동] 서버에서 현재 사용자의 좌석 정보를 조회"""

        # 1. 세션에서 로그인한 학번 가져오기
        current_sid = UserSession.instance().get_user_id()
        
        if not current_sid:
            # 테스트 중이라 로그인을 안 거쳤다면, 경고 후 리턴
            QMessageBox.critical(self, "오류", "로그인 정보가 없습니다. 다시 로그인해주세요.")
            return
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/status", 
                params={"sid": current_sid}
            )
            
            if response.status_code == 200:
                res_json = response.json()
                data_list = res_json.get("data", [])
                
                if not data_list:
                    QMessageBox.warning(self, "알림", "현재 이용 중인 좌석이 없습니다.")
                    self.extend_btn.setEnabled(False)
                    return

                # 가장 최근 예약 정보 가져오기 (활성 예약)
                # 백엔드의 get_reservation_status는 리스트를 반환함
                reservation = data_list[0] 
                
                self.current_reservation_id = reservation['reservation_id']
                
                # 시간 데이터 처리
                raw_start = str(reservation['start_time'])
                raw_end = str(reservation['end_time'])
                
                # 시간 포맷팅 (YYYY-MM-DD HH:MM:SS -> HH:MM)
                # 만약 HH:MM:SS만 온다면 그대로 사용
                if len(raw_start) > 5:
                    display_start = raw_start[11:16] if len(raw_start) > 10 else raw_start[:5]
                else:
                    display_start = raw_start

                if len(raw_end) > 5:
                    display_end = raw_end[11:16] if len(raw_end) > 10 else raw_end[:5]
                else:
                    display_end = raw_end

                # 연장 후 종료 시간 계산 (3시간 추가)
                try:
                    # DB에서 오는 형식이 'YYYY-MM-DD HH:MM:SS'라고 가정
                    full_fmt = "%Y-%m-%d %H:%M:%S"
                    
                    # 날짜가 없을 경우를 대비한 처리
                    if len(raw_end) < 10: 
                        now = datetime.now()
                        end_dt = datetime.combine(now.date(), datetime.strptime(raw_end, "%H:%M:%S").time())
                    else:
                        end_dt = datetime.strptime(raw_end, full_fmt)
                        
                    new_end_dt = end_dt + timedelta(hours=3)
                    new_end_str = new_end_dt.strftime("%H:%M")
                    
                except Exception as e:
                    print(f"Time Calc Error: {e}")
                    new_end_str = "-"

                # 표시용 데이터 업데이트
                ROOM_MAP = {"1": "1", "2-1": "2-1", "2-2": "2-2", "2-2_grad": "2-2(대학원)"}
                
                self.seat_data["seat_room"] = ROOM_MAP.get(reservation.get('room_id'), str(reservation.get('room_id')))
                self.seat_data["seat_number"] = str(reservation.get('seat_number', '?'))
                self.seat_data["assigned_time_start"] = display_start
                self.seat_data["assigned_time_end"] = display_end
                self.seat_data["new_end_time"] = new_end_str

                self.update_ui_labels()
                
            else:
                print(f"Error fetching status: {response.text}")
                QMessageBox.critical(self, "오류", "좌석 정보를 불러오지 못했습니다.")

        except Exception as e:
            print(f"Network Error: {e}")
            QMessageBox.critical(self, "오류", f"서버 연결 실패: {e}")

    def _handle_extend(self):
        """[API 연동] 좌석 연장 요청 전송"""
        if not self.current_reservation_id:
            QMessageBox.warning(self, "오류", "연장할 좌석 정보가 없습니다.")
            return

        # 세션에서 학번 가져오기
        current_sid = UserSession.instance().get_user_id()
        
        try:
            payload = {
                "reservation_id": self.current_reservation_id,
                "sid": current_sid
            }
            
            response = requests.post(f"{API_BASE_URL}/extend", json=payload)
            
            if response.status_code == 201:
                self.switch_callback("result", mode="extend")
            
            elif response.status_code == 409:
                # 실패 (정책 위반: 시간 부족, 최대 시간 초과 등)
                error_msg = response.json().get("detail", {}).get("message", "연장할 수 없습니다.")

                # QMessageBox.warning(self, "연장 실패", error_msg)
                message = {
                    "title": "연장 실패",
                    "body": error_msg, # "예약 후 최소 120분을..."
                    "footer": ""
                }
                buttons = [
                    {
                        'text': '확인', 
                        'style': 'confirm', 
                        # 🚨 여기서 메인 화면("reservation")으로 이동시킵니다.
                        'callback': lambda: self.switch_callback("reservation") 
                    }
                ]
                CustomAlertDialog(message, self, buttons=buttons).exec()
            
            else:
                CustomAlertDialog({"title":"오류", "body":f"연장 요청 실패 (Code: {response.status_code})"}, self).exec()

        except Exception as e:
            CustomAlertDialog({"title":"오류", "body":f"서버 통신 오류: {e}"}, self).exec()

        
    def _format_time_str(self, time_str):
        """ 'HH:MM' 문자열을 받아 '오전/오후 H:MM' 형태로 변환 """
        if not time_str or time_str == "-":
            return "-"
        try:
            hour, minute = map(int, time_str.split(':'))
            
            ampm = "오후" if hour >= 12 else "오전"
            
            display_hour = hour % 12
            if display_hour == 0: 
                display_hour = 12
            
            return f"{ampm} {display_hour}:{minute:02d}"
        except Exception:
            return time_str # 변환 실패 시 원본 반환