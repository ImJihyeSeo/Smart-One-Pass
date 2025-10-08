from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from ui_style import BUTTON_STYLE
from .base_page import BasePage

class EnrollmentStartPage(BasePage):
    def __init__(self, switch_callback, user_data):
        super().__init__(switch_callback)
        self.switch_callback = switch_callback
        self.user_data = user_data  # enrollment_input 페이지에서 전달 받은 이름/학번
        self.setStyleSheet("QWidget { background: transparent; }") 

        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)
                
        # 시작 안내
        title_label = QLabel("얼굴 등록을 시작합니다")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff; margin-bottom: 50px; background: transparent;")
        main_layout.addWidget(title_label)
        
        # 유의사항 안내
        guidance_box = QWidget()
        guidance_box.setStyleSheet("""
            QWidget {
                background-color: #333333; 
                border-radius: 10px;
                padding: 20px;
            }
            QLabel {
                color: #cccccc;
                font-size: 16px;
                line-height: 1.5;
            }
        """)
        guidance_box.setFixedWidth(380)
        guidance_layout = QVBoxLayout(guidance_box)
        guidance_layout.setAlignment(Qt.AlignCenter)

        guidance_title = QLabel("촬영 시 유의사항")
        guidance_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        guidance_title.setAlignment(Qt.AlignCenter)

        guidance_text = QLabel(
            "1. 총 3단계의 촬영이 진행됩니다.\n"
            "2. 각 단계는 10~15초 정도 소요됩니다.\n"
            "3. 선글라스, 모자, 마스크는 벗어주세요.\n"
            "4. 몸은 고정하고 고개만 움직여주세요."
        )
        guidance_text.setAlignment(Qt.AlignCenter)
        guidance_text.setWordWrap(True)

        guidance_layout.addWidget(guidance_title)
        guidance_layout.addWidget(guidance_text)

        # guidance_box 가운데 정렬
        guidance_container = QHBoxLayout()
        guidance_container.addStretch(1)
        guidance_container.addWidget(guidance_box)
        guidance_container.addStretch(1)

        main_layout.addLayout(guidance_container)
        main_layout.addStretch(1)

        # 버튼
        start_btn = QPushButton("촬영 시작하기")
        start_btn.setStyleSheet(BUTTON_STYLE)
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(start_btn)
        button_layout.addStretch(1)

        main_layout.addLayout(button_layout)
        main_layout.addStretch(1)

        # enrollment_recording 페이지로 이동
        start_btn.clicked.connect(lambda: self.switch_callback("enrollment_recording", self.user_data))