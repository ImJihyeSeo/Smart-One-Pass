from PySide6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QFrame
)
from PySide6.QtCore import Qt
from .base_page import BasePage
from ui_style import BUTTON_STYLE, INPUT_STYLE, CustomAlertDialog


class EnrollmentInputPage(BasePage):
    def __init__(self, switch_callback):
        super().__init__(switch_callback)
        self.switch_callback = switch_callback
        self.setStyleSheet("QWidget { background: transparent; }") 

        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)

        # 안내 텍스트
        title_label = QLabel("얼굴 등록을 위해\n이름과 학번을 입력해주세요")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff; margin-bottom: 5px;")
        main_layout.addWidget(title_label)
        
        guide_label = QLabel("입력하신 정보는 얼굴 인식 시스템 등록을 위해서만 사용됩니다")
        guide_label.setAlignment(Qt.AlignCenter)
        guide_label.setStyleSheet("font-size: 14px; color: #aaaaaa; margin-bottom: 20px;")
        main_layout.addWidget(guide_label)
        
        main_layout.addStretch(0.5) 

        # 중앙 입력 폼
        self.design_frame = QFrame()
        self.design_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border-radius: 12px;
                padding: 30px; 
            }
        """)
        self.design_frame.setFixedWidth(380)

        label_style = "color: #ffffff; font-size: 15px; font-weight: bold;"
        
        design_layout = QVBoxLayout(self.design_frame)
        design_layout.setContentsMargins(0, 0, 0, 0)
        design_layout.setSpacing(10)


        # 라벨/입력 필드 정렬 함수
        def create_input_block(label_text, placeholder_text):
            block_layout = QHBoxLayout()
            block_layout.setContentsMargins(0, 0, 0, 0)
            block_layout.setSpacing(1) # 라벨과 필드 간격
            
            # 라벨
            label = QLabel(label_text)
            label.setStyleSheet(label_style)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter) 
            
            # 입력 필드
            input_field = QLineEdit()
            input_field.setPlaceholderText(placeholder_text)
            input_field.setStyleSheet(INPUT_STYLE)
            
            block_layout.addWidget(label)
            block_layout.addWidget(input_field)
            
            return input_field, block_layout
            
        # 이름 입력 블록
        self.name_input, name_block_layout = create_input_block("이름", "김인하")
        design_layout.addLayout(name_block_layout)
        # 학번 입력 블록
        self.student_id_input, id_block_layout = create_input_block("학번", "20251234")
        design_layout.addLayout(id_block_layout)
        
        design_layout.addSpacing(30) 

        # 등록 시작 버튼
        start_btn = QPushButton("등록 시작하기")
        button_style_override = BUTTON_STYLE + " min-width: 160px; min-height: 45px; font-size: 18px; font-weight: bold;"
        start_btn.setStyleSheet(button_style_override)
        start_btn.clicked.connect(self.validate_and_switch)
        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 30, 0, 30)
        button_layout.addStretch(1)
        button_layout.addWidget(start_btn)
        button_layout.addStretch(1)

        frame_hbox = QHBoxLayout()
        frame_hbox.addStretch(1)
        frame_hbox.addWidget(self.design_frame)
        frame_hbox.addStretch(1)

        main_layout.addLayout(frame_hbox)
        main_layout.addLayout(button_layout)
        main_layout.addStretch(2) 

    def validate_and_switch(self):
        name = self.name_input.text().strip()
        student_id = self.student_id_input.text().strip()
        
        if not name or not student_id:
            alert = CustomAlertDialog("이름과 학번을\n모두 입력해야 합니다", self)
            alert.adjustSize()
            alert.exec()
            return

        user_data = {"name": name, "student_id": student_id}
        self.switch_callback("enrollment_start", user_data)