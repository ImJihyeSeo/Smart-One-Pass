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
        self.setStyleSheet("""
            QWidget { background: transparent; }
            QLabel { color: white; }
            QPushButton {
                font-size: 20px;
                color: white;
                background-color: transparent;
                border: none;
            }
            QPushButton:hover { color: #f44336; }
        """)
        
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
        balance_layout = QVBoxLayout(balance_widget)
        balance_layout.setContentsMargins(BUTTON_MARGIN_SIDE, BUTTON_MARGIN_TOP, 0, 0) 
        balance_layout.setSpacing(0)
        
        # 2. 중앙 컨텐츠 영역
        self.center_container = QWidget()
        center_layout = QVBoxLayout(self.center_container)
        center_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        center_layout.setContentsMargins(0, 50, 0, 0)

        # 로고
        self.logo_label = QLabel()
        pixmap = QPixmap("resources/header.png")
        logo_size = QSize(300, 100)
        
        if pixmap.isNull():
            self.logo_label.setText("LOGO")
        else:
            self.logo_label.setPixmap(pixmap.scaled(logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.logo_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.logo_label)        
        
        # 3. X 버튼
        self.exit_btn = QPushButton("X")
        self.exit_btn.setFixedSize(BUTTON_WIDTH, BUTTON_WIDTH)
        self.exit_btn.clicked.connect(lambda: self.switch_callback("idle"))
        
        # X 버튼 담을 컨테이너 및 레이아웃
        exit_container = QWidget()
        exit_layout = QVBoxLayout(exit_container)
        exit_layout.setContentsMargins(0, BUTTON_MARGIN_TOP, BUTTON_MARGIN_SIDE, 0) 
        exit_layout.setSpacing(0)
        exit_layout.addWidget(self.exit_btn, alignment=Qt.AlignTop | Qt.AlignRight)
        
        # 4. 메인 수평 레이아웃에 요소 배치
        self.main_h_layout.addWidget(balance_widget, 0) # 왼쪽 밸런스 위젯
        self.main_h_layout.addWidget(self.center_container, 1)  # 중앙 컨테이너
        self.main_h_layout.addWidget(exit_container, 0) # 오른쪽 X 버튼
