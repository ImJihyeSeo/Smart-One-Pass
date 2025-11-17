from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QFrame, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from .base_page import BasePage
from ui_style import BUTTON_STYLE, CANCEL_BUTTON_STYLE, TITLE_STYLE

# 백엔드 API 연동

import sys
import os
import requests
from datetime import datetime, timedelta
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

# 상위 폴더의 session_manager 불러오기
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
try:
    from session_manager import UserSession
except ImportError:
    print("Warning: session_manager not found")

# API 주소
API_BASE_URL = "http://34.213.241.165:8000/seat"



class ReturnSeatPage(BasePage):
    """좌석 반납 페이지"""

    def __init__(self, switch_callback):
        super().__init__(switch_callback)
        self.setObjectName("ReturnSeatPage")

        # 기존 코드 주석 처리
        # # 좌석 정보 (DB 연동 필요)
        # self.seat_data = {
        #     "seat_room": "2-1",
        #     "seat_number": "148",
        #     "assigned_time_start": "1:00",
        #     "assigned_time_end": "7:00",
        #     "remaining_time_min": 300,
        #     "total_time_min": 360,
        #     "extend_time": "6:00"
        # }

        # 백엔드 API 연동
        # 좌석 정보 초기화
        self.seat_data = {
            "seat_room": "-",
            "seat_number": "-",
            "assigned_time_start": "-",
            "assigned_time_end": "-",
            "remaining_time_min": 0,
            "total_time_min": 0,
            "extend_time": "-" 
        }

        # 색상 상수
        CARD_BG = "#242424"
        BLUE = "#2e6cff"
        WHITE = "#ffffff"

        # 기본 스타일
        self.setStyleSheet(f"""
            #ReturnSeatPage {{
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
        question_label = QLabel("좌석을 반납하시겠습니까?")
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

        for text in ["좌석", "배정일시", "잔여시간", "연장가능시간"]:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size: 28px; color: {WHITE}; font-weight: 800;")
            key_layout.addWidget(lbl, alignment=Qt.AlignLeft)

        # 중앙 세로선
        line_frame = QFrame()
        line_frame.setStyleSheet(f"border-left: 1px solid {WHITE};") 
        line_frame.setFixedWidth(1) 
        line_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # 기존 코드 주석 처리
        # # 오른쪽 값 라벨
        # value_layout = QVBoxLayout()
        # value_layout.setSpacing(30)

        # 백엔드 API 연동
        # 오른쪽 값 라벨 (나중에 업데이트하기 위해 멤버 변수로 저장)
        self.value_labels = {}
        value_container = QWidget()
        value_layout = QVBoxLayout(value_container)
        value_layout.setSpacing(30)


        # 라벨 생성 헬퍼 함수
        def create_value_label(key, color=WHITE):
            lbl = QLabel("-")
            lbl.setStyleSheet(f"font-size: 28px; color: {color};")
            lbl.setTextFormat(Qt.RichText)
            lbl.setWordWrap(False)
            value_layout.addWidget(lbl, alignment=Qt.AlignLeft)
            self.value_labels[key] = lbl

        create_value_label("seat_info")
        create_value_label("time_info")
        create_value_label("remain_info") # 잔여시간은 색상이 섞여있어 HTML로 처리
        create_value_label("extend_info")


        # 기존 코드 주석 처리
        # value_htmls = [
        #     # 좌석
        #     f'<span style="font-size:28px; color:{WHITE};">'
        #     f'제{self.seat_data["seat_room"]}열람실 {self.seat_data["seat_number"]}번'
        #     f'</span>',
            
        #     # 배정일시
        #     f'<span style="font-size:28px; color:{WHITE};">'
        #     f'오후 {self.seat_data["assigned_time_start"]} ~ 오후 {self.seat_data["assigned_time_end"]}'
        #     f'</span>',
            
        #     # 잔여시간
        #     f'<span style="font-size:28px;">'
        #     f'<span style="color:{BLUE}; font-weight:bold;">{self.seat_data["remaining_time_min"]}</span>' # 파란색
        #     f'<span style="color:{WHITE};"> / {self.seat_data["total_time_min"]}</span>'
        #     f'<span style="color:{WHITE};"> (분)</span>' 
        #     f'</span>',
            
        #     # 연장가능시간
        #     f'<span style="font-size:28px; color:{WHITE};">'
        #     f'오후 {self.seat_data["extend_time"]}'
        #     f'</span>'
        # ]

        # for html in value_htmls:
        #     lbl = QLabel(html)
        #     lbl.setTextFormat(Qt.RichText)
        #     lbl.setWordWrap(False)
        #     value_layout.addWidget(lbl, alignment=Qt.AlignLeft)

        # 레이아웃 배치
        card_h_layout.addWidget(key_container)
        card_h_layout.addWidget(line_frame)
        card_h_layout.addLayout(value_layout)

        # 반납 버튼
        return_btn = QPushButton("반납")
        return_btn.setFixedSize(200, 100)
        return_btn.setStyleSheet(BUTTON_STYLE)
        return_btn.clicked.connect(self._handle_return)
        
        # 취소 버튼
        cancel_btn = QPushButton("취소")
        cancel_btn.setFixedSize(200, 100)
        cancel_btn.setStyleSheet(CANCEL_BUTTON_STYLE)
        cancel_btn.clicked.connect(lambda: self.switch_callback("reservation"))

        # 버튼 그룹 레이아웃
        btn_h_layout = QHBoxLayout()
        btn_h_layout.addWidget(return_btn)
        btn_h_layout.addWidget(cancel_btn)
        btn_h_layout.setAlignment(Qt.AlignHCenter)
        
        main_layout.addSpacing(50)
        main_layout.addLayout(btn_h_layout)
        main_layout.addStretch(1)


        # 기존 코드 주석 처리
        # def _handle_return(self):
        #     """좌석 반납 처리 (DB 연동 필요)"""
        #     self.switch_callback("result", mode="return")

        # 백엔드 API 연동
        # [API 연동] 페이지 로드 시 데이터 가져오기
        QTimer.singleShot(100, self.fetch_seat_info)

    def update_ui_labels(self):
        """ self.seat_data를 기반으로 UI 텍스트 갱신 """
        BLUE = "#2e6cff"
        WHITE = "#ffffff"
        
        # 1. 좌석
        self.value_labels["seat_info"].setText(
            f'제{self.seat_data["seat_room"]}열람실 {self.seat_data["seat_number"]}번'
        )
        
        # 2. 배정 일시
        self.value_labels["time_info"].setText(
            f'오후 {self.seat_data["assigned_time_start"]} ~ 오후 {self.seat_data["assigned_time_end"]}'
        )
        
        # 3. 잔여 시간 (HTML)
        remain_html = (
            f'<span style="font-size:28px;">'
            f'<span style="color:{BLUE}; font-weight:bold;">{self.seat_data["remaining_time_min"]}</span>'
            f'<span style="color:{WHITE};"> / {self.seat_data["total_time_min"]}</span>'
            f'<span style="color:{WHITE};"> (분)</span>'
            f'</span>'
        )
        self.value_labels["remain_info"].setText(remain_html)
        
        # 4. 연장 가능 시간
        self.value_labels["extend_info"].setText(
            f'오후 {self.seat_data["extend_time"]}'
        )

    def fetch_seat_info(self):
        """ [API 연동] 현재 좌석 정보 조회 """
        current_sid = UserSession.instance().get_user_id()
        if not current_sid:
            return

        try:
            # GET /seat/status
            response = requests.get(f"{API_BASE_URL}/status", params={"sid": current_sid})
            
            if response.status_code == 200:
                data_list = response.json().get("data", [])
                
                if not data_list:
                    QMessageBox.warning(self, "알림", "반납할 좌석이 없습니다.")
                    self.switch_callback("reservation")
                    return

                reservation = data_list[0]
                
                # 데이터 파싱 및 가공
                # room_id 매핑
                ROOM_MAP = {"1": "1", "2-1": "2-1", "2-2": "2-2", "2-2_grad": "2-2(대학원)"}
                room_name = ROOM_MAP.get(reservation['room_id'], reservation['room_id'])
                
                # 시간 계산
                # 1. 현재 시간 가져오기
                now = datetime.now()
                time_fmt = "%H:%M:%S" # DB 시간 형식

                try:
                    # 2. DB 문자열을 시간 객체로 변환
                    # (reservation['start_time']은 "14:00:00" 같은 문자열임)
                    s_time_obj = datetime.strptime(reservation['start_time'], time_fmt).time()
                    e_time_obj = datetime.strptime(reservation['end_time'], time_fmt).time()

                    # 3. 오늘 날짜와 합쳐서 온전한 datetime 객체 생성
                    # (시간끼리만 빼면 날짜 계산이 안 되므로 오늘 날짜를 붙여줌)
                    start_dt = datetime.combine(now.date(), s_time_obj)
                    end_dt = datetime.combine(now.date(), e_time_obj)

                    # 4. 총 이용 시간 계산 (종료 - 시작)
                    total_delta = end_dt - start_dt
                    total_min = int(total_delta.total_seconds() / 60)

                    # 5. 잔여 시간 계산 (종료 - 현재)
                    remain_delta = end_dt - now
                    remain_min = int(remain_delta.total_seconds() / 60)

                    # (만약 예약 시간이 이미 지났다면 0으로 처리)
                    if remain_min < 0:
                        remain_min = 0

                    # 6. 연장 가능 시간 계산 (종료 1시간 전)
                    extend_possible_dt = end_dt - timedelta(hours=1)
                    extend_time_str = extend_possible_dt.strftime("%H:%M")

                except Exception as e:
                    print(f"Time Calculation Error: {e}")
                    # 에러 발생 시 기본값 설정
                    total_min = 0
                    remain_min = 0
                    extend_time_str = "-"

                self.seat_data["seat_room"] = room_name
                self.seat_data["seat_number"] = str(reservation['seat_number'])
                self.seat_data["assigned_time_start"] = str(reservation['start_time'])[:5]
                self.seat_data["assigned_time_end"] = str(reservation['end_time'])[:5]
                
                # 잔여 시간 등은 현재 시간 기준으로 계산 필요 (여기서는 임시 값)
                self.seat_data["remaining_time_min"] = remain_min # 예시
                self.seat_data["total_time_min"] = total_min # 3시간

                # 🚨 계산한 시간을 여기에 넣어서 'is not accessed' 경고 해결!
                self.seat_data["extend_time"] = extend_time_str

                self.update_ui_labels()
                
            else:
                QMessageBox.critical(self, "오류", "정보를 불러오지 못했습니다.")

        except Exception as e:
            print(f"Network Error: {e}")


    def _handle_return(self):
        """ [API 연동] 좌석 반납 요청 """
        current_sid = UserSession.instance().get_user_id()
        
        try:
            # POST /seat/return
            payload = {"sid": current_sid}
            response = requests.post(f"{API_BASE_URL}/return", json=payload)
            
            if response.status_code == 201:
                self.switch_callback("result", mode="return")
            else:
                error_msg = response.json().get("detail", {}).get("message", "반납 실패")
                QMessageBox.warning(self, "반납 실패", error_msg)
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"통신 오류: {e}")