from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QFontDatabase, QFont
from ui_style import scale_value, scale_qsize

class CommonHeader(QWidget):
    def __init__(self, switch_callback, parent=None):
        super().__init__(parent)
        self.switch_callback = switch_callback

        self.setObjectName("CommonHeader")
        self.setMaximumHeight(150)

        QFontDatabase.addApplicationFont("resources/fonts/Pretendard-Regular.ttf")
        self.setFont(QFont("Pretendard", 18))

        # 스타일 적용 범위 CommonHeader로 한정
        self.setStyleSheet("""
            #CommonHeader { background: transparent; }
            #CommonHeader QLabel { color: white; }
            #CommonHeader QPushButton {
                font-size: 20px;
                color: white;
                background-color: transparent;
                border: none;
            }
            #CommonHeader QPushButton:hover { color: #f44336; }
        """)

        # 버튼/여백 크기 정의
        BUTTON_WIDTH = scale_value(40)
        BUTTON_MARGIN_TOP = scale_value(10) 
        BUTTON_MARGIN_SIDE = scale_value(10)
        
        # 메인 레이아웃
        self.main_h_layout = QHBoxLayout(self)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)
        self.main_h_layout.setAlignment(Qt.AlignTop)

        # 왼쪽 밸런스 위젯
        balance_widget = QWidget(self)
        balance_widget.setFixedWidth(BUTTON_WIDTH + BUTTON_MARGIN_SIDE)
        balance_layout = QVBoxLayout(balance_widget)
        balance_layout.setContentsMargins(BUTTON_MARGIN_SIDE, BUTTON_MARGIN_TOP, 0, 0)
        balance_layout.setSpacing(0)
        
        # 2. 중앙 컨텐츠 영역
        self.center_container = QWidget()
        center_layout = QVBoxLayout(self.center_container)
        center_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        center_layout.setContentsMargins(0, scale_value(50), 0, 0)

        self.logo_label = QLabel()
        pixmap = QPixmap("resources/header.png")
        logo_size = scale_qsize(QSize(300, 100))
        
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

        exit_container = QWidget()
        exit_layout = QVBoxLayout(exit_container)
        exit_layout.setContentsMargins(0, BUTTON_MARGIN_TOP, BUTTON_MARGIN_SIDE, 0)
        exit_layout.setSpacing(0)
        exit_layout.addWidget(self.exit_btn, alignment=Qt.AlignTop | Qt.AlignRight)

        # 전체 배치
        self.main_h_layout.addWidget(balance_widget, 0)
        self.main_h_layout.addWidget(self.center_container, 1)
        self.main_h_layout.addWidget(exit_container, 0)
