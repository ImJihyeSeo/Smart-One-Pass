from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import os
from .base_page import BasePage

class PredictionResultPage(BasePage):
    def __init__(self, switch_callback, prediction_info):
        super().__init__(switch_callback)
        self.prediction_info = prediction_info
        
        self.setObjectName("PredictionResultPage")
        self.setStyleSheet(self._get_page_style())
        
        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        main_layout.setSpacing(10)
        
        # 1. 예측 시간 표시 카드
        date_display = self._format_date_display(
            self.prediction_info.get('date_display', '00월 00일 (일)'),
            self.prediction_info.get('time_str', '12:00')
        )
        time_display_card = self._create_time_display_card(date_display)
        main_layout.addWidget(time_display_card, alignment=Qt.AlignHCenter) 
        main_layout.addSpacing(30)
        
        # 2. 메인 카드 프레임 생성
        card_frame = QFrame()
        card_frame.setObjectName("MainCardFrame")
        card_frame.setFixedSize(650, 750) 
        card_frame.setStyleSheet(self._get_card_frame_style())
        
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(50, 40, 50, 40)
        card_layout.setSpacing(30)

        # 그리드 레이아웃 초기화
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20) 
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # 그리드 컨테이너를 생성하고 레이아웃에 바로 추가
        grid_container = QWidget()
        grid_container.setLayout(self.grid_layout) 
        card_layout.addWidget(grid_container)
        
        # 로딩 상태 표시
        self._init_loading_state() 

        main_layout.addWidget(card_frame, alignment=Qt.AlignHCenter)
        main_layout.addStretch(1)

    def update_ui(self, result_data: list):
        """ 백엔드 데이터를 받아 화면 갱신 """
        # 기존 위젯 깨끗이 삭제
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 새 데이터로 카드 생성하여 배치
        for i, data in enumerate(result_data):
            card = self._create_status_card(data)
            row = i // 2
            col = i % 2
            self.grid_layout.addWidget(card, row, col)
            
        print("프론트엔드 화면 갱신 완료")

    def _init_loading_state(self):
        """ 로딩 중일 때 보여줄 임시 데이터 """
        temp_data = [
            {"name": "제1열람실", "status": "로딩중...", "color": "#999999"},
            {"name": "제2-1열람실", "status": "로딩중...", "color": "#999999"},
            {"name": "제2-2열람실", "status": "로딩중...", "color": "#999999"},
            {"name": "제2-2열람실\n(대학원생 전용)", "status": "로딩중...", "color": "#999999"},
        ]
        self.update_ui(temp_data)

    def _create_status_card(self, data):
        """ 개별 열람실 카드 생성 """
        CARD_FIXED_SIZE = 270 
        ICON_HEIGHT = 130 
        
        item_frame = QFrame() 
        item_frame.setFixedSize(CARD_FIXED_SIZE, CARD_FIXED_SIZE) 
        
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(10, 15, 10, 15) 
        item_layout.setSpacing(5) 
        item_layout.addStretch(1) 
        
        # 1. 열람실 이름
        room_name = data.get('name', '알 수 없음')
        # name_label = QLabel(room_name.replace('\n', '<br>'))
        name_label = QLabel(room_name)
        name_label.setWordWrap(True)   # ✅ [핵심 1] 텍스트가 길면 알아서 줄바꿈
        # name_label.setTextFormat(Qt.RichText)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("""
            font-size: 26px; 
            color: #ffffff; 
            background: transparent; 
            margin: 0;
            min-height: 70px;
        """)
        item_layout.addWidget(name_label)
        item_layout.addSpacing(10)
        
        # 2. 아이콘 (상태에 따라 이미지 변경)
        status_text = data.get('status', '미정')
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_path = self._get_icon_path(status_text)
        
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                scaled = pixmap.scaledToHeight(ICON_HEIGHT, Qt.SmoothTransformation)
                icon_label.setPixmap(scaled)
        item_layout.addWidget(icon_label, alignment=Qt.AlignCenter)
                
        STATUS_MAP = {
            "혼잡": "#E74C3C",  # 붉은색
            "보통": "#F1C40F",  # 노란색
            "여유": "#3498DB",  # 파란색
            "만석": "#E74C3C"   # 만석도 혼잡과 같은 붉은색 처리
        }
        
        # 매핑된 색상이 있으면 사용하고, 없으면 백엔드에서 온 color 사용, 그것도 없으면 흰색
        text_color = STATUS_MAP.get(status_text, data.get('color', '#FFFFFF'))
        
        status_label = QLabel(status_text)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet(
            f"font-size: 26px; color: {text_color}; font-weight: bold; margin: 0; background: transparent;"
        )
        item_layout.addWidget(status_label)
        item_layout.addStretch(1) 
        
        return item_frame

    def _get_icon_path(self, status_type):
        icon_filename = ""
        if status_type == "혼잡":
            icon_filename = "face_red.png" 
        elif status_type == "보통":
            icon_filename = "face_yellow.png" 
        elif status_type == "여유":
            icon_filename = "face_blue.png" 
        elif status_type == "만석":
            icon_filename = "face_red.png"
        else:
            return None 
        
        current_dir = os.path.dirname(__file__)
        return os.path.abspath(os.path.join(current_dir, '..', 'resources', icon_filename))

    def _get_page_style(self):
        return """
            #PredictionResultPage { background-color: #1a1a1a; }
            QLabel { background: transparent; color: #ffffff; }
        """

    def _get_card_frame_style(self):
        return """
            #MainCardFrame {
                background-color: transparent;
                border: 2px solid #505050;
                border-radius: 30px;
            }
        """
        
    def _format_date_display(self, date_display, time_str):
        DAY_MAP = {"Mon": "월", "Tue": "화", "Wed": "수", "Thu": "목", "Fri": "금", "Sat": "토", "Sun": "일"}
        time_part = time_str.split(':')
        if not time_part: return f"{date_display} 예측"
        try:
            hour = int(time_part[0])
            am_pm = "AM" if hour < 12 else "PM"
            display_hour = 12 if hour == 0 or hour == 12 else hour % 12
            parts = date_display.split('(')
            date_part = parts[0].strip()
            day_part_en = parts[1].strip().split(')')[0]
            day_part_kr = DAY_MAP.get(day_part_en, day_part_en)
            return f"{date_part} ({day_part_kr}) {display_hour}{am_pm} 예측"
        except:
            return f"{date_display} 예측"

    def _create_time_display_card(self, text):
        card = QFrame()
        card.setFixedSize(450, 60)
        card.setStyleSheet("QFrame { background-color: #242424; border-radius: 12px; } QLabel { font-size: 28px; color: #ffffff; }")
        hbox = QHBoxLayout(card)
        hbox.setContentsMargins(0, 0, 0, 0)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        hbox.addWidget(label)
        return card