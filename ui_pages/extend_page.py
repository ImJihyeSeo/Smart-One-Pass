from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QFrame, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from .base_page import BasePage
from ui_style import BUTTON_STYLE, CANCEL_BUTTON_STYLE, TITLE_STYLE

# 백엔드 API 연동
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

# 현재 로그인한 사용자 ID (로그인 시점에 저장된 전역 변수나 설정에서 가져와야 함)
# 테스트를 위해 임시 값 설정
# CURRENT_USER_SID = "20181234"




class ExtendSeatPage(BasePage):
    """좌석 연장 페이지"""

    def __init__(self, switch_callback):
        super().__init__(switch_callback)
        self.setObjectName("ExtendSeatPage")

        # 좌석 정보 (DB 연동 필요)
        # self.seat_data = {
        #     "seat_room": "2-1",
        #     "seat_number": "53",
        #     "assigned_time_start": "1:00",  # 배정 시작
        #     "assigned_time_end": "7:00",    # 배정 종료
        #     "extend_duration": "3", # 연장 시간
        #     "new_end_time": "10:00" # 연장 후 종료 시간
        # }

        # 백엔드 API 연동
        # 현재 예약 정보를 담을 변수 초기화
        self.current_reservation_id = None
        self.seat_data = {
            "seat_room": "-",
            "seat_number": "-",
            "assigned_time_start": "-",
            "assigned_time_end": "-",
            "extend_duration": "3", # core_service.py에 EXTENSION_DURATION = 3시간으로 고정됨
            "new_end_time": "-"
        }
        
        # ✅ [수정 1] 라벨 저장용 딕셔너리 초기화 (이게 없어서 에러가 났음)
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

        # # 오른쪽 값 라벨
        # value_layout = QVBoxLayout()
        # value_layout.setSpacing(30)

        # [오른쪽] 값 라벨 (여기를 수정함)
        value_container = QWidget() # 레이아웃 에러 방지용 컨테이너
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

        # for html in value_htmls:
        #     lbl = QLabel(html)
        #     lbl.setTextFormat(Qt.RichText)
        #     lbl.setWordWrap(False)
        #     value_layout.addWidget(lbl, alignment=Qt.AlignLeft)
        
        # ✅ [수정 2] create_value_label 메서드를 사용해 라벨을 생성하고 딕셔너리에 저장
        # (기존의 for html in value_htmls 루프 삭제함)
        self.create_value_label("seat_info", value_layout, WHITE)
        self.create_value_label("time_info", value_layout, WHITE)
        self.create_value_label("extend_time", value_layout, BLUE, is_bold=True, suffix="시간")
        self.create_value_label("end_time", value_layout, WHITE)

        # 레이아웃 배치
        card_h_layout.addWidget(key_container)
        card_h_layout.addWidget(line_frame)
        # card_h_layout.addLayout(value_layout)
        card_h_layout.addWidget(value_container) # ✅ 컨테이너를 넣어야 안전함

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

        # 백엔드 API 연동
        # 페이지 로드 시 데이터 가져오기 (UI가 그려진 후 실행)
        QTimer.singleShot(100, self.fetch_seat_info)

    # def _handle_extend(self):
    #     """좌석 연장 처리 (DB 연동 필요)"""
    #     self.switch_callback("result", mode="extend")


    # 백엔드 API 연동

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

        # ✅ [안전장치] 페이지가 닫혔거나 라벨이 없으면 중단
        if not hasattr(self, 'value_labels') or not self.value_labels:
            return
        
        # # 1. 좌석 정보
        # self.value_labels["seat_info"]["label"].setText(
        #     f'제{self.seat_data["seat_room"]}열람실 {self.seat_data["seat_number"]}번'
        # )
        # # 2. 배정 일시
        # self.value_labels["time_info"]["label"].setText(
        #     f'오후 {self.seat_data["assigned_time_start"]} ~ 오후 {self.seat_data["assigned_time_end"]}'
        # )
        # # 3. 연장 시간
        # self.value_labels["extend_time"]["label"].setText(
        #     f'{self.seat_data["extend_duration"]}{self.value_labels["extend_time"]["suffix"]}'
        # )
        # # 4. 예상 종료 시간
        # self.value_labels["end_time"]["label"].setText(
        #     f'오후 {self.seat_data["new_end_time"]}'
        # )

        try:
            # 1. 좌석 정보
            if "seat_info" in self.value_labels:
                self.value_labels["seat_info"]["label"].setText(
                    f'제{self.seat_data["seat_room"]}열람실 {self.seat_data["seat_number"]}번'
                )
            # 2. 배정 일시
            if "time_info" in self.value_labels:
                self.value_labels["time_info"]["label"].setText(
                    f'오후 {self.seat_data["assigned_time_start"]} ~ 오후 {self.seat_data["assigned_time_end"]}'
                )
            # 3. 연장 시간
            if "extend_time" in self.value_labels:
                self.value_labels["extend_time"]["label"].setText(
                    f'{self.seat_data["extend_duration"]}{self.value_labels["extend_time"]["suffix"]}'
                )
            # 4. 예상 종료 시간
            if "end_time" in self.value_labels:
                self.value_labels["end_time"]["label"].setText(
                    f'오후 {self.seat_data["new_end_time"]}'
                )
        except RuntimeError:
            print("Warning: UI 업데이트 중 위젯이 삭제됨")
        except Exception as e:
            print(f"UI Update Error: {e}")

    def fetch_seat_info(self):
        """[API 연동] 서버에서 현재 사용자의 좌석 정보를 조회"""

        # 1. 세션에서 로그인한 학번 가져오기
        current_sid = UserSession.instance().get_user_id()
        
        if not current_sid:
            # 테스트 중이라 로그인을 안 거쳤다면, 경고 후 리턴 (또는 임시값 사용)
            QMessageBox.critical(self, "오류", "로그인 정보가 없습니다. 다시 로그인해주세요.")
            # self.switch_callback("main") # 메인으로 튕겨내기 가능
            return
        
        try:
            # GET /status?sid={CURRENT_USER_SID}
            response = requests.get(
                f"{API_BASE_URL}/status", 
                params={"sid": current_sid}
            )
            
            if response.status_code == 200:
                res_json = response.json()
                data_list = res_json.get("data", [])
                
                if not data_list:
                    QMessageBox.warning(self, "알림", "현재 이용 중인 좌석이 없습니다.")
                    self.extend_btn.setEnabled(False) # 연장 버튼 비활성화
                    return

                # 가장 최근 예약 정보 가져오기 (활성 예약)
                # 백엔드의 get_reservation_status는 리스트를 반환함
                reservation = data_list[0] 
                
                self.current_reservation_id = reservation['reservation_id']
                
            #     # 시간 파싱 (백엔드는 HH:MM:SS 형식 문자열 반환)
            #     start_str = reservation['start_time']
            #     end_str = reservation['end_time']
                
            #     # 표시용 데이터 업데이트
            #     self.seat_data["seat_room"] = reservation.get('room_id', '?') # room_id 매핑 필요할 수 있음
            #     self.seat_data["seat_number"] = str(reservation.get('seat_number', '?'))
            #     self.seat_data["assigned_time_start"] = start_str[:5] # HH:MM 까지만 표시
            #     self.seat_data["assigned_time_end"] = end_str[:5]
                
            #     # 연장 후 시간 계산 (3시간 더하기)
            #     # 백엔드 core_service.py의 TIME_FORMAT = '%Y-%m-%d %H:%M:%S' 고려
            #     # 하지만 status API는 현재 time 필드만 줄 수도 있으므로 주의
            #     # 여기서는 간단히 end_str(HH:MM:SS)를 파싱해서 3시간 더함
                
            #     try:
            #         end_dt = datetime.strptime(end_str, "%H:%M:%S")
            #         new_end_dt = end_dt + timedelta(hours=3)
            #         self.seat_data["new_end_time"] = new_end_dt.strftime("%H:%M")
            #     except ValueError:
            #         # 날짜가 포함된 경우 처리 ('2025-11-21 14:00:00')
            #          end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
            #          new_end_dt = end_dt + timedelta(hours=3)
            #          self.seat_data["new_end_time"] = new_end_dt.strftime("%H:%M")

            #     self.update_ui_labels()
                
            # else:
            #     print(f"Error fetching status: {response.text}")
            #     QMessageBox.critical(self, "오류", "좌석 정보를 불러오지 못했습니다.")

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
            # POST /extend
            # Body: {"reservation_id": 123, "sid": "..."}
            payload = {
                "reservation_id": self.current_reservation_id,
                "sid": current_sid
            }
            
            response = requests.post(f"{API_BASE_URL}/extend", json=payload)
            
            if response.status_code == 201:
                # 성공 시 결과 페이지로 이동
                self.switch_callback("result", mode="extend")
            
            elif response.status_code == 409:
                # 실패 (정책 위반: 시간 부족, 최대 시간 초과 등)
                error_msg = response.json().get("detail", {}).get("message", "연장할 수 없습니다.")
                QMessageBox.warning(self, "연장 실패", error_msg)
            
            else:
                # 기타 서버 에러
                QMessageBox.critical(self, "오류", f"연장 요청 실패 (Code: {response.status_code})")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"서버 통신 오류: {e}")