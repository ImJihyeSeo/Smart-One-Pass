from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap

class CommonHeader(QWidget):

    def __init__(self, switch_callback, parent=None):
        super().__init__(parent)
        self.switch_callback = switch_callback
        self.setStyleSheet("background: transparent;")
        self.setMaximumHeight(150)
        
        # 버튼/여백 크기 정의
        BUTTON_WIDTH = 40
        BUTTON_MARGIN_TOP = 10
        BUTTON_MARGIN_SIDE = 10
        
        # 메인 레이아웃
        self.main_h_layout = QHBoxLayout(self)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)
        self.main_h_layout.setAlignment(Qt.AlignTop)
        
        # 1. 밸런스 위젯 - 왼쪽 공간 균형 맞추기 위함
        balance_widget = QWidget(self)
        balance_widget.setFixedWidth(BUTTON_WIDTH + BUTTON_MARGIN_SIDE) 
        balance_widget.setStyleSheet("background: transparent;")
        
        balance_layout = QVBoxLayout(balance_widget)
        balance_layout.setContentsMargins(BUTTON_MARGIN_SIDE, BUTTON_MARGIN_TOP, 0, 0) 
        balance_layout.setSpacing(0)
        
        
        # 2. 중앙 컨텐츠 영역
        self.center_container = QWidget()
        self.center_container.setStyleSheet("background: transparent;")
        self.center_container.setMaximumHeight(150)
        
        center_layout = QVBoxLayout(self.center_container)
        center_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        center_layout.setContentsMargins(0, 50, 0, 0)

        # 로고
        self.logo_label = QLabel()
        try:
            pixmap = QPixmap("resources/header_logo.png")
            logo_size = QSize(50, 50)
            if not pixmap.isNull():
                self.logo_label.setPixmap(pixmap.scaled(logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.logo_label.setText("LOGO")
        except Exception:
            self.logo_label.setText("LOGO")
        self.logo_label.setStyleSheet("background: transparent; color: white;")
        self.logo_label.setAlignment(Qt.AlignCenter)

        # 텍스트
        self.info_text = QLabel("JeongSeok Smart One-Pass")
        self.info_text.setAlignment(Qt.AlignCenter)
        self.info_text.setStyleSheet("font-size: 14px; color: #aaaaaa; background: transparent; margin-top: 5px;")

        center_layout.addWidget(self.logo_label)
        center_layout.addWidget(self.info_text)

        
        # 3. X 버튼
        self.exit_btn = QPushButton("X")
        self.exit_btn.setFixedSize(BUTTON_WIDTH, BUTTON_WIDTH)
        self.exit_btn.setStyleSheet("""
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
        self.exit_btn.clicked.connect(lambda: self.switch_callback("idle"))
        
        # X 버튼 담을 컨테이너 및 레이아웃
        exit_container = QWidget()
        exit_layout = QVBoxLayout(exit_container)
        exit_layout.setContentsMargins(0, BUTTON_MARGIN_TOP, BUTTON_MARGIN_SIDE, 0) 
        exit_layout.setSpacing(0)
        exit_layout.addWidget(self.exit_btn, alignment=Qt.AlignTop | Qt.AlignRight)
        
        exit_container.setFixedWidth(BUTTON_WIDTH + BUTTON_MARGIN_SIDE)

        # 4. 메인 수평 레이아웃에 요소 배치
        self.main_h_layout.addWidget(balance_widget, 0) # 왼쪽 밸런스 위젯
        self.main_h_layout.addWidget(self.center_container, 1)  # 중앙 컨테이너
        self.main_h_layout.addWidget(exit_container, 0) # 오른쪽 X 버튼
