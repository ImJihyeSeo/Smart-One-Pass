from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QGridLayout, QSizePolicy, QSpacerItem, QFrame, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QMouseEvent
from ui_style import CustomAlertDialog
from .base_page import BasePage 


# ======================================================================
# 가상 DB Manager (DB 연동 모듈로 대체 필요)
# ======================================================================
class DBManager:
    def __init__(self):
        # DB 연결 초기화 코드
        pass

    def get_all_seat_statuses(self, room_id=1):
        """ 특정 열람실의 모든 좌석 상태 조회 """
        # 임시 데이터: 제1열람실 (room_id: 1) 및 제2-1열람실 (room_id: 2) 상태
        if room_id == 1:
            reserved_seats = [1, 2, 97, 101, 141, 142, 261, 345]
            all_seats = list(range(1, 377 + 1)) # 전체 좌석 ID
        
        elif room_id == 2:
            reserved_seats = [1, 5, 20, 30, 45, 60, 100, 150, 200, 250]
            all_seats = list(range(1, 270 + 1))
        
        else:
            return {}

        statuses = {}
        for seat_id in all_seats:
            statuses[seat_id] = "reserved" if seat_id in reserved_seats else "available"

        return statuses


# ----------------------------------------------------------------------
# 좌석 버튼
# ----------------------------------------------------------------------
class SeatButton(QPushButton):
    """ 좌석 버튼: ID/상태 저장 -> 클릭 시 팝업 """
    def __init__(self, seat_id, current_status="available", parent=None): 
        super().__init__(str(seat_id), parent)
        self.seat_id = seat_id
        self.current_status = current_status # DB에서 가져온 상태 저장
        self.setFixedSize(35, 30)
        self.setFont(QFont("Arial", 8))
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
        
        self.inner_widget.setMinimumSize(self.inner_widget.sizeHint())
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
class ReadingRoom1SeatMapPage(BasePage):
    def __init__(self, switch_callback, room_name=None):
        super().__init__(switch_callback)
        self.room_name = room_name if room_name else "제1열람실"
        
        self.db = DBManager()
        
        self.seat_statuses = self.db.get_all_seat_statuses(room_id=1)   # 지금은 제1열람실 데이터만 로드 (room_id=1)

        content_layout = self.get_content_layout() 
        self.set_header_spacing(0)
        
        # 배치도 영역
        seat_map_container = QWidget()
        self._create_seat_map_layout(seat_map_container, self.seat_statuses) 
        
        movable_container = MovableSeatMapContainer(seat_map_container)
        
        # 테두리 프레임
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Plain)
        frame.setMaximumHeight(500)
        frame.setMaximumWidth(500)
        frame.setStyleSheet("""
            QFrame {
                border: 1px solid #1a1a1a;
                border-radius: 0px;
                background-color: transparent;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.addWidget(movable_container)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        
        content_layout.addWidget(frame, 1)
        
        # ------------------------------------------------
        # 열람실 선택 드롭다운
        # ------------------------------------------------
        
        # 중앙 정렬 위한 컨테이너
        selection_container = QWidget()
        selection_vbox = QVBoxLayout(selection_container)
        selection_vbox.setContentsMargins(0, 0, 0, 0)
        selection_vbox.setSpacing(5)
        selection_vbox.setAlignment(Qt.AlignHCenter)
        
        self.room_selector = QComboBox()
        self.room_selector.setObjectName("RoomSelector")
        self.room_selector.setStyleSheet("""
            QComboBox {
                background-color: transparent;
                color: #ffffff;
                border: 1px solid #1a1a1a;
                border-radius: 4px;
                padding: 5px 10px;
                padding-right: 35px; /* 화살표 공간 */
                font-size: 16px;
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
                background-color: #000000;
                color: #ffffff;
                selection-background-color: #3263ed;
            }
        """)

        # 열람실 목록 / 현재 페이지 설정
        room_list = ["제1열람실", "제2-1열람실", "제2-2열람실", "제2-3열람실(대학원생 전용)"]
        self.room_selector.addItems(room_list)
        current_index = self.room_selector.findText(self.room_name)
        if current_index >= 0:
            self.room_selector.setCurrentIndex(current_index)

        # 페이지 전환
        self.room_selector.currentIndexChanged.connect(self._handle_room_selection)
        selection_vbox.addWidget(self.room_selector, alignment=Qt.AlignHCenter)

        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch(1)
        bottom_hbox.addWidget(selection_container)
        bottom_hbox.addStretch(1)

        content_layout.addLayout(bottom_hbox)
    
    # ----------------------------------------------------------------------
    # 페이지 전환 처리
    # ----------------------------------------------------------------------
    def _handle_room_selection(self, index):
        """ 드롭다운 선택 변경 시 해당 열람실 배치도 페이지로 전환 """
        selected_room_name = self.room_selector.itemText(index)
        
        # 현재 열람실 선택 -> 무시
        if selected_room_name == self.room_name:
            return

        self.switch_callback("seat_map", selected_room_name)

    def _get_styled_seat_number(self, seat_id):
        return f'<span style="color:#2e6cff;">{seat_id}</span>'

    def _show_reservation_popup(self, seat_id):
        """ 좌석 클릭 시 팝업 띄움 """
        status = self.seat_statuses.get(seat_id, "unknown")
        
        if status == "available":
            # 예약 가능 좌석
            title = "좌석배정"
            body = f"{self.room_name} {self._get_styled_seat_number(seat_id)}번"
            footer = ""

            buttons = [
                {'text': '닫기', 'style': 'cancel', 'callback': None},
                {'text': '배정', 'style': 'confirm', 'callback': lambda: self._process_reservation(seat_id)}
            ]
            
        elif status == "reserved":
            # 예약된 좌석
            title = f"{self.room_name} {self._get_styled_seat_number(seat_id)}번"
            body = "이용 불가"
            footer = ""
            
            # 닫기 버튼
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

    def _process_reservation(self, seat_id):
        # 실제 DB 업데이트 필요
        # 다음 페이지 전환
        complete_message = {
            "title": "배정 완료",
            "body": f"{self.room_name} {self._get_styled_seat_number(seat_id)}번",
            "footer": ""
        }
        complete_buttons = [
            {
                'text': '확인', 
                'style': 'confirm', 
                'callback': lambda: self.switch_callback("idle")
            }
        ]
        
        complete_dialog = CustomAlertDialog(complete_message, self, buttons=complete_buttons)
        complete_dialog.exec()

    # ----------------------------------------------------------------------
    # 배치도 생성 함수
    # ----------------------------------------------------------------------

    def _create_seat_map_layout(self, container, seat_statuses):
        """ 배치도 레이아웃 구성 """
        main_vbox = QVBoxLayout(container)
        main_vbox.setSpacing(0)
        main_vbox.setContentsMargins(20, 20, 20, 20)
        
        V_GAP_SMALL = 20
        V_GAP_LARGE = 40
        
        # QGridLayout 열 위치 매핑 (구역 간격 처리)
        col_map = {
            'L': 0, 'S1': 1, 'CS': 2, 'S2': 3, 'CT': 4, 'S3': 7, 'R': 8, 'RW': 9
        }
        
        # ----------------------------------------------------
        # 좌석 버튼 생성 / 그리드 중앙 정렬 
        # ----------------------------------------------------
        
        def create_seat_btn(seat_id, click_callback, seat_statuses):
            """ 좌석 버튼 생성, 상태 전달, 클릭 이벤트 연결 """
            status = seat_statuses.get(seat_id, "unknown")
            btn = SeatButton(seat_id, current_status=status) 
            btn.clicked.connect(lambda checked, s_id=seat_id: click_callback(s_id))
            return btn
        
        def wrap_and_center_grid(grid):
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
        
        # ----------------------------------------------------
        # 톱니바퀴형 블록 생성 함수
        # ----------------------------------------------------
        def create_zig_zag_block_6col(seats_list, click_callback, seat_statuses):
            """ 2행 6열"""
            grid = QGridLayout()
            grid.setSpacing(8)
            grid.setContentsMargins(0, 0, 0, 0)
            
            seats_row1 = seats_list[0:6]; seats_row2 = seats_list[6:][::-1]
            for i in range(6):
                grid.addWidget(create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
                grid.addWidget(create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
            
            return wrap_and_center_grid(grid)
        
        def create_zig_zag_block_4col_layout(seats_list, click_callback, seat_statuses):
            """ 2행 4열 """
            grid = QGridLayout() 
            grid.setSpacing(8)
            grid.setContentsMargins(0, 0, 0, 0) 
            
            seats_row1, seats_row2 = seats_list[0:4], seats_list[4:]
            for i in range(4):
                grid.addWidget(create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
                grid.addWidget(create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
            return grid
        
        def create_zig_zag_block_3col_layout(seats_list, click_callback, seat_statuses):
            """ 2행 3열"""
            grid = QGridLayout() 
            grid.setSpacing(8)
            grid.setContentsMargins(0, 0, 0, 0) 
            
            seats_row1, seats_row2 = seats_list[0:3], seats_list[3:]
            for i in range(3):
                grid.addWidget(create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
                grid.addWidget(create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
            return grid

        def create_zig_zag_block_8col(seats_list, click_callback, seat_statuses):
            """ 2행 8열 """
            grid = QGridLayout() 
            grid.setSpacing(4) 
            grid.setContentsMargins(0, 0, 0, 0)
            
            seats_row1, seats_row2 = seats_list[0:8], seats_list[8:]
            for i in range(8):
                grid.addWidget(create_seat_btn(seats_row1[i], click_callback, seat_statuses), 0, i)
                grid.addWidget(create_seat_btn(seats_row2[i], click_callback, seat_statuses), 1, i)
            
            return wrap_and_center_grid(grid)
        
        def create_wall_block_2col(seats_L, seats_R, click_callback, seat_statuses):
            """ 2열 """
            grid = QGridLayout()
            grid.setSpacing(8)
            grid.setContentsMargins(0, 0, 0, 0)
            
            rows = len(seats_L)
            for r in range(rows):
                grid.addWidget(create_seat_btn(seats_L[r], click_callback, seat_statuses), r, 0)
                grid.addWidget(create_seat_btn(seats_R[r], click_callback, seat_statuses), r, 1)
            
            return wrap_and_center_grid(grid)

        def create_side_group(seats_list, seat_statuses):
            """ 왼쪽 구역 """
            vbox = QVBoxLayout()
            vbox.setSpacing(0)
            vbox.setContentsMargins(0, 0, 0, 0)
            
            vbox.addWidget(create_zig_zag_block_6col(seats_list[:12], self._show_reservation_popup, seat_statuses))
            vbox.addItem(QSpacerItem(0, V_GAP_SMALL, QSizePolicy.Fixed, QSizePolicy.Fixed)) 
            vbox.addWidget(create_zig_zag_block_6col(seats_list[12:], self._show_reservation_popup, seat_statuses))
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
        hbox_reserved.setSpacing(5)
        for i in range(1, 4):
             btn = QPushButton(f"장애인{i}")
             btn.setStyleSheet("background-color: #ff9800; color: white; border-radius: 4px; padding: 5px;")
             hbox_reserved.addWidget(btn)
        
        # 블록 배치
        for i, widget in enumerate(all_left_blocks):
            vbox_left.addWidget(widget)
            if i < len(all_left_blocks) - 1:
                vbox_left.addItem(QSpacerItem(0, V_GAP_SMALL, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        vbox_left.addItem(QSpacerItem(0, V_GAP_SMALL, QSizePolicy.Fixed, QSizePolicy.Fixed)) 
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
            center_layout.addWidget(create_wall_block_2col(seats_L, seats_R, self._show_reservation_popup, seat_statuses), 
                                    current_center_grid_row, col_map['CS'], rows, 1, Qt.AlignTop)
            
            # 3번 구역
            vbox_table.addWidget(create_zig_zag_block_6col(seats_T, self._show_reservation_popup, seat_statuses), Qt.AlignTop)
            
            current_center_grid_row += rows
            
            # 2번 구역 간격
            if i < len(central_combined_blocks) - 1:
                center_layout.addItem(QSpacerItem(0, V_GAP_SMALL, QSizePolicy.Fixed, QSizePolicy.Fixed), current_center_grid_row, col_map['CS'], 1, 4) 
                current_center_grid_row += 1 
                
            # 3번 구역 간격
            if i < len(central_combined_blocks) - 1:
                 vbox_table.addItem(QSpacerItem(0, V_GAP_SMALL, QSizePolicy.Fixed, QSizePolicy.Fixed))
            else:
                 vbox_table.addItem(QSpacerItem(0, V_GAP_SMALL, QSizePolicy.Fixed, QSizePolicy.Fixed))

        # 하단 (3-5 ~ 3-10)
        seats_3_x_lower = {
            '3-5': list(range(189, 201)), '3-6': list(range(201, 213)),
            '3-7': list(range(213, 225)), '3-8': list(range(225, 237)),
            '3-9': list(range(237, 249)), '3-10': list(range(249, 261)),
        }
        
        seats_lower_names = list(seats_3_x_lower.keys())
        for i, (name, seats) in enumerate(seats_3_x_lower.items()):
            vbox_table.addWidget(create_zig_zag_block_6col(seats, self._show_reservation_popup, seat_statuses), Qt.AlignTop)
            
            if i < len(seats_lower_names) - 1:
                vbox_table.addItem(QSpacerItem(0, V_GAP_SMALL, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
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
            hbox_row.setSpacing(V_GAP_SMALL) 
            
            hbox_row.addLayout(create_zig_zag_block_4col_layout(seats_odd, self._show_reservation_popup, seat_statuses))
            hbox_row.addLayout(create_zig_zag_block_3col_layout(seats_even, self._show_reservation_popup, seat_statuses))
            
            vbox_right.addLayout(hbox_row)
            
            if i < q_groups_count - 1:
                vbox_right.addItem(QSpacerItem(0, V_GAP_SMALL, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        # 5번 구역
        vbox_right.addItem(QSpacerItem(0, V_GAP_SMALL, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        seats_5_1_ordered = list(range(345, 353)) + list(range(353, 361))[::-1]
        seats_5_2_ordered = list(range(361, 369)) + list(range(369, 377))[::-1]
        
        vbox_right.addWidget(create_zig_zag_block_8col(seats_5_1_ordered, self._show_reservation_popup, seat_statuses))
        vbox_right.addItem(QSpacerItem(0, V_GAP_SMALL, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        vbox_right.addWidget(create_zig_zag_block_8col(seats_5_2_ordered, self._show_reservation_popup, seat_statuses))
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
        
        container.setMinimumSize(1200, 2000)
