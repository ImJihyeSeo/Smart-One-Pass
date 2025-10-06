from PySide6.QtWidgets import QWidget, QVBoxLayout, QSpacerItem
from .common_header import CommonHeader

class BasePage(QWidget):
    def __init__(self, switch_callback):
        super().__init__()
        self.switch_callback = switch_callback

        # 공통 레이아웃
        self.base_layout = QVBoxLayout(self)
        self.base_layout.setContentsMargins(0, 0, 0, 0)
        self.base_layout.setSpacing(20)

        # 공통 헤더
        self.common_header = CommonHeader(switch_callback=switch_callback, parent=self)
        self.base_layout.addWidget(self.common_header)
        # spacing 위젯을 멤버 변수로 저장 (얼굴 등록 화면에서 조절하기 위해)
        self.header_spacing = QSpacerItem(0, 30)
        self.base_layout.addSpacerItem(self.header_spacing)

        # 각 페이지의 콘텐츠 담을 placeholder 위젯
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