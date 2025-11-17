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
        self.prediction_info = prediction_info  # {'date_display', 'time_str'}
        
        self.setObjectName("PredictionResultPage")
        self.setStyleSheet(self._get_page_style())
        
        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        main_layout.setSpacing(10)
        
        # 예측 시간
        date_display = self._format_date_display(
            self.prediction_info.get('date_display', '00월 00일 (일)'),
            self.prediction_info.get('time_str', '12:00')
        )
        time_display_card = self._create_time_display_card(date_display)

        main_layout.addWidget(time_display_card, alignment=Qt.AlignHCenter) 
        main_layout.addSpacing(30)
        
        # 테두리
        card_frame = QFrame()
        card_frame.setObjectName("MainCardFrame")
        card_frame.setFixedSize(650, 750) 
        card_frame.setStyleSheet(self._get_card_frame_style())
        
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(50, 40, 50, 40)
        card_layout.setSpacing(30)

        # 예측 결과
        result_grid = self._create_result_grid()
        grid_container = QWidget()
        grid_container.setLayout(result_grid)
        card_layout.addWidget(grid_container)
        
        main_layout.addWidget(card_frame, alignment=Qt.AlignHCenter)
        main_layout.addStretch(1)

    # 예측 모델 연동
    # ★ [NEW] 이 함수를 추가하세요! 백엔드 데이터를 받아 화면을 갱신합니다.
    def update_ui(self, result_data: list):
        """
        백엔드 API 결과(result_data)를 받아서 카드를 동적으로 생성합니다.
        result_data 구조: [{'name': '...', 'status': '여유', 'color': '#...'}, ...]
        """
        # 1. 기존 카드들 모두 지우기 (초기화)
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 2. 새 데이터로 카드 생성
        for i, data in enumerate(result_data):
            # _create_status_card 함수는 data 딕셔너리를 그대로 사용하도록 설계되어 있으므로
            # 백엔드에서 키값('name', 'status', 'color')만 맞춰주면 완벽하게 호환됩니다.
            card = self._create_status_card(data, i)
            
            row = i // 2
            col = i % 2
            self.grid_layout.addWidget(card, row, col)
            
        print("✅ 프론트엔드 화면 갱신 완료")
        
    def _get_page_style(self):
        return """
            #PredictionResultPage {
                background-color: #1a1a1a; 
            }
            QLabel {
                background: transparent;
                color: #ffffff;
            }
            #PageTitleLabel {
                font-size: 26px; 
                font-weight: bold;
                color: #A0A0A0;
                margin-left: 75px; 
            }
        """

    def _get_card_frame_style(self):
        """ 메인 카드 프레임 스타일 """
        return """
            #MainCardFrame {
                background-color: transparent;
                border: 2px solid #505050;
                border-radius: 30px;
            }
        """
        
    def _format_date_display(self, date_display, time_str):
        """ 'MM월 dd일 (ddd) HH:MM' 형식을 'MM월 dd일 (요일) HPM 예측'으로 변환 """
        
        # 요일 매핑 딕셔너리
        DAY_MAP = {
            "Mon": "월",
            "Tue": "화",
            "Wed": "수",
            "Thu": "목",
            "Fri": "금",
            "Sat": "토",
            "Sun": "일",
        }

        time_part = time_str.split(':')
        if not time_part:
            return f"{date_display} 예측"
            
        # 시간대 포맷팅
        try:
            hour = int(time_part[0])
        except ValueError:
             hour = 12
             
        am_pm = "AM" if hour < 12 else "PM"
        
        display_hour = 12 if hour == 0 or hour == 12 else hour % 12
        if display_hour == 0: display_hour = 12

        # 날짜, 요일 파싱
        try:
            parts = date_display.split('(')
            date_part = parts[0].strip()
            day_part_en = parts[1].strip().split(')')[0]
            
            # 한글 변환
            day_part_kr = DAY_MAP.get(day_part_en, day_part_en) # 매핑 실패 시 원본 유지
            
            return f"{date_part} ({day_part_kr}) {display_hour}{am_pm} 예측"
        
        except Exception:
            # 파싱 오류 시 최소한의 정보만 반환
            return f"{date_display} {display_hour}{am_pm} 예측"
        
    def _create_time_display_card(self, text):
        card = QFrame()
        card.setFixedSize(450, 60)
        card.setStyleSheet("""
            QFrame {
                background-color: #242424;
                border-radius: 12px;
            }
            QLabel {
                font-size: 28px; 
                color: #ffffff; 
            }
        """)
        
        hbox = QHBoxLayout(card)
        hbox.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        hbox.addWidget(label)
        return card

    def _get_prediction_data(self):
        """ 
        [API 연동 필요]
        1. self.prediction_info['date_str']와 self.prediction_info['time_str']를 
           AI 모델 API에 전달.
        2. API로부터 각 열람실의 예측 결과를 받아서 아래 'virtual_api_response' 구조로 매핑.
        """
        
        # 임시 데이터
        virtual_api_response = {
            "제1열람실": "혼잡", 
            "제2-1열람실": "여유", 
            "제2-2열람실": "보통", 
            "제2-2열람실\n(대학원생 전용)": "여유", 
        }

        prediction_results = {}
        
        STATUS_MAP = {
            "혼잡": {"color": "#E74C3C"},
            "보통": {"color": "#F1C40F"},
            "여유": {"color": "#3498DB"},
        }
        
        for room, status in virtual_api_response.items():
            prediction_results[room] = {
                "status": status,
                "color": STATUS_MAP.get(status, {}).get("color", "#FFFFFF"),
            }
            
        return prediction_results
        
    def _get_icon_path(self, status_type):
        icon_filename = ""

        if status_type == "혼잡":
            icon_filename = "face_red.png" 
        elif status_type == "보통":
            icon_filename = "face_yellow.png" 
        elif status_type == "여유":
            icon_filename = "face_blue.png" 
        else:
            print(f"경고: 알 수 없는 상태 - {status_type}")
            return None
        
        current_dir = os.path.dirname(__file__)
        
        icon_path = os.path.abspath(
            os.path.join(current_dir, '..', 'resources', icon_filename)
        )
        
        if not os.path.exists(icon_path):
            print(f"경고: 아이콘 파일 경로 오류 - 파일 없음: {icon_path}")
            return None
            
        return icon_path

    def _create_result_grid(self):
        results = self._get_prediction_data()   # 예측 결과 불러오기 
        
        grid = QGridLayout()
        grid.setSpacing(20) 
        grid.setContentsMargins(0, 0, 0, 0) 
        
        CARD_FIXED_SIZE = 270 
        ICON_HEIGHT = 130 
        rooms = list(results.keys())

        for i, room_name in enumerate(rooms):
            data = results[room_name]
            
            item_frame = QFrame() 
            item_frame.setFixedSize(CARD_FIXED_SIZE, CARD_FIXED_SIZE) 
            item_frame.setObjectName(f"PredictionItemCard_{i}")
            
            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 15, 10, 15) 
            item_layout.setSpacing(5) 
            item_layout.addStretch(1) 
            
            # 열람실 이름
            name_label = QLabel(room_name.replace('\n', '<br>'))
            name_label.setTextFormat(Qt.RichText)
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
            
            # 얼굴 아이콘
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignCenter)
            icon_path = self._get_icon_path(data['status'])
            if icon_path and os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaledToHeight(
                        ICON_HEIGHT, Qt.SmoothTransformation
                    )
                    icon_label.setPixmap(scaled_pixmap)
            item_layout.addWidget(icon_label, alignment=Qt.AlignCenter)
            
            # 텍스트
            status_label = QLabel(data['status'])
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setStyleSheet(
                f"font-size: 26px; color: {data['color']}; font-weight: bold; margin: 0; background: transparent;"
            )
            item_layout.addWidget(status_label)
            item_layout.addStretch(1) 

            row = i // 2
            col = i % 2
            grid.addWidget(item_frame, row, col, alignment=Qt.AlignCenter) 
            
        return grid
