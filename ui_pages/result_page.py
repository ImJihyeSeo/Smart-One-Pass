from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QSize, QAbstractAnimation
from PySide6.QtGui import QPixmap, QPainter
from .base_page import BasePage
from ui_style import blinking_effect


'''
얼굴 인식 성공/실패 결과 + 얼굴 등록 결과 표시하는 페이지
'''
class ResultPage(BasePage):

    '''
    결과 데이터(success, retries)에 따라 아이콘 파일과 안내 메시지 결정
    '''
    def __init__(self, switch_callback, result_data, mode="auth"):
        super().__init__(switch_callback)
        self.success, current_retries = result_data
        self.mode = mode
        
        # 애니메이션 객체 초기화
        self.scale_animation = None
        self.fade_animation = None
        
        remaining_retries = current_retries - 1 if not self.success else current_retries
        
        self.setStyleSheet("background-color: transparent;")

        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignCenter)
        self.set_header_spacing(-70)
        
        # 카드 위젯
        card_widget = QWidget()
        card_widget.setFixedSize(350, 300) 
        card_widget.setStyleSheet("""
            QWidget {
                background-color: #242424;
                border-radius: 15px;
            }
        """)

        # 카드 내부 레이아웃
        card_layout = QVBoxLayout(card_widget)
        card_layout.setAlignment(Qt.AlignCenter) 
        card_layout.setContentsMargins(30, 30, 30, 30) 
        card_layout.setSpacing(10)

        icon_size = 100
        timeout_ms = 3000
        
        main_message = ""
        sub_message = ""
        
        if self.mode == "auth":
            self.success, current_retries = result_data
            remaining_retries = current_retries - 1 if not self.success else current_retries
            
            if self.success:
                icon_file = "resources/check.png"
                name = "김인하" 
                main_message = f"환영합니다, {name}님!"
                sub_message = "출입문이 열립니다."
                timeout_ms = 3000
                next_page = "idle"
            
            elif remaining_retries > 0:
                icon_file = "resources/alert.png"
                main_message = "인식 실패! 다시 시도해주세요."
                sub_message = f"남은 횟수: {remaining_retries}회"
                timeout_ms = 4000
                next_page = "processing"
            else:
                icon_file = "resources/alert.png"
                main_message = "인식에 최종 실패했습니다."
                sub_message = "학생증을 이용해 주세요."
                timeout_ms = 6000
                next_page = "idle"
        
        elif self.mode == "enroll":
            user_data = result_data  # {name, student_id}
            icon_file = "resources/check.png"
            main_message = f"{user_data['name']}님 ({user_data['student_id']}),\n성공적으로 등록되었습니다!"
            sub_message = "메인 화면으로 자동 전환됩니다"
            timeout_ms = 5000
            next_page = "idle"                

        # 1. 중앙 아이콘
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent;")
        
        icon_display_size = QSize(int(icon_size * 0.7), int(icon_size * 0.7)) 
        
        # 아이콘 이미지 로드 및 그리기
        icon_pixmap = QPixmap(icon_file) 
        if icon_pixmap.isNull():
            self.icon_label.setText("?")
            self.icon_label.setStyleSheet("font-size: 80px; color: white;")
        else:
            scaled_icon = icon_pixmap.scaled(icon_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(scaled_icon)
            self.icon_label.setFixedSize(icon_display_size) 
        
        card_layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)
        card_layout.addSpacing(20) 

        # 2. 메시지 라벨 - 메인 메시지
        self.name_label = QLabel(main_message)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("""
            font-size: 20px; color: #ffffff; background-color: rgba(0, 0, 0, 0); 
        """)
        card_layout.addWidget(self.name_label)
        card_layout.addSpacing(10) 

        # 3. 메시지 라벨 - 서브 메시지
        self.action_label = QLabel(sub_message)
        self.action_label.setAlignment(Qt.AlignCenter)
        self.action_label.setStyleSheet("""
            font-size: 16px; color: #ffffff; background-color: rgba(0, 0, 0, 0); 
        """)
        card_layout.addWidget(self.action_label)

        self.opacity_effect, self.fade_animation = blinking_effect(self.action_label)   # 깜박임 효과
        
        main_layout.addStretch(1) 
        main_layout.addWidget(card_widget, alignment=Qt.AlignCenter)
        main_layout.addStretch(1)
        
        # Timer to switch page after a delay
        self.timer = QTimer(self)
        
        # 페이지 전환 로직: 성공/최종 실패 시 idle, 재시도 가능 시 processing으로 복귀
        if self.success or remaining_retries <= 0:
            next_page = "idle" 
        else:
            next_page = "processing" 

        self.timer.timeout.connect(lambda: self.switch_callback(next_page, remaining_retries)) 
        self.timer.start(timeout_ms)

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
        
    def next_step(self, success, remaining_retries):
        if self.fade_animation and self.fade_animation.state() == QAbstractAnimation.Running:
            self.fade_animation.stop()
            
        if success or remaining_retries <= 0:
            next_page = "idle" 
        else:
            next_page = "processing" 
            
        self.switch_callback(next_page, remaining_retries)