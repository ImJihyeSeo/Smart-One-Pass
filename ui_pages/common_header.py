'''
상단 UI 요소
X 버튼 + 학교 로고/타이틀 정보 영역
'''

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap

class CommonHeader(QWidget):

    def __init__(self, switch_callback, parent=None):
        super().__init__(parent)
        self.switch_callback = switch_callback
        self.setStyleSheet("background: transparent;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. 상단 X 버튼
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(10, 10, 10, 10)
        top_bar.addStretch(1)
        
        exit_btn = QPushButton("X")
        exit_btn.setFixedSize(40, 40)
        exit_btn.setStyleSheet("""
            QPushButton {
                font-size: 20px;
                color: #ffffff; 
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                color: #f44336;
            }
        """)
        exit_btn.clicked.connect(lambda: self.switch_callback("idle"))
        top_bar.addWidget(exit_btn)
        
        main_layout.addLayout(top_bar)
        
        # 2. 웹캠 위 로고/타이틀 영역
        
        self.info_container = QWidget()
        self.info_container.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(self.info_container)
        info_layout.setAlignment(Qt.AlignCenter)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # 2-1. 로고
        self.info_logo = QLabel()
        try:
            pixmap = QPixmap("resources/header_logo.png") 
            logo_size = QSize(50, 50)
            if not pixmap.isNull():
                self.info_logo.setPixmap(pixmap.scaled(logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.info_logo.setStyleSheet("background: transparent;")
                self.info_logo.setAlignment(Qt.AlignCenter)
            else:
                self.info_logo.setText("LOGO")
                self.info_logo.setStyleSheet("font-size: 16px; color: yellow; background: transparent; padding: 5px;")
        except Exception:
            self.info_logo.setText("LOGO")
            self.info_logo.setStyleSheet("font-size: 16px; color: yellow; background: transparent; padding: 5px;")
 
        # 2-2. 타이틀
        self.info_text = QLabel("JeongSeok Smart One-Pass")
        self.info_text.setAlignment(Qt.AlignCenter)
        self.info_text.setStyleSheet("font-size: 14px; color: #aaaaaa; margin-top: 5px; background: transparent;")
        
        info_layout.addWidget(self.info_logo)
        info_layout.addWidget(self.info_text)

        # 최종 레이아웃에 중앙 정보 컨테이너 추가
        # 이 위젯을 사용하는 부모 페이지에서 addStretch를 통해 수직 정렬
        main_layout.addWidget(self.info_container)