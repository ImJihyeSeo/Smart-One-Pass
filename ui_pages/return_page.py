from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QFrame, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from .base_page import BasePage
from ui_style import BUTTON_STYLE, CANCEL_BUTTON_STYLE, TITLE_STYLE

class ReturnSeatPage(BasePage):
    """좌석 반납 페이지"""

    def __init__(self, switch_callback):
        super().__init__(switch_callback)
        self.setObjectName("ReturnSeatPage")

        # 좌석 정보 (DB 연동 필요)
        self.seat_data = {
            "seat_room": "2-1",
            "seat_number": "148",
            "assigned_time_start": "1:00",
            "assigned_time_end": "7:00",
            "remaining_time_min": 300,
            "total_time_min": 360,
            "extend_time": "6:00"
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

        # 오른쪽 값 라벨
        value_layout = QVBoxLayout()
        value_layout.setSpacing(30)

        value_htmls = [
            # 좌석
            f'<span style="font-size:28px; color:{WHITE};">'
            f'제{self.seat_data["seat_room"]}열람실 {self.seat_data["seat_number"]}번'
            f'</span>',
            
            # 배정일시
            f'<span style="font-size:28px; color:{WHITE};">'
            f'오후 {self.seat_data["assigned_time_start"]} ~ 오후 {self.seat_data["assigned_time_end"]}'
            f'</span>',
            
            # 잔여시간
            f'<span style="font-size:28px;">'
            f'<span style="color:{BLUE}; font-weight:bold;">{self.seat_data["remaining_time_min"]}</span>' # 파란색
            f'<span style="color:{WHITE};"> / {self.seat_data["total_time_min"]}</span>'
            f'<span style="color:{WHITE};"> (분)</span>' 
            f'</span>',
            
            # 연장가능시간
            f'<span style="font-size:28px; color:{WHITE};">'
            f'오후 {self.seat_data["extend_time"]}'
            f'</span>'
        ]

        for html in value_htmls:
            lbl = QLabel(html)
            lbl.setTextFormat(Qt.RichText)
            lbl.setWordWrap(False)
            value_layout.addWidget(lbl, alignment=Qt.AlignLeft)

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


    def _handle_return(self):
        """좌석 반납 처리 (DB 연동 필요)"""
        self.switch_callback("result", mode="return")