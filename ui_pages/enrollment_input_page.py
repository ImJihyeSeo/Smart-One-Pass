from PySide6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QFrame
)
from PySide6.QtCore import Qt
from .base_page import BasePage
from ui_style import BUTTON_STYLE, INPUT_STYLE, LABEL_STYLE, TITLE_STYLE, GUIDE_STYLE, CustomAlertDialog

class EnrollmentInputPage(BasePage):
    def __init__(self, switch_callback):
        super().__init__(switch_callback)
        self.setStyleSheet("QWidget { background: transparent; }") 

        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.addSpacing(70)

        # 안내 텍스트
        title_label = QLabel("얼굴 등록을 위해\n이름과 학번을 입력해주세요")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(TITLE_STYLE)
        main_layout.addWidget(title_label)
        
        guide_label = QLabel("입력하신 정보는 얼굴 인식 시스템 등록을 위해서만 사용됩니다")
        guide_label.setAlignment(Qt.AlignCenter)
        guide_label.setStyleSheet(LABEL_STYLE)
        main_layout.addWidget(guide_label)
        
        main_layout.addSpacing(60)

        # 중앙 입력 폼 감싸는 컨테이너
        input_container_frame = QFrame()
        input_container_frame.setFixedSize(580, 350)
        input_container_frame.setStyleSheet("""
            QFrame {
                background-color: #242424;
                border-radius: 20px;
                padding: 30px 50px;
            }
        """)
        
        # 내부 레이아웃
        design_layout = QVBoxLayout(input_container_frame)
        design_layout.setContentsMargins(0, 0, 0, 0)
        design_layout.setSpacing(0) 

        # 라벨/입력 필드 정렬 함수
        def create_input_block(label_text, placeholder_text):
            block_layout = QVBoxLayout()
            block_layout.setContentsMargins(0, 0, 0, 0)
            
            # 라벨
            label = QLabel(label_text)
            label.setStyleSheet(LABEL_STYLE)
            label.setAlignment(Qt.AlignCenter) 
            
            # 입력 필드
            input_field = QLineEdit()
            input_field.setPlaceholderText(placeholder_text)
            input_field.setStyleSheet(INPUT_STYLE)
            input_field.setAlignment(Qt.AlignCenter)
            
            block_layout.addWidget(label)
            block_layout.addWidget(input_field)
            
            return input_field, block_layout
            
        # 이름 입력 블록
        self.name_input, name_block_layout = create_input_block("이름", "김인하")
        design_layout.addLayout(name_block_layout)
        design_layout.addSpacing(25)

        # 학번 입력 블록
        self.student_id_input, id_block_layout = create_input_block("학번", "20251234")
        design_layout.addLayout(id_block_layout)
        design_layout.addSpacing(25) 

        # 중앙 입력 폼 배치
        frame_hbox = QHBoxLayout()
        frame_hbox.addStretch(1)
        frame_hbox.addWidget(input_container_frame)
        frame_hbox.addStretch(1)

        main_layout.addLayout(frame_hbox)
        main_layout.addSpacing(20)

        # 등록 시작 버튼
        start_btn = QPushButton("등록 시작하기")
        start_btn.setStyleSheet(BUTTON_STYLE)
        start_btn.clicked.connect(self.validate_and_switch)
        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 50, 0, 50)         
        button_layout.addStretch(1)
        button_layout.addWidget(start_btn)
        button_layout.addStretch(1)

        main_layout.addLayout(button_layout)
        main_layout.addStretch(1) 

    def _show_popup(self, title, body, buttons=None):
        info_message = {"title": title, "body": body, "footer": ""}
        
        if buttons is None:
            buttons = [{'text': '확인', 'style': 'confirm', 'callback': None}  ]
            
        dialog = CustomAlertDialog(info_message, self, buttons=buttons, width=450)
        dialog.exec()

    def validate_and_switch(self):
        name = self.name_input.text().strip()
        student_id = self.student_id_input.text().strip()
        
        # 유효성 검사
        if not name:
            self._show_popup("입력 오류", "이름을 입력해 주세요.")
            return

        if not student_id or not student_id.isdigit() or len(student_id) != 8:
            self._show_popup("입력 오류", "정확한 8자리 학번을<br>입력해 주세요.")
            return

        user_data = {"name": name, "student_id": student_id}
        self.switch_callback("enrollment_start", user_data)