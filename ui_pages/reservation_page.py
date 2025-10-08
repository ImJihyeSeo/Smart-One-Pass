from .base_page import BasePage
from PySide6.QtWidgets import QLabel, QPushButton
from PySide6.QtCore import Qt

class ReservationPage(BasePage):
    def __init__(self, switch_callback):
        super().__init__(switch_callback)
        
        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("시설 예약 및 잔여석 예측 기능 구현 예정")
        title.setStyleSheet("font-size: 24px; color: #ffffff;")
        
        main_layout.addWidget(title)
        
        # 임시 복귀 버튼
        back_btn = QPushButton("메인으로 돌아가기")
        back_btn.clicked.connect(lambda: self.switch_callback("idle"))
        main_layout.addWidget(back_btn)