from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from config import TOTAL_ATTEMPTS, BUTTON_STYLE 

'''
애플리케이션의 시작/기본 화면을 표시하는 페이지
'''
class IdlePage(QWidget):

    '''
    중앙에 인하대 로고, 하단에 버튼 배치
    '''
    def __init__(self, switch_callback):
        super().__init__()
        self.switch_callback = switch_callback
        
        self.setObjectName("IdlePage")
        
        self.setStyleSheet("""
            #IdlePage {
                background-color: #1a1a1a; 
                color: #ffffff; 
                border-radius: 20px; 
            }
            QLabel {
                background: transparent;
                color: #ffffff;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. 중앙 컨텐츠 영역 (로고 이미지)
        
        main_layout.addStretch(1) 
        
        central_logo_label = QLabel()
        central_logo_label.setAlignment(Qt.AlignCenter)
        
        try:
            pixmap = QPixmap("resources/logo.png")
            central_logo_label.setPixmap(pixmap.scaled(QSize(250, 250), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except:
            central_logo_label.setText("MAIN LOGO")
            central_logo_label.setStyleSheet("font-size: 48px; color: #007bff; font-weight: bold;")
            
        main_layout.addWidget(central_logo_label)
        
        main_layout.addStretch(1) 
        
        # 2. 버튼 영역
        button_container = QWidget()
        button_container.setStyleSheet("background: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setSpacing(40)
        
        start_recognition_btn = QPushButton("얼굴 인식 시작")
        start_recognition_btn.setStyleSheet(BUTTON_STYLE)
        start_recognition_btn.clicked.connect(lambda: self.switch_callback("processing", TOTAL_ATTEMPTS))
        
        start_enrollment_btn = QPushButton("얼굴 등록")
        start_enrollment_btn.setStyleSheet(BUTTON_STYLE)
        start_enrollment_btn.clicked.connect(lambda: self.switch_callback("enrollment_input"))

        button_layout.addWidget(start_recognition_btn)
        button_layout.addWidget(start_enrollment_btn)
        
        main_layout.addWidget(button_container)
        
        main_layout.addSpacing(40) 
        
        self.setLayout(main_layout)

    def mousePressEvent(self, event):
        pass