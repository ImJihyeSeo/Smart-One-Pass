from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QSize, QAbstractAnimation
from PySide6.QtGui import QPixmap, QPainter
from .base_page import BasePage
from ui_style import blinking_effect, TITLE_STYLE, LABEL_STYLE

'''
얼굴 인식 성공/실패 결과 + 얼굴 등록 결과 표시하는 페이지
'''
class ResultPage(BasePage):

    '''
    결과 데이터(인증: success, retries, name / 등록: user_data)에 따라 메시지 결정
    '''
    def __init__(self, switch_callback, result_data, mode="auth"):
        super().__init__(switch_callback)
        self.mode = mode
        
        # 애니메이션 객체 초기화
        self.scale_animation = None
        self.fade_animation = None

        next_page = "idle" # 기본값

        # 결과 데이터 언팩
        if self.mode in ["auth", "auth_reservation"]:
            if len(result_data) == 4:
                # 'auth_reservation' 모드
                self.success, current_retries, name, self.user_data = result_data
            else:
                # 'auth' 모드
                self.success, current_retries, name = result_data
                self.user_data = None

            remaining_retries = current_retries - 1 if not self.success else current_retries
        
        else: # enroll, return, extend 모드
            self.success = True # 성공 전제로 전환됨
            remaining_retries = 0
            name = None
            self.user_data = result_data
        
        if self.mode == "auth":
            # 인증 모드: (success, current_retries, name)을 받음
            self.success, current_retries, name = result_data
            remaining_retries = current_retries - 1 if not self.success else current_retries

            if self.success:
                icon_file = "resources/check.png"
                main_message = f"환영합니다, {name}님!"
                sub_message = "출입문이 열립니다."
                next_page = "idle"
            elif remaining_retries > 0:
                icon_file = "resources/alert.png"
                main_message = "인식 실패! 다시 시도해주세요."
                sub_message = f"남은 횟수: {remaining_retries}회"
                next_page = "processing"
            else:
                icon_file = "resources/alert.png"
                main_message = "인식에 최종 실패했습니다."
                sub_message = "학생증을 이용해 주세요."
                next_page = "idle"
            
            timeout_ms = 3000 if self.success else 5000

        elif self.mode == "auth_reservation":
            # 예약 인증 모드: (success, current_retries, name, user_data)을 받음
            timeout_ms = 3000 if self.success else 5000
            if self.success:
                icon_file = "resources/check.png"
                main_message = f"환영합니다, {name}님!"
                sub_message = "예약 페이지로 자동 전환됩니다."
                next_page = "reservation"   # 쓰이지 않음 - 성공 시 바로 reservation 페이지로 이동 - 학생 정보(self.user_data) 전달
            elif remaining_retries > 0:
                icon_file = "resources/alert.png"
                main_message = "인식 실패! 다시 시도해주세요."
                sub_message = f"남은 횟수: {remaining_retries}회"
                next_page = "processing"    # 재시도 시 processing 페이지로, 모드 유지
            else:
                icon_file = "resources/alert.png"
                main_message = "인식에 최종 실패했습니다."
                sub_message = "학생증을 이용해 주세요."
                next_page = "idle"  # 최종 실패 시 idle 페이지로

        elif self.mode == "enroll":
            # 등록 모드: user_data (dict)를 받음
            user_data = result_data
            self.success = True # 등록 성공 간주 (enrollment_recording_page에서 실패 시 전환 안 함)
            remaining_retries = 0 
            
            icon_file = "resources/check.png"
            main_message = f"{user_data['name']}님 ({user_data['student_id']}),\n성공적으로 등록되었습니다!"
            sub_message = "메인 화면으로 자동 전환됩니다"
            timeout_ms = 5000
            next_page = "idle"

        elif self.mode == "return":
            # 반납 모드
            icon_file = "resources/check.png"
            main_message = "좌석 반납이\n완료되었습니다!"
            sub_message = "메인 화면으로 자동 전환됩니다."
            self.success = True
            remaining_retries = 0
            timeout_ms = 3000

        elif self.mode == "extend":
            # 연장 모드
            icon_file = "resources/check.png"
            main_message = "좌석 연장이\n완료되었습니다!" 
            sub_message = "메인 화면으로 자동 전환됩니다."
            self.success = True
            remaining_retries = 0
            timeout_ms = 3000

        self.setStyleSheet("background-color: transparent;")

        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignCenter)
        self.set_header_spacing(-140)
        
        # 카드 위젯
        card_widget = QWidget()
        card_widget.setFixedSize(600, 550)
        card_widget.setStyleSheet("""
            QWidget {
                background-color: #242424;
                border-radius: 15px;
                padding: 5px;
            }
        """)
        
        card_layout = QVBoxLayout(card_widget)
        card_layout.setAlignment(Qt.AlignCenter)

        # 아이콘
        self.icon_label = QLabel()
        self.icon_label.setStyleSheet("background: transparent; border: none; border: 0px; margin: 0px;")
        pixmap = QPixmap(icon_file)
        icon_size = QSize(130, 130)
        self.icon_label.setPixmap(pixmap.scaled(icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.icon_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.icon_label)
        card_layout.addSpacing(25)

        # 메인 메시지
        self.message_label = QLabel(main_message)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("font-size: 38px; color: #ffffff; margin-bottom: 5px;")
        card_layout.addWidget(self.message_label)
        card_layout.addSpacing(20)

        # 서브 메시지
        self.action_label = QLabel(sub_message)
        self.action_label.setAlignment(Qt.AlignCenter)
        self.action_label.setStyleSheet(LABEL_STYLE)
        card_layout.addWidget(self.action_label)

        self.opacity_effect, self.fade_animation = blinking_effect(self.action_label)   # 깜박임 효과
        
        main_layout.addStretch(1) 
        main_layout.addWidget(card_widget, alignment=Qt.AlignCenter)
        main_layout.addStretch(1)
        
        self.timer = QTimer(self)
        
        # 페이지 전환 로직: 성공/최종 실패/등록 완료 시 idle, 재시도 가능 시 processing으로 복귀
        if next_page == "reservation" and self.success:
            # 성공 시 학생 정보 전달
            self.timer.timeout.connect(lambda: self.switch_callback(next_page, self.user_data))
        elif next_page == "processing":
            # 재시도 시 남은 횟수와 모드 전달
            self.timer.timeout.connect(lambda: self.switch_callback(next_page, remaining_retries, mode=self.mode))
        else:
            # idle이나 auth 모드 처리
            self.timer.timeout.connect(lambda: self.switch_callback(next_page, remaining_retries)) 

        self.timer.start(timeout_ms)

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
        
    def next_step(self, success, remaining_retries):
        if self.fade_animation and self.fade_animation.state() == QAbstractAnimation.Running:
            self.fade_animation.stop()
