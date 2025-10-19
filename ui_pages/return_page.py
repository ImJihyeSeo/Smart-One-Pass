from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QFrame, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from .base_page import BasePage
from ui_style import BUTTON_STYLE

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
        CARD_BG = "#181818"
        BLUE = "#2e6cff"
        WHITE = "#ffffff"

        # 기본 스타일
        self.setStyleSheet(f"""
            #ReturnSeatPage {{
                background-color: #1a1a1a;
                color: {WHITE};
            }}
            #QuestionText {{
                font-size: 20px;
                font-weight: 500;
                color: {WHITE};
            }}
        """)

        # 메인 레이아웃
        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.setSpacing(30)
        main_layout.addSpacing(40)

        # 질문 문구
        question_label = QLabel("좌석을 반납하시겠습니까?")
        question_label.setAlignment(Qt.AlignCenter)
        question_label.setObjectName("QuestionText")
        main_layout.addWidget(question_label)
        main_layout.addSpacing(20)

        # 카드 프레임
        card_frame = QFrame()
        card_frame.setFixedWidth(380)
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
        card_h_layout.setContentsMargins(30, 25, 30, 25)
        card_h_layout.setSpacing(25)

        # 왼쪽 라벨
        key_container = QWidget()
        key_container.setFixedWidth(100)
        key_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum) 
        key_layout = QVBoxLayout(key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(22)

        for text in ["좌석", "배정일시", "잔여시간", "연장가능시간"]:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size: 16px; color: {WHITE}; font-weight: 500;")
            key_layout.addWidget(lbl, alignment=Qt.AlignLeft)

        # 중앙 세로선
        line_frame = QFrame()
        line_frame.setStyleSheet(f"border-left: 1px solid {WHITE};") 
        line_frame.setFixedWidth(1) 
        line_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # 오른쪽 값 라벨
        value_layout = QVBoxLayout()
        value_layout.setSpacing(22)

        GRAY = "#aaaaaa"

        value_htmls = [
            # 좌석
            f'<span style="font-size:16px;"><span style="color:{GRAY};">제</span><span style="color:{WHITE};">{self.seat_data["seat_room"]}<span style="color:{GRAY};">열람실</span> '
            f'{self.seat_data["seat_number"]}</span><span style="color:{GRAY};">번</span></span>',
            
            # 배정일시
            f'<span style="font-size:16px;"><span style="color:{GRAY};">오후 </span>'
            f'<span style="color:{WHITE};">{self.seat_data["assigned_time_start"]}</span>'
            f'<span style="color:{GRAY};"> ~ 오후 </span>'
            f'<span style="color:{WHITE};">{self.seat_data["assigned_time_end"]}</span></span>',
            
            # 잔여시간
            f'<span style="font-size:16px;">'
            f'<span style="color:{BLUE}; font-weight:bold;">{self.seat_data["remaining_time_min"]}</span>'
            f'<span style="color:{WHITE};"> / {self.seat_data["total_time_min"]}</span>'
            f'<span style="color:{GRAY};"> (분)</span></span>',
            
            # 연장가능시간
            f'<span style="font-size:16px;"><span style="color:{GRAY};">오후 </span>'
            f'<span style="color:{WHITE};">{self.seat_data["extend_time"]}</span></span>'
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
        return_btn.setFixedSize(120, 45)
        return_btn.setStyleSheet(BUTTON_STYLE)
        return_btn.clicked.connect(self._handle_return)
        main_layout.addSpacing(30)
        main_layout.addWidget(return_btn, alignment=Qt.AlignHCenter)
        main_layout.addStretch(1)


    def _handle_return(self):
        """좌석 반납 처리 (DB 연동 필요)"""
        msg = {
            "title": "반납 완료",
            "body": "반납이 완료되었습니다.",
            "footer": "",
        }
        self.switch_callback("reservation", popup_msg=msg)