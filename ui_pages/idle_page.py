from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from ui_style import TOTAL_ATTEMPTS, IDLE_PAGE_STYLE, ImageButtonWidget

class IdlePage(QWidget):

    '''
    중앙에 인하대 로고, 하단에 버튼 배치
    '''
    def __init__(self, switch_callback):
        super().__init__()
        self.switch_callback = switch_callback
        
        self.setObjectName("IdlePage")
        self.setStyleSheet(IDLE_PAGE_STYLE)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addStretch(2)
        
        # 도서관 로고
        main_layout.addWidget(self.create_logo_label(
            "resources/lib_logo.png",
            "MAIN LOGO",
            QSize(550, 550),
            "font-size: 24px; color: #007bff; font-weight: bold;"
        ))

        # 타이틀 로고
        title_label = self.create_logo_label(
            "resources/title_logo.png",
            "TITLE LOGO",
            QSize(550, 200),
            "font-size: 18px; color: #f5f5f5; font-weight: normal;"
        )
        title_label.setContentsMargins(0, 5, 0, 0)
        main_layout.addWidget(title_label)
        main_layout.addStretch(1) 
        
        # 버튼 영역
        button_container = QWidget()
        button_container.setStyleSheet("background: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setSpacing(40)
        button_size = QSize(230, 230)

        start_recognition_btn = ImageButtonWidget("resources/entry_button.png", button_size) # 이미지 경로 지정
        start_recognition_btn.clicked.connect(lambda: self.switch_callback("processing", TOTAL_ATTEMPTS))
        
        reserve_facility_btn = ImageButtonWidget("resources/reservation_button.png", button_size) # 이미지 경로 지정
        reserve_facility_btn.clicked.connect(lambda: self.switch_callback("processing", TOTAL_ATTEMPTS, mode="auth_reservation"))

        start_enrollment_btn = ImageButtonWidget("resources/enrollment_button.png", button_size) # 이미지 경로 지정
        start_enrollment_btn.clicked.connect(lambda: self.switch_callback("enrollment_input"))

        button_layout.addWidget(start_recognition_btn)
        button_layout.addWidget(reserve_facility_btn)
        button_layout.addWidget(start_enrollment_btn)
        
        main_layout.addWidget(button_container)
        
        # copyright 로고
        copyright_label = self.create_logo_label(
            "resources/copyright_logo.png",
            "COPYRIGHT LOGO",
            QSize(200, 35),
            "font-size: 32px; color: #f5f5f5; font-weight: normal;"
        )
        copyright_label.setContentsMargins(0, 80, 0, 0)
        main_layout.addWidget(copyright_label)
        main_layout.addSpacing(25)

        self.setLayout(main_layout)

    def create_logo_label(self, image_path, fallback_text, size, text_style):
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            label.setText(fallback_text)
            label.setStyleSheet(text_style)
        else:
            label.setPixmap(pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return label

    def mousePressEvent(self, event):
        pass