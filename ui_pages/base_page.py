from PySide6.QtWidgets import QWidget, QVBoxLayout, QSpacerItem
from .common_header import CommonHeader
from PySide6.QtGui import QColor, QPalette

class BasePage(QWidget):
    def __init__(self, switch_callback):
        super().__init__()
        self.switch_callback = switch_callback

        # 공통 레이아웃
        self.base_layout = QVBoxLayout(self)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.base_layout.setSpacing(50)
        
        # 배경색 통일
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#1a1a1a"))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        # 공통 헤더
        self.common_header = CommonHeader(
            switch_callback=switch_callback, 
            parent=self
        )
        self.base_layout.addWidget(self.common_header)

        # spacing 위젯
        self.header_spacing = QSpacerItem(0, 40)
        self.base_layout.addSpacerItem(self.header_spacing)

        # 콘텐츠 영역
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.base_layout.addWidget(self.content_widget)

    def get_content_layout(self):
        return self.content_layout
    
    # spacing 조절 함수
    def set_header_spacing(self, height):
        self.header_spacing.changeSize(0, height)
        self.base_layout.invalidate()  # 레이아웃 갱신
    