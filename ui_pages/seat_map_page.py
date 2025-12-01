from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QGridLayout, QSizePolicy, QSpacerItem, QFrame, QComboBox, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QMouseEvent
from ui_style import CustomAlertDialog
from .base_page import BasePage 

# 백엔드 API 연동
import requests
import sys
import os

# 세션 매니저 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
try:
    from session_manager import UserSession
except ImportError:
    print("Warning: session_manager not found")

# API 주소
API_BASE_URL = "http://34.213.241.165:8000/seat"

# [중요] 프론트엔드 room_id(숫자)와 백엔드 room_id(문자열) 매핑
ROOM_ID_MAP = {
    1: "1",         # 제1열람실
    2: "2-1",       # 제2-1열람실
    3: "2-2",       # 제2-2열람실
    4: "2-2_grad"   # 대학원생 전용
}


# ======================================================================
# 가상 DB Manager (DB 연동 모듈로 대체 필요)
# ======================================================================
class DBManager:
    def __init__(self):
        # DB 연결 초기화 코드
        pass

    def get_all_seat_statuses(self, room_id=1):
        """ [API 연동] 서버에서 예약된 좌석 정보를 가져와 상태를 설정합니다. """
        
        # 1. 서버용 room_id로 변환
        server_room_id = ROOM_ID_MAP.get(room_id, str(room_id))
        
        # 2. 전체 좌석 수 설정 (고정값 유지)
        if room_id == 1: max_seat = 380
        elif room_id == 2: max_seat = 270
        elif room_id == 3: max_seat = 176
        elif room_id == 4: max_seat = 198
        else: max_seat = 0
            
        # 기본 상태는 모두 'available'로 초기화
        all_seats = list(range(1, max_seat + 1))
        statuses = {seat_id: "available" for seat_id in all_seats}
        
        try:
            # 3. API 호출: 해당 열람실의 예약된 좌석 리스트 조회
            # GET /seat/status?room_id=...
            response = requests.get(f"{API_BASE_URL}/status", params={"room_id": server_room_id})
            
            if response.status_code == 200:
                data_list = response.json().get("data", [])
                
                # 4. 예약된 좌석들의 상태를 'reserved'로 변경
                for reservation in data_list:
                    seat_num = reservation.get("seat_number")
                    if seat_num:
                        statuses[int(seat_num)] = "reserved"
            else:
                print(f"Failed to load seats: {response.text}")

        except Exception as e:
            print(f"Network Error (Get Seats): {e}")
            
        return statuses

    # 기존 코드 주석화
    # def get_all_seat_statuses(self, room_id=1):
    #     """ 특정 열람실의 모든 좌석 상태 조회 """
    #     # 임시 데이터: 제1열람실 (room_id: 1) 및 제2-1열람실 (room_id: 2) 상태
    #     if room_id == 1:
    #         reserved_seats = [1, 2, 97, 101, 141, 142, 261, 345]
    #         all_seats = list(range(1, 380 + 1)) # 전체 좌석 ID
        
    #     elif room_id == 2:
    #         reserved_seats = [1, 5, 20, 30, 45, 60, 100, 150, 200, 250]
    #         all_seats = list(range(1, 270 + 1))

    #     elif room_id == 3:  # 제2-2열람실
    #         reserved_seats = [5, 11, 25, 33, 65, 92, 118, 140, 157, 161]
    #         all_seats = list(range(1, 176 + 1))

    #     elif room_id == 4:  # 제2-2열람실(대학원생)
    #         reserved_seats = [67, 100, 121, 130, 177, 185]
    #         all_seats = list(range(1, 198 + 1))
                
    #     else:
    #         return {}

    #     statuses = {}
    #     for seat_id in all_seats:
    #         statuses[seat_id] = "reserved" if seat_id in reserved_seats else "available"

    #     return statuses


# ----------------------------------------------------------------------
# 좌석 버튼
# ----------------------------------------------------------------------
class SeatButton(QPushButton):
    """ 좌석 버튼: ID/상태 저장 -> 클릭 시 팝업 """
    def __init__(self, seat_id, current_status="available", parent=None): 
        super().__init__(str(seat_id), parent)
        self.seat_id = seat_id
        self.current_status = current_status # DB에서 가져온 상태 저장
        self.setFixedSize(70, 60)
        self.setFont(QFont("Arial", 20))
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName(f"Seat_{seat_id}")
        self._update_style()

    def _update_style(self):
        style = """
            QPushButton {
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 3px;
                font-weight: bold;
            }
        """
        
        # 좌석 상태별 스타일
        if self.current_status == "available":
             style += "QPushButton { background-color: #161616; color: #3263ed; border-color: #3263ed; }"
        elif self.current_status == "reserved":
             style += "QPushButton { background-color: #2e2e2e; color: #7f7f7f; border-color: #2e2e2e; }" 
        else:
             style += "QPushButton { background-color: #ff9800; }" 

        self.setStyleSheet(style)
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # 팝업 연결
            self.click()


# ----------------------------------------------------------------------
# 드래그 이동 컨테이너
# ----------------------------------------------------------------------
class MovableSeatMapContainer(QWidget):
    """ 좌석 배치도 위젯 마우스 드래그로 이동시키는 기능 구현 """
    def __init__(self, inner_widget, parent=None):
        super().__init__(parent)
        self.inner_widget = inner_widget
        self.inner_widget.setParent(self)
        
        self._drag_start_pos = None
        self._initial_pos = None
        self.inner_widget.move(0, 0) 
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self._initial_pos = self.inner_widget.pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start_pos is not None:
            delta = event.pos() - self._drag_start_pos
            
            new_x = self._initial_pos.x() + delta.x()
            new_y = self._initial_pos.y() + delta.y()

            # 이동 범위 제한 (컨테이너 경계 내에서만 이동)
            max_x = self.width() - self.inner_widget.width()
            max_y = self.height() - self.inner_widget.height()
            
            new_x = max(min(new_x, 0), max_x)
            new_y = max(min(new_y, 0), max_y)

            self.inner_widget.move(new_x, new_y)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_start_pos = None
        self._initial_pos = None
        event.accept()


# ----------------------------------------------------------------------
# 열람실 배치도 페이지
# ----------------------------------------------------------------------
class BaseSeatMapPage(BasePage):
    """ 배치도 페이지 공통 로직 관리용 부모 클래스 """
    def __init__(self, switch_callback, room_name):
        super().__init__(switch_callback)
        self.room_name = room_name
        self.seat_statuses = {}
        self.db = DBManager()

    def _get_combo_box_style(self):
        """ QComboBox 스타일 반환 """
        return """
            QComboBox {
                background-color: transparent;
                color: #ffffff;
                border: 5px solid #242424;
                border-radius: 4px;
                padding: 5px 10px;
                padding-right: 35px;
                font-size: 26px;
                min-height: 40px;
            }
            QComboBox::drop-down {
                border: none; 
                background-color: transparent; 
                width: 25px; 
                subcontrol-origin: padding; 
                subcontrol-position: center right; 
            }
            QComboBox::down-arrow {
                image: url(resources/down_arrow.png); 
                width: 15px; 
                height: 15px;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a;
                color: #ffffff;
                selection-background-color: #3263ed;
            }
        """

    def _handle_room_selection(self, index):
        """ 드롭다운 선택 변경 시 해당 열람실 배치도 페이지로 전환 """
        selected_room_name = self.room_keys[index]  # 인덱스 사용해 실제 페이지 전환 키 가져옴
        
        if selected_room_name == self.room_name:
            return

        self.switch_callback("seat_map", selected_room_name)

    def _get_styled_seat_number(self, seat_id):
        """ 캐럴, 장애인석인 경우 이름 대체해 반환 """
        CARREL_START_ID = 193   # 캐럴석
        CARREL_END_ID = 198
        DISABLED_START_ID = 378 # 장애인석
        DISABLED_END_ID = 380
        
        if CARREL_START_ID <= seat_id <= CARREL_END_ID:
            carrel_num = 6 - (seat_id - CARREL_START_ID)
            display_name = f"캐럴{carrel_num}"

        elif DISABLED_START_ID <= seat_id <= DISABLED_END_ID:
            disabled_num = seat_id - DISABLED_START_ID + 1
            display_name = f"장애인{disabled_num}"
        
        else:
            display_name = str(seat_id)
        
        return f'<span style="color:#2e6cff;">{display_name}</span>'

    def _show_reservation_popup(self, seat_id):
        """ 좌석 클릭 시 팝업 띄움 """     
        styled_seat = self._get_styled_seat_number(seat_id)
        status = self.seat_statuses.get(seat_id, "unknown")
        
        if status == "available":   # 예약 가능 좌석
            title = "좌석배정"
            body = f"{self.room_name} {styled_seat}번"
            footer = ""
            buttons = [
                {'text': '닫기', 'style': 'cancel', 'callback': None},
                {'text': '배정', 'style': 'confirm', 'callback': lambda: self._process_reservation(seat_id)}
            ]
            
        elif status == "reserved":  # 예약된 좌석
            title = "이용불가좌석"
            body = f"{self.room_name} {styled_seat}번"
            footer = ""
            buttons = [{'text': '닫기', 'style': 'cancel', 'callback': None}]
            
        else: # 기타 상태
            title = "오류"
            body = "좌석 상태를 확인할 수 없습니다."
            footer = ""
            buttons = [{'text': '확인', 'style': 'confirm','callback': None}]

        info_message = {
            "title": title,
            "body": body,
            "footer": footer
        }
        
        dialog = CustomAlertDialog(info_message, self, buttons=buttons)
        dialog.exec()

    # 백엔드 API 연동
    def _process_reservation(self, seat_id):
        """ [API 연동] 좌석 예약 요청을 보냅니다. """
        
        # 1. 로그인 정보 확인
        current_sid = UserSession.instance().get_user_id()
        if not current_sid:
            CustomAlertDialog({"title": "오류", "body": "로그인 정보가 없습니다.", "footer": ""}, self).exec()
            return

        # 2. 현재 페이지의 room_id 찾기 (이름 -> ID 역매핑)
        NAME_TO_ID = {
            "제1열람실": "1",
            "제2-1열람실": "2-1",
            "제2-2열람실": "2-2",
            "제2-2열람실\n(대학원생 전용)": "2-2_grad"
        }
        server_room_id = NAME_TO_ID.get(self.room_name, "1")

        try:
            # 3. API 호출 (POST /seat/reserve)
            payload = {
                "sid": current_sid,
                "room_id": server_room_id,
                "seat_number": seat_id
            }
            
            response = requests.post(f"{API_BASE_URL}/reserve", json=payload)
            
            if response.status_code == 201:
                # 성공 시 완료 팝업 -> 메인으로 이동
                complete_message = {
                    "title": "배정완료",
                    "body": f"{self.room_name} {self._get_styled_seat_number(seat_id)}번",
                    "footer": ""
                }
                complete_buttons = [{
                    'text': '확인', 
                    'style': 'confirm', 
                    'callback': lambda: self.switch_callback("idle")
                }]
                CustomAlertDialog(complete_message, self, buttons=complete_buttons).exec()
                
            elif response.status_code == 409:
                # 이미 예약된 좌석 등 정책 위반
                error_msg = response.json().get("detail", {}).get("message", "예약할 수 없습니다.")
                CustomAlertDialog({"title": "배정실패", "body": error_msg, "footer": ""}, self).exec()
                
            else:
                CustomAlertDialog({"title": "오류", "body": "서버 오류가 발생했습니다.", "footer": ""}, self).exec()

        except Exception as e:
            print(f"Reservation Error: {e}")
            CustomAlertDialog({"title": "통신오류", "body": "서버와 연결할 수 없습니다.", "footer": ""}, self).exec()


    # 기존 코드 주석 처리
    # def _process_reservation(self, seat_id):
    #     # 실제 DB 업데이트 필요
    #     # 다음 페이지 전환
    #     complete_message = {
    #         "title": "배정완료",
    #         "body": f"{self.room_name} {self._get_styled_seat_number(seat_id)}번",
    #         "footer": ""
    #     }
    #     complete_buttons = [
    #         {
    #             'text': '확인', 
    #             'style': 'confirm', 
    #             'callback': lambda: self.switch_callback("idle")
    #         }
    #     ]
        
    #     complete_dialog = CustomAlertDialog(complete_message, self, buttons=complete_buttons)
    #     complete_dialog.exec()

    def _setup_common_ui(self, room_id):
        """ 공통 UI (프레임, 드롭다운) 설정 """
        content_layout = self.get_content_layout() 
        self.set_header_spacing(0)
        
        # 배치도 영역
        seat_map_container = QWidget()
        seat_map_container.setMinimumSize(1200, 2000)
        
        self._create_seat_map_layout(seat_map_container, self.seat_statuses) 
        
        movable_container = MovableSeatMapContainer(seat_map_container)
        
        # ------------------------------------------------
        # 테두리 프레임
        # ------------------------------------------------

        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Plain)

        VIEWPORT_WIDTH = 700
        VIEWPORT_HEIGHT = 850
        frame.setFixedSize(VIEWPORT_WIDTH, VIEWPORT_HEIGHT)

        frame.setStyleSheet("""
            QFrame {
                border: 5px solid #242424;
                border-radius: 0px;
                background-color: transparent;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.addWidget(movable_container)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        
        content_layout.addWidget(frame, 1, alignment=Qt.AlignHCenter)
        
        # ------------------------------------------------
        # 열람실 선택 드롭다운
        # ------------------------------------------------
        
        selection_container = QWidget()
        selection_vbox = QVBoxLayout(selection_container)
        selection_vbox.setContentsMargins(0, 0, 0, 0)
        selection_vbox.setSpacing(5)
        selection_vbox.setAlignment(Qt.AlignHCenter)
        
        self.room_selector = QComboBox()
        self.room_selector.setObjectName("RoomSelector")
        self.room_selector.setStyleSheet(self._get_combo_box_style()) 

        # 페이지 전환에 사용할 실제 키 목록
        self.room_keys = [
            "제1열람실", 
            "제2-1열람실", 
            "제2-2열람실", 
            "제2-2열람실\n(대학원생 전용)" # 실제 키는 \n 포함
        ]

        # 드롭다운에 표시될 텍스트 목록
        display_list = [
            "제1열람실", 
            "제2-1열람실", 
            "제2-2열람실", 
            "제2-2열람실 (대학원생 전용)"
        ]

        self.room_selector.addItems(display_list)

        # 현재 room_name에 해당하는 인덱스
        try:
            current_index = self.room_keys.index(self.room_name)
            self.room_selector.setCurrentIndex(current_index)
        except ValueError:
            pass

        current_index = self.room_selector.findText(self.room_name)
        if current_index >= 0:
            self.room_selector.setCurrentIndex(current_index)

        self.room_selector.currentIndexChanged.connect(self._handle_room_selection)
        selection_vbox.addWidget(self.room_selector, alignment=Qt.AlignHCenter)

        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch(1)
        bottom_hbox.addWidget(selection_container)
        bottom_hbox.addStretch(1)

        content_layout.addLayout(bottom_hbox)

    def _create_seat_map_layout(self, container, seat_statuses):
        """ 서브 클래스에서 구현 """
        pass

    # ----------------------------------------------------------------------
    # 배치도 생성 관련 보조 함수
    # ----------------------------------------------------------------------
    
    def _create_seat_btn(self, seat_id, click_callback, seat_statuses):
        """ 좌석 버튼 생성, 상태 전달, 클릭 이벤트 연결 """
        status = seat_statuses.get(seat_id, "unknown")
        btn = SeatButton(seat_id, current_status=status) 
        btn.clicked.connect(lambda checked, s_id=seat_id: click_callback(s_id))
        return btn
    
    def _wrap_and_center_grid(self, grid):
        """ QGridLayout을 QHBoxLayout로 감싸 중앙에 배치 """
        grid_widget = QWidget()
        grid_widget.setLayout(grid)
        
        hbox = QHBoxLayout()
        hbox.setSpacing(0)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addStretch(1)
        hbox.addWidget(grid_widget)
        hbox.addStretch(1)
        
        final_widget = QWidget()
        final_widget.setLayout(hbox)

        size_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        final_widget.setSizePolicy(size_policy)
        return final_widget

    # ----------------------------------------------------------------------
    # 톱니바퀴형 블록 생성 함수
    # ----------------------------------------------------------------------
        
    def _create_zig_zag_block_6col(self, seats_list, click_callback, seat_statuses):
        """ 2행 6열"""
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)
        
        seats_row1 = seats_list[0:6]; seats_row2 = seats_list[6:][::-1]
        for i in range(6):
            grid.addWidget(self._create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
            grid.addWidget(self._create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
        
        return self._wrap_and_center_grid(grid)
    
    def _create_zig_zag_block_4col_layout(self, seats_list, click_callback, seat_statuses):
        """ 2행 4열 """
        grid = QGridLayout() 
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0) 
        
        seats_row1, seats_row2 = seats_list[0:4], seats_list[4:]
        for i in range(4):
            grid.addWidget(self._create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
            grid.addWidget(self._create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
        return grid
    
    def _create_zig_zag_block_3col_layout(self, seats_list, click_callback, seat_statuses):
        """ 2행 3열 """
        grid = QGridLayout() 
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0) 
        
        seats_row1, seats_row2 = seats_list[0:3], seats_list[3:]
        for i in range(3):
            grid.addWidget(self._create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
            grid.addWidget(self._create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
        return grid

    def _create_zig_zag_block_3col(self, seats_list, click_callback, seat_statuses):
        """ 2행 3열 """
        grid = QGridLayout() 
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0) 
        
        seats_row1, seats_row2 = seats_list[0:3], seats_list[3:]
        for i in range(3):
            # 0이 더미 좌석 -> QPushButton 대신 QLabel 추가
            if seats_row1[i] > 0:
                grid.addWidget(self._create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
            else:
                # 더미 좌석
                empty_lbl = QLabel("")
                empty_lbl.setFixedSize(55, 55)
                grid.addWidget(empty_lbl, 0, i) 
                
            if seats_row2[i] > 0:
                grid.addWidget(self._create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
            else:
                # 더미 좌석
                empty_lbl = QLabel("")
                empty_lbl.setFixedSize(35, 30)
                grid.addWidget(empty_lbl, 1, i)
            
        return self._wrap_and_center_grid(grid)

    def _create_zig_zag_block_4col(self, seats_list, click_callback, seat_statuses):
        """ 2행 4열 """
        grid = QGridLayout() 
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)
        
        seats_row1, seats_row2 = seats_list[0:4], seats_list[4:]
        for i in range(4):
            grid.addWidget(self._create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
            grid.addWidget(self._create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
        
        return self._wrap_and_center_grid(grid)

    def _create_zig_zag_block_8col(self, seats_list, click_callback, seat_statuses):
        """ 2행 8열 """
        grid = QGridLayout() 
        grid.setSpacing(4) 
        grid.setContentsMargins(0, 0, 0, 0)
        
        seats_row1, seats_row2 = seats_list[0:8], seats_list[8:]
        for i in range(8):
            grid.addWidget(self._create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
            grid.addWidget(self._create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
        
        return self._wrap_and_center_grid(grid)
    
    def _create_zig_zag_block_9col(self, seats_list, click_callback, seat_statuses):
        """ 2행 9열 """
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)
        
        seats_row1 = seats_list[0:9]
        seats_row2 = seats_list[9:]
        
        for i in range(9):
            grid.addWidget(self._create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
            grid.addWidget(self._create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
        
        return self._wrap_and_center_grid(grid)

    def _create_wall_block_2col(self, seats_L, seats_R, click_callback, seat_statuses):
        """ N행 2열 """
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)
        
        rows = len(seats_L)
        for r in range(rows):
            grid.addWidget(self._create_seat_btn(seats_L[r], click_callback, seat_statuses), r, 0)
            grid.addWidget(self._create_seat_btn(seats_R[r], click_callback, seat_statuses), r, 1)
        
        return self._wrap_and_center_grid(grid)


# ----------------------------------------------------------------------
# 제1열람실 배치도 페이지
# ----------------------------------------------------------------------
class ReadingRoom1SeatMapPage(BaseSeatMapPage):
    def __init__(self, switch_callback, room_name=None):
        super().__init__(switch_callback, room_name if room_name else "제1열람실")
        
        self.seat_statuses = self.db.get_all_seat_statuses(room_id=1) # 제1열람실 데이터 로드
        self._setup_common_ui(room_id=1)

    def _create_seat_map_layout(self, container, seat_statuses):
        """ 제1열람실 배치도 레이아웃 구성 """
        main_vbox = QVBoxLayout(container)
        main_vbox.setSpacing(0)
        main_vbox.setContentsMargins(20, 20, 20, 20)
        
        V_GAP_SMALL = 20
        V_GAP_LARGE = 90
        
        # QGridLayout 열 위치 매핑 (구역 간격 처리)
        col_map = {
            'L': 0, 'S1': 1, 'CS': 2, 'S2': 3, 'CT': 4, 'S3': 7, 'R': 8, 'RW': 9
        }
        
        def create_side_group(seats_list, seat_statuses):
            """ 왼쪽 구역 배치 """
            vbox = QVBoxLayout()
            vbox.setSpacing(0)
            vbox.setContentsMargins(0, 0, 0, 0)
            
            vbox.addWidget(self._create_zig_zag_block_6col(seats_list[:12], self._show_reservation_popup, seat_statuses)) 
            vbox.addItem(QSpacerItem(0, V_GAP_LARGE, QSizePolicy.Fixed, QSizePolicy.Fixed)) 
            vbox.addWidget(self._create_zig_zag_block_6col(seats_list[12:], self._show_reservation_popup, seat_statuses)) 
            vbox.addStretch(1)
            
            widget = QWidget()
            widget.setLayout(vbox)
            size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            widget.setSizePolicy(size_policy)

            return widget
        
        # ----------------------------------------------------
        # 왼쪽 (1번) 구역 배치
        # ----------------------------------------------------
        seats_L_all = list(range(1, 97))
        L_blocks = [seats_L_all[i:i+24] for i in range(0, 96, 24)]
        left_section = QWidget()

        vbox_left = QVBoxLayout(left_section)
        vbox_left.setSpacing(0)
        vbox_left.setContentsMargins(0, 0, 0, 0)

        all_left_blocks = [create_side_group(L_blocks[i], seat_statuses) for i in range(4)]
        
        # 장애인석
        hbox_reserved = QHBoxLayout()
        hbox_reserved.setSpacing(10)
        
        # 장애인석 ID 할당
        disabled_seat_ids = list(range(378, 381))
        
        # 버튼 크기
        DISABLED_BTN_W = 130
        DISABLED_BTN_H = 80
        
        for i, seat_id in enumerate(disabled_seat_ids):
            current_status = seat_statuses.get(seat_id, "available")
            
            btn = SeatButton(seat_id, current_status=current_status)
            btn.setFixedSize(DISABLED_BTN_W, DISABLED_BTN_H)
            btn.setText(f"장애인{i + 1}") 
            btn.setFont(QFont("Arial", 22, QFont.Bold))
            
            # 스타일
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #ff9800; /* 노란색 배경 */
                    color: white;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 3px;
                    border: 1px solid #ff9800;
                }}
            """)
            
            btn.clicked.connect(lambda checked, s=seat_id: self._show_reservation_popup(s))
            
            hbox_reserved.addWidget(btn)
        
        # 블록 배치
        for i, widget in enumerate(all_left_blocks):
            vbox_left.addWidget(widget)
            if i < len(all_left_blocks) - 1:
                vbox_left.addItem(QSpacerItem(0, V_GAP_LARGE, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        vbox_left.addItem(QSpacerItem(0, V_GAP_LARGE, QSizePolicy.Fixed, QSizePolicy.Fixed)) 
        vbox_left.addLayout(hbox_reserved)
        vbox_left.addStretch(1) 
        
        # ----------------------------------------------------
        # 중앙 (2, 3번) 구역 배치
        # ----------------------------------------------------
        
        # 중앙 구역 좌석 리스트
        central_combined_blocks = [
            (list(range(97, 101)), list(range(137, 141))[::-1], list(range(141, 153)), 4), 
            (list(range(101, 107)), list(range(131, 137))[::-1], list(range(153, 165)), 6), 
            (list(range(107, 113)), list(range(125, 131))[::-1], list(range(165, 177)), 6), 
            (list(range(113, 119)), list(range(119, 125))[::-1], list(range(177, 189)), 6), 
        ]
        
        center_section = QWidget()
        center_layout = QGridLayout(center_section) 
        center_layout.setSpacing(0)
        center_layout.setContentsMargins(0, 0, 0, 0)

        # 3번 구역 분리
        table_section = QWidget()
        vbox_table = QVBoxLayout(table_section)
        vbox_table.setSpacing(0)
        vbox_table.setContentsMargins(0, 0, 0, 0)
        
        current_center_grid_row = 0
        
        # 상단
        for i, (seats_L, seats_R, seats_T, rows) in enumerate(central_combined_blocks):
            # 2번 구역
            center_layout.addWidget(self._create_wall_block_2col(seats_L, seats_R, self._show_reservation_popup, seat_statuses), 
                                    current_center_grid_row, col_map['CS'], rows, 1, Qt.AlignTop) 
            
            # 3번 구역
            vbox_table.addWidget(self._create_zig_zag_block_6col(seats_T, self._show_reservation_popup, seat_statuses), Qt.AlignTop)
            
            current_center_grid_row += rows
            
            # 2번 구역 간격
            if i < len(central_combined_blocks) - 1:
                center_layout.addItem(QSpacerItem(0, V_GAP_LARGE, QSizePolicy.Fixed, QSizePolicy.Fixed), current_center_grid_row, col_map['CS'], 1, 4) 
                current_center_grid_row += 1 
                
            # 3번 구역 간격
            if i < len(central_combined_blocks) - 1:
                 vbox_table.addItem(QSpacerItem(0, V_GAP_LARGE, QSizePolicy.Fixed, QSizePolicy.Fixed))
            else:
                 vbox_table.addItem(QSpacerItem(0, V_GAP_LARGE, QSizePolicy.Fixed, QSizePolicy.Fixed))

        # 하단 (3-5 ~ 3-10)
        seats_3_x_lower = {
            '3-5': list(range(189, 201)), '3-6': list(range(201, 213)),
            '3-7': list(range(213, 225)), '3-8': list(range(225, 237)),
            '3-9': list(range(237, 249)), '3-10': list(range(249, 261)),
        }
        
        seats_lower_names = list(seats_3_x_lower.keys())
        for i, (name, seats) in enumerate(seats_3_x_lower.items()):
            vbox_table.addWidget(self._create_zig_zag_block_6col(seats, self._show_reservation_popup, seat_statuses), Qt.AlignTop)
            
            if i < len(seats_lower_names) - 1:
                vbox_table.addItem(QSpacerItem(0, V_GAP_LARGE, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        vbox_table.addStretch(1) 

        center_layout.addWidget(table_section, 0, col_map['CT'], -1, 1)
        
        # 고정 수평 간격
        center_layout.addItem(
             QSpacerItem(V_GAP_LARGE, 0, QSizePolicy.Fixed, QSizePolicy.Fixed), 
             0, col_map['S2'], -1, 1
        )

        # 2번 구역 하단 공간
        center_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Fixed, QSizePolicy.Expanding), 
            current_center_grid_row, col_map['CS'], 1, 1
        )
        
        # ----------------------------------------------------
        # 오른쪽 (4, 5번) 구역 배치
        # ----------------------------------------------------
        
        right_section = QWidget()
        vbox_right = QVBoxLayout(right_section)
        vbox_right.setSpacing(0)
        vbox_right.setContentsMargins(0, 0, 0, 0)
        
        # 4번 구역 좌석 리스트
        q_groups = [
             ([261, 262, 263, 264, 274, 273, 272, 271], [265, 266, 267, 270, 269, 268]),
             ([275, 276, 277, 278, 288, 287, 286, 285], [279, 280, 281, 284, 283, 282]),
             ([289, 290, 291, 292, 302, 301, 300, 299], [293, 294, 295, 298, 297, 296]),
             ([303, 304, 305, 306, 316, 315, 314, 313], [307, 308, 309, 312, 311, 310]),
             ([317, 318, 319, 320, 330, 329, 328, 327], [321, 322, 323, 326, 325, 324]),
             ([331, 332, 333, 334, 344, 343, 342, 341], [335, 336, 337, 340, 339, 338]),
        ]
        
        q_groups_count = len(q_groups)
        
        # 4번 구역
        for i, (seats_odd, seats_even) in enumerate(q_groups):
            hbox_row = QHBoxLayout()
            hbox_row.setSpacing(V_GAP_LARGE) 
            
            hbox_row.addLayout(self._create_zig_zag_block_4col_layout(seats_odd, self._show_reservation_popup, seat_statuses))
            hbox_row.addLayout(self._create_zig_zag_block_3col_layout(seats_even, self._show_reservation_popup, seat_statuses))
            
            vbox_right.addLayout(hbox_row)
            
            if i < q_groups_count - 1:
                vbox_right.addItem(QSpacerItem(0, V_GAP_LARGE, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        # 5번 구역
        vbox_right.addItem(QSpacerItem(0, V_GAP_LARGE, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        seats_5_1_ordered = list(range(345, 353)) + list(range(353, 361))[::-1]
        seats_5_2_ordered = list(range(361, 369)) + list(range(369, 377))[::-1]
        
        vbox_right.addWidget(self._create_zig_zag_block_8col(seats_5_1_ordered, self._show_reservation_popup, seat_statuses))
        vbox_right.addItem(QSpacerItem(0, V_GAP_LARGE, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        vbox_right.addWidget(self._create_zig_zag_block_8col(seats_5_2_ordered, self._show_reservation_popup, seat_statuses))
        vbox_right.addStretch(1) 

        # 최종 레이아웃 배치 (왼쪽 | 중앙 | 오른쪽)
        final_hbox = QHBoxLayout()
        final_hbox.setSpacing(V_GAP_LARGE) 
        final_hbox.addWidget(left_section, 0) 
        final_hbox.addWidget(center_section, 0) 
        final_hbox.addWidget(right_section, 1)
        final_hbox.addStretch(1)
        
        main_vbox.addLayout(final_hbox)
        main_vbox.addStretch(1)


# ----------------------------------------------------------------------
# 제2-1열람실 배치도 페이지
# ----------------------------------------------------------------------
class ReadingRoom2_1SeatMapPage(BaseSeatMapPage):
    def __init__(self, switch_callback, room_name=None):
        super().__init__(switch_callback, room_name if room_name else "제2-1열람실")
        
        self.seat_statuses = self.db.get_all_seat_statuses(room_id=2) # 제2-1열람실 데이터 로드
        self._setup_common_ui(room_id=2)

    def _create_seat_map_layout(self, container, seat_statuses):
        """ 제2-1열람실 배치도 레이아웃 구성 """
        main_vbox = QVBoxLayout(container)
        main_vbox.setSpacing(0)
        main_vbox.setContentsMargins(20, 20, 20, 20)
        
        V_GAP_SMALL = 20
        V_GAP_LARGE = 90
        
        # ----------------------------------------------------
        # 왼쪽 (1번) 구역
        # ----------------------------------------------------

        # 1-1 구역
        block_1_1_container = QWidget()
        vbox_1_1 = QVBoxLayout(block_1_1_container)
        vbox_1_1.setSpacing(0)
        vbox_1_1.setContentsMargins(0, 0, 0, 0)

        # 상단
        seats_1_1_A_L = list(range(1, 15))      
        seats_1_1_A_R = list(range(36, 22, -1))
        block_1_1_A = self._create_wall_block_2col(seats_1_1_A_L, seats_1_1_A_R, self._show_reservation_popup, seat_statuses)
        vbox_1_1.addWidget(block_1_1_A)
        vbox_1_1.addSpacing(V_GAP_LARGE)
        
        # 하단
        seats_1_1_B_L = list(range(15, 19))
        seats_1_1_B_R = list(range(22, 18, -1))
        block_1_1_B = self._create_wall_block_2col(seats_1_1_B_L, seats_1_1_B_R, self._show_reservation_popup, seat_statuses)
        vbox_1_1.addWidget(block_1_1_B)
        
        # 1-2 구역
        block_1_2_container = QWidget()
        vbox_1_2 = QVBoxLayout(block_1_2_container)
        vbox_1_2.setSpacing(0)
        vbox_1_2.setContentsMargins(0, 0, 0, 0)
        
        # 상단
        seats_1_2_A_L = list(range(37, 51))
        seats_1_2_A_R = list(range(72, 58, -1))
        block_1_2_A = self._create_wall_block_2col(seats_1_2_A_L, seats_1_2_A_R, self._show_reservation_popup, seat_statuses)
        vbox_1_2.addWidget(block_1_2_A)
        vbox_1_2.addSpacing(V_GAP_LARGE)

        # 하단
        seats_1_2_B_L = list(range(51, 55))
        seats_1_2_B_R = list(range(58, 54, -1))
        block_1_2_B = self._create_wall_block_2col(seats_1_2_B_L, seats_1_2_B_R, self._show_reservation_popup, seat_statuses)
        vbox_1_2.addWidget(block_1_2_B)

        # 배치
        left_section_h_container = QWidget()
        left_section_h_layout = QHBoxLayout(left_section_h_container)
        left_section_h_layout.setContentsMargins(0, 0, 0, 0)
        left_section_h_layout.setSpacing(V_GAP_LARGE)
        
        left_section_h_layout.addWidget(block_1_1_container)
        left_section_h_layout.addWidget(block_1_2_container)

        left_section = QWidget()
        vbox_left = QVBoxLayout(left_section)
        vbox_left.setContentsMargins(0, 0, 0, 0)
        vbox_left.addWidget(left_section_h_container)
        vbox_left.addStretch(1) 
        
        # ----------------------------------------------------
        # 중앙 (2, 3번) 구역
        # ----------------------------------------------------
        
        center_section = QWidget()
        hbox_center = QHBoxLayout(center_section) 
        hbox_center.setSpacing(V_GAP_LARGE) # 구역 간 수평 간격
        hbox_center.setContentsMargins(0, 0, 0, 0)
        
        # 2번 구역
        block_2_1_container = QWidget()
        vbox_2_1 = QVBoxLayout(block_2_1_container)
        vbox_2_1.setSpacing(0) 
        vbox_2_1.setContentsMargins(0, 0, 0, 0)
        
        # 상단
        seats_2_1_A_L = list(range(73, 81))       
        seats_2_1_A_R = list(range(102, 94, -1))  
        block_2_1_A = self._create_wall_block_2col(seats_2_1_A_L, seats_2_1_A_R, self._show_reservation_popup, seat_statuses)
        vbox_2_1.addWidget(block_2_1_A)
        vbox_2_1.addSpacing(V_GAP_LARGE) 

        # 하단
        seats_2_1_B_L = list(range(81, 88))       
        seats_2_1_B_R = list(range(94, 87, -1))   
        block_2_1_B = self._create_wall_block_2col(seats_2_1_B_L, seats_2_1_B_R, self._show_reservation_popup, seat_statuses)
        vbox_2_1.addWidget(block_2_1_B)
        vbox_2_1.addStretch(1) 

        # 3-1 구역
        block_3_1_container = QWidget()
        vbox_3_1 = QVBoxLayout(block_3_1_container)
        vbox_3_1.setSpacing(0)
        vbox_3_1.setContentsMargins(0, 0, 0, 0)

        # 상단
        seats_3_1_A_L = list(range(103, 117))
        seats_3_1_A_R = list(range(140, 126, -1))
        block_3_1_A = self._create_wall_block_2col(seats_3_1_A_L, seats_3_1_A_R, self._show_reservation_popup, seat_statuses)
        vbox_3_1.addWidget(block_3_1_A)
        vbox_3_1.addSpacing(V_GAP_LARGE) 
        
        # 하단
        seats_3_1_B_L = list(range(117, 122))
        seats_3_1_B_R = list(range(126, 121, -1))
        block_3_1_B = self._create_wall_block_2col(seats_3_1_B_L, seats_3_1_B_R, self._show_reservation_popup, seat_statuses)
        vbox_3_1.addWidget(block_3_1_B)
        vbox_3_1.addStretch(1)
        
        # 3-2 구역
        block_3_2_container = QWidget()
        vbox_3_2 = QVBoxLayout(block_3_2_container)
        vbox_3_2.setSpacing(0)
        vbox_3_2.setContentsMargins(0, 0, 0, 0)

        # 상단
        seats_3_2_A_L = list(range(141, 155))
        seats_3_2_A_R = list(range(178, 164, -1))
        block_3_2_A = self._create_wall_block_2col(seats_3_2_A_L, seats_3_2_A_R, self._show_reservation_popup, seat_statuses)
        vbox_3_2.addWidget(block_3_2_A)
        vbox_3_2.addSpacing(V_GAP_LARGE) 

        # 하단
        seats_3_2_B_L = list(range(155, 160))
        seats_3_2_B_R = list(range(164, 159, -1))
        block_3_2_B = self._create_wall_block_2col(seats_3_2_B_L, seats_3_2_B_R, self._show_reservation_popup, seat_statuses)
        vbox_3_2.addWidget(block_3_2_B)
        vbox_3_2.addStretch(1)

        # 배치
        hbox_center.addWidget(block_2_1_container)
        hbox_center.addWidget(block_3_1_container)
        hbox_center.addWidget(block_3_2_container)
        
        # ----------------------------------------------------
        # 오른쪽 (4, 5, 6번) 구역
        # ----------------------------------------------------
        
        right_section = QWidget()
        vbox_right = QVBoxLayout(right_section)
        vbox_right.setSpacing(V_GAP_LARGE) # 구역 간 수직 간격
        vbox_right.setContentsMargins(0, 0, 0, 0)

        # 4번 구역
        grid_4_1 = QGridLayout()
        seats_4_1 = list(range(179, 185)) 
        for i, seat_id in enumerate(seats_4_1):
            grid_4_1.addWidget(self._create_seat_btn(seat_id, self._show_reservation_popup, seat_statuses), 0, i)
        vbox_right.addWidget(self._wrap_and_center_grid(grid_4_1))

        # 5-1 구역
        seats_5_1_row1 = list(range(192, 184, -1)) 
        seats_5_1_row2 = list(range(193, 201)) 
        vbox_right.addWidget(self._create_zig_zag_block_8col(seats_5_1_row1 + seats_5_1_row2, self._show_reservation_popup, seat_statuses))
        
        # 5-2 구역
        seats_5_2_row1 = list(range(208, 200, -1)) 
        seats_5_2_row2 = list(range(209, 217)) 
        vbox_right.addWidget(self._create_zig_zag_block_8col(seats_5_2_row1 + seats_5_2_row2, self._show_reservation_popup, seat_statuses))

        # 5-3 구역
        seats_5_3_row1 = list(range(224, 216, -1)) 
        seats_5_3_row2 = list(range(225, 233)) 
        vbox_right.addWidget(self._create_zig_zag_block_8col(seats_5_3_row1 + seats_5_3_row2, self._show_reservation_popup, seat_statuses))

        # 5-4 구역
        seats_5_4_row1 = list(range(240, 232, -1)) 
        seats_5_4_row2 = list(range(241, 249)) 
        vbox_right.addWidget(self._create_zig_zag_block_8col(seats_5_4_row1 + seats_5_4_row2, self._show_reservation_popup, seat_statuses))

        # 5-5 구역
        seats_5_5_row1 = list(range(256, 248, -1)) 
        seats_5_5_row2 = list(range(257, 265)) 
        vbox_right.addWidget(self._create_zig_zag_block_8col(seats_5_5_row1 + seats_5_5_row2, self._show_reservation_popup, seat_statuses))

        # 6번 구역
        grid_6_1 = QGridLayout()
        seats_6_1 = list(range(270, 264, -1)) 
        for i, seat_id in enumerate(seats_6_1):
            grid_6_1.addWidget(self._create_seat_btn(seat_id, self._show_reservation_popup, seat_statuses), 0, i)
        vbox_right.addWidget(self._wrap_and_center_grid(grid_6_1))
        vbox_right.addStretch(1)
        
        # ----------------------------------------------------
        # 최종 레이아웃 배치
        # ----------------------------------------------------
        
        final_hbox = QHBoxLayout()
        final_hbox.setSpacing(V_GAP_LARGE) 
        final_hbox.addWidget(left_section, 0) 
        final_hbox.addWidget(center_section, 0)
        final_hbox.addWidget(right_section, 1)
        final_hbox.addStretch(1)
        
        main_vbox.addLayout(final_hbox)
        main_vbox.addStretch(1)


# ----------------------------------------------------------------------
# 제2-2열람실 배치도 페이지
# ----------------------------------------------------------------------
class ReadingRoom2_2SeatMapPage(BaseSeatMapPage):
    def __init__(self, switch_callback, room_name=None):
        super().__init__(switch_callback, room_name if room_name else "제2-2열람실")
        
        self.seat_statuses = self.db.get_all_seat_statuses(room_id=3) # 제2-2열람실 데이터 로드
        self._setup_common_ui(room_id=3)

    def _create_seat_map_layout(self, container, seat_statuses):
        """ 제2-2열람실 배치도 레이아웃 구성 """
        main_vbox = QVBoxLayout(container)
        main_vbox.setSpacing(0)
        main_vbox.setContentsMargins(20, 20, 20, 20)
        
        V_GAP_SMALL = 20
        V_GAP_LARGE = 90 
        
        # ----------------------------------------------------
        # 1번 구역
        # ----------------------------------------------------

        block_1_1_container = QWidget()
        block_1_1_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        vbox_1_1_main = QVBoxLayout(block_1_1_container)
        vbox_1_1_main.setSpacing(V_GAP_LARGE)
        vbox_1_1_main.setContentsMargins(0, 0, 0, 0)
        
        # 상단
        seats_1_1_A1_L = list(range(1, 3))     
        seats_1_1_A1_R = list(range(28, 26, -1)) 
        block_1_1_A_top1 = self._create_wall_block_2col(seats_1_1_A1_L, seats_1_1_A1_R, self._show_reservation_popup, seat_statuses)
        vbox_1_1_main.addWidget(block_1_1_A_top1)
        
        # 중간
        seats_1_1_A2_L = list(range(3, 7))
        seats_1_1_A2_R = list(range(26, 22, -1))
        block_1_1_A_top2 = self._create_wall_block_2col(seats_1_1_A2_L, seats_1_1_A2_R, self._show_reservation_popup, seat_statuses)
        vbox_1_1_main.addWidget(block_1_1_A_top2)

        # 하단 시작점 위치 조정
        HEIGHT_ADJUSTMENT = 136
        vbox_1_1_main.addItem(QSpacerItem(0, HEIGHT_ADJUSTMENT, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        # 하단
        seats_1_1_B_L = list(range(7, 15))
        seats_1_1_B_R = list(range(22, 14, -1))
        block_1_1_A_bottom = self._create_wall_block_2col(seats_1_1_B_L, seats_1_1_B_R, self._show_reservation_popup, seat_statuses)
        vbox_1_1_main.addWidget(block_1_1_A_bottom)
        vbox_1_1_main.addStretch(1)

        # ----------------------------------------------------
        # 2번 구역
        # ----------------------------------------------------

        block_2_x_container = QWidget()
        block_2_x_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        vbox_2_x = QVBoxLayout(block_2_x_container)
        vbox_2_x.setSpacing(V_GAP_LARGE)
        vbox_2_x.setContentsMargins(0, 0, 0, 0)
        
        # 상단
        seats_2_1_A_L = list(range(29, 31))
        seats_2_1_A_R = list(range(60, 58, -1))
        block_2_1_A = self._create_wall_block_2col(seats_2_1_A_L, seats_2_1_A_R, self._show_reservation_popup, seat_statuses)
        vbox_2_x.addWidget(block_2_1_A)

        # 중간
        seats_2_1_B_L = list(range(31, 37))
        seats_2_1_B_R = list(range(58, 52, -1))
        block_2_1_B = self._create_wall_block_2col(seats_2_1_B_L, seats_2_1_B_R, self._show_reservation_popup, seat_statuses)
        vbox_2_x.addWidget(block_2_1_B)

        # 하단
        seats_2_2_L = list(range(37, 45))
        seats_2_2_R = list(range(52, 44, -1)) 
        block_2_2 = self._create_wall_block_2col(seats_2_2_L, seats_2_2_R, self._show_reservation_popup, seat_statuses)
        vbox_2_x.addWidget(block_2_2)
        vbox_2_x.addStretch(1)

        # ----------------------------------------------------
        # 3번 구역
        # ----------------------------------------------------

        block_3_x_container = QWidget()
        block_3_x_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        vbox_3_x = QVBoxLayout(block_3_x_container)
        vbox_3_x.setSpacing(V_GAP_LARGE)
        vbox_3_x.setContentsMargins(0, 0, 0, 0)
        
        # 상단
        seats_3_1_A_L = list(range(61, 63))
        seats_3_1_A_R = list(range(84, 82, -1))
        block_3_1_A = self._create_wall_block_2col(seats_3_1_A_L, seats_3_1_A_R, self._show_reservation_popup, seat_statuses)
        vbox_3_x.addWidget(block_3_1_A)
        
        # 하단
        seats_3_1_B_L = list(range(63, 67))
        seats_3_1_B_R = list(range(82, 78, -1))
        block_3_1_B = self._create_wall_block_2col(seats_3_1_B_L, seats_3_1_B_R, self._show_reservation_popup, seat_statuses)
        vbox_3_x.addWidget(block_3_1_B)
        vbox_3_x.addStretch(1)
        
        # ----------------------------------------------------
        # 4번 구역
        # ----------------------------------------------------

        block_4_x_container = QWidget()
        block_4_x_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        hbox_4_x = QHBoxLayout(block_4_x_container) 
        hbox_4_x.setSpacing(V_GAP_LARGE)
        hbox_4_x.setContentsMargins(0, 0, 0, 0)
        
        # 4-1
        block_4_1_container = QWidget()
        vbox_4_1 = QVBoxLayout(block_4_1_container)
        vbox_4_1.setSpacing(0)
        vbox_4_1.setContentsMargins(0, 0, 0, 0)
        
        # 상단
        seats_4_1_A_L = list(range(85, 87))
        seats_4_1_A_R = list(range(112, 110, -1))
        block_4_1_A = self._create_wall_block_2col(seats_4_1_A_L, seats_4_1_A_R, self._show_reservation_popup, seat_statuses)
        vbox_4_1.addWidget(block_4_1_A)
        vbox_4_1.addSpacing(V_GAP_LARGE) 
        
        # 하단
        seats_4_1_B_L = list(range(87, 93))
        seats_4_1_B_R = list(range(110, 104, -1))
        block_4_1_B = self._create_wall_block_2col(seats_4_1_B_L, seats_4_1_B_R, self._show_reservation_popup, seat_statuses)
        vbox_4_1.addWidget(block_4_1_B)
        vbox_4_1.addStretch(1)
        hbox_4_x.addWidget(block_4_1_container)
        
        # 4-2
        block_4_2_container = QWidget()
        vbox_4_2 = QVBoxLayout(block_4_2_container)
        vbox_4_2.setSpacing(0)
        vbox_4_2.setContentsMargins(0, 0, 0, 0)

        # 상단
        seats_4_2_A_L = list(range(113, 115))
        seats_4_2_A_R = list(range(144, 142, -1))
        block_4_2_A = self._create_wall_block_2col(seats_4_2_A_L, seats_4_2_A_R, self._show_reservation_popup, seat_statuses)
        vbox_4_2.addWidget(block_4_2_A)
        vbox_4_2.addSpacing(V_GAP_LARGE) 
        
        # 하단
        seats_4_2_B_L = list(range(115, 121))
        seats_4_2_B_R = list(range(142, 136, -1))
        block_4_2_B = self._create_wall_block_2col(seats_4_2_B_L, seats_4_2_B_R, self._show_reservation_popup, seat_statuses)
        vbox_4_2.addWidget(block_4_2_B)
        vbox_4_2.addStretch(1) 
        hbox_4_x.addWidget(block_4_2_container)
        
        # ----------------------------------------------------
        # 5번 구역
        # ----------------------------------------------------

        block_5_x_container = QWidget()
        vbox_5_x = QVBoxLayout(block_5_x_container)
        vbox_5_x.setSpacing(0)
        vbox_5_x.setContentsMargins(0, 0, 0, 0)
        
        # 5-1
        seats_5_1_row1 = list(range(145, 153))
        seats_5_1_row2 = list(range(160, 152, -1))
        block_5_1 = self._create_zig_zag_block_8col(seats_5_1_row1 + seats_5_1_row2, self._show_reservation_popup, seat_statuses)
        vbox_5_x.addWidget(block_5_1)
        vbox_5_x.addSpacing(V_GAP_LARGE)

        # 5-2
        seats_5_2_row1 = list(range(161, 169))
        seats_5_2_row2 = list(range(176, 168, -1)) 
        block_5_2 = self._create_zig_zag_block_8col(seats_5_2_row1 + seats_5_2_row2, self._show_reservation_popup, seat_statuses)
        vbox_5_x.addWidget(block_5_2)
        vbox_5_x.addStretch(1)

        # ----------------------------------------------------
        # 최종 레이아웃 배치
        # ----------------------------------------------------

        top_h_container = QWidget()
        top_hbox = QHBoxLayout(top_h_container)
        top_hbox.setSpacing(V_GAP_LARGE)    # 구역 간 수평 간격
        top_hbox.setContentsMargins(0, 0, 0, 0)
        
        top_hbox.addWidget(block_1_1_container) 
        top_hbox.addWidget(block_2_x_container) 
        top_hbox.addWidget(block_3_x_container)
        top_hbox.addWidget(block_4_x_container)
        top_hbox.addWidget(block_5_x_container)
        
        main_vbox.addWidget(top_h_container)
        main_vbox.addStretch(1)


# ----------------------------------------------------------------------
# 제2-2열람실 (대학원생 전용) 배치도 페이지
# ----------------------------------------------------------------------
class ReadingRoom2_2GradSeatMapPage(BaseSeatMapPage):
    def __init__(self, switch_callback, room_name=None):
        grad_room_name = "제2-2열람실\n(대학원생 전용)"
        super().__init__(switch_callback, room_name if room_name else grad_room_name)

        self.seat_statuses = self.db.get_all_seat_statuses(room_id=4) # room_id=4 로드
        self._setup_common_ui(room_id=4)

    # BaseSeatMapPage 의 _show_reservation_popup 메서드 오버라이딩
    def _show_reservation_popup(self, seat_id):
        styled_seat = self._get_styled_seat_number(seat_id)
        status = self.seat_statuses.get(seat_id, "unknown")

        room_name_base = "제2-2열람실"
        room_name_spec = "(대학원생 전용)"

        if status == 'available':
            title = "좌석배정"
            body = f"{room_name_base}<br>{room_name_spec}<br>{styled_seat}번"
            footer = ""
            buttons = [
                {'text': '닫기', 'style': 'cancel', 'callback': None},
                {'text': '배정', 'style': 'confirm', 'callback': lambda: self._process_reservation(seat_id)}
            ]
            
        elif status == "reserved":
            title = "이용불가좌석"
            body = f"{room_name_base}<br>{room_name_spec}<br>{styled_seat}번"
            footer = ""
            buttons = [{'text': '닫기', 'style': 'cancel', 'callback': None}]
            
        else:
            title = "오류"
            body = "좌석 상태를 확인할 수 없습니다."
            footer = ""
            buttons = [{'text': '확인', 'style': 'confirm','callback': None}]

        info_message = {
            "title": title,
            "body": body,
            "footer": footer
        }

        dialog = CustomAlertDialog(info_message, self, buttons=buttons) 
        dialog.exec()

    # 백엔드 API 연동
    # [수정] 대학원생 열람실 전용 예약 처리 (API 연동 추가)
    def _process_reservation(self, seat_id):
        """ [API 연동] 좌석 예약 요청 (대학원생 전용) """
        
        # 1. 로그인 정보 확인
        current_sid = UserSession.instance().get_user_id()
        if not current_sid:
            CustomAlertDialog({"title": "오류", "body": "로그인 정보가 없습니다.", "footer": ""}, self).exec()
            return

        # 2. room_id 설정 (대학원생실 고정 ID)
        server_room_id = "2-2_grad"

        try:
            # 3. API 호출 (POST /seat/reserve)
            payload = {
                "sid": current_sid,
                "room_id": server_room_id,
                "seat_number": seat_id
            }
            
            response = requests.post(f"{API_BASE_URL}/reserve", json=payload)
            
            if response.status_code == 201:
                # 4. 성공 시 완료 팝업 (대학원생 전용 메시지 포맷 유지)
                styled_seat = self._get_styled_seat_number(seat_id)
                room_name_base = "제2-2열람실"
                room_name_spec = "(대학원생 전용)"

                complete_message = {
                    "title": "배정완료",
                    "body": f"{room_name_base}<br>{room_name_spec}<br>{styled_seat}번",
                    "footer": ""
                }
                complete_buttons = [{
                    'text': '확인', 
                    'style': 'confirm', 
                    'callback': lambda: self.switch_callback("idle")
                }]
                CustomAlertDialog(complete_message, self, buttons=complete_buttons).exec()
                
            elif response.status_code == 409:
                # 실패 처리
                error_msg = response.json().get("detail", {}).get("message", "예약할 수 없습니다.")
                CustomAlertDialog({"title": "배정실패", "body": error_msg, "footer": ""}, self).exec()
            else:
                CustomAlertDialog({"title": "오류", "body": "서버 오류가 발생했습니다.", "footer": ""}, self).exec()

        except Exception as e:
            print(f"Reservation Error: {e}")
            CustomAlertDialog({"title": "통신오류", "body": "서버와 연결할 수 없습니다.", "footer": ""}, self).exec()

    # 기존 코드 주석 처리
    # 오버라이딩
    # def _process_reservation(self, seat_id):
    #     # 실제 DB 업데이트 필요
    #     # 다음 페이지 전환

    #     styled_seat = self._get_styled_seat_number(seat_id)

    #     room_name_base = "제2-2열람실"
    #     room_name_spec = "(대학원생 전용)"

    #     complete_message = {
    #         "title": "배정완료",
    #         "body": f"{room_name_base}<br>{room_name_spec}<br>{styled_seat}번",
    #         "footer": ""
    #     }
    #     complete_buttons = [
    #         {
    #             'text': '확인', 
    #             'style': 'confirm', 
    #             'callback': lambda: self.switch_callback("idle")
    #         }
    #     ]
        
    #     complete_dialog = CustomAlertDialog(complete_message, self, buttons=complete_buttons)
    #     complete_dialog.exec()

    def _create_seat_map_layout(self, container, seat_statuses):
        main_vbox = QVBoxLayout(container)
        main_vbox.setSpacing(0)
        main_vbox.setContentsMargins(20, 20, 20, 20)
        
        V_GAP_SMALL = 20
        V_GAP_LARGE = 90
        
        # ----------------------------------------------------
        # 메인 수평 컨테이너 (1번 | 2번 | 캐럴)
        # ----------------------------------------------------
        
        main_h_container = QWidget()
        main_hbox = QHBoxLayout(main_h_container)
        main_hbox.setSpacing(V_GAP_LARGE)
        main_hbox.setContentsMargins(0, 0, 0, 0)
        
        # 캐럴 구역
        carrel_container = QWidget()
        vbox_carrel = QVBoxLayout(carrel_container)
        vbox_carrel.setSpacing(V_GAP_SMALL)
        vbox_carrel.setContentsMargins(0, 0, 0, 0)
        
        # 캐럴 좌석 ID 할당
        carrel_seat_ids = list(range(193, 199)) 
        
        # 캐럴 버튼 크기
        CARREL_BTN_W = 120
        CARREL_BTN_H = 80
        
        # 캐럴 버튼 생성 및 이벤트 연결
        for i, seat_id in enumerate(carrel_seat_ids):
            current_status = seat_statuses.get(seat_id, "available")
            
            btn = SeatButton(seat_id, current_status=current_status)
            btn.setFixedSize(CARREL_BTN_W, CARREL_BTN_H)
            btn.setText(f"캐럴{6 - i}") 
            btn.setFont(QFont("Arial", 22, QFont.Bold))
            btn.clicked.connect(lambda checked, s=seat_id: self._show_reservation_popup(s))

            vbox_carrel.addWidget(btn)

        vbox_carrel.addStretch(1)
        
        # 1, 2번 구역
        seat_blocks_container = QWidget()
        seat_blocks_hbox = QHBoxLayout(seat_blocks_container)
        seat_blocks_hbox.setSpacing(V_GAP_LARGE)
        seat_blocks_hbox.setContentsMargins(0, 0, 0, 0)
        
        # 1-1
        seats_1_1_L = list(range(67, 73))
        seats_1_1_R = list(range(78, 72, -1))
        block_1_1 = self._create_wall_block_2col(seats_1_1_L, seats_1_1_R, self._show_reservation_popup, seat_statuses)
        
        # 1-2
        seats_1_2_L = list(range(93, 99))
        seats_1_2_R = list(range(104, 98, -1))
        block_1_2 = self._create_wall_block_2col(seats_1_2_L, seats_1_2_R, self._show_reservation_popup, seat_statuses)

        # 2-1
        seats_2_1_L = list(range(121, 129))
        seats_2_1_R = list(range(136, 128, -1))
        block_2_1 = self._create_wall_block_2col(seats_2_1_L, seats_2_1_R, self._show_reservation_popup, seat_statuses)

        # 2-2
        seats_2_2_L = list(range(177, 185))
        seats_2_2_R = list(range(192, 184, -1))
        block_2_2 = self._create_wall_block_2col(seats_2_2_L, seats_2_2_R, self._show_reservation_popup, seat_statuses)
        
        seat_blocks_hbox.addWidget(block_1_1, alignment=Qt.AlignTop)
        seat_blocks_hbox.addWidget(block_1_2, alignment=Qt.AlignTop)
        
        seat_blocks_hbox.addWidget(block_2_1, alignment=Qt.AlignTop)
        seat_blocks_hbox.addWidget(block_2_2, alignment=Qt.AlignTop)
        seat_blocks_hbox.addStretch(1) 
        
        # 1번 | 2번 | 캐럴
        main_hbox.addWidget(seat_blocks_container)
        main_hbox.addWidget(carrel_container, alignment=Qt.AlignTop) 
        main_hbox.addStretch(1)

        # ----------------------------------------------------
        # 최종 레이아웃 배치
        # ----------------------------------------------------
        
        main_vbox.addWidget(main_h_container)
        main_vbox.addStretch(1)
