from PySide6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QFrame
)
from PySide6.QtCore import Qt
from .base_page import BasePage
from ui_style import BUTTON_STYLE, INPUT_STYLE, LABEL_STYLE, TITLE_STYLE, GUIDE_STYLE, CustomAlertDialog

# 백엔드 API 연동

# DB 학생 정보 확인
from PySide6.QtCore import QThread, Signal
import requests
import json

AWS_BASE_URL = "http://34.213.241.165:8000"

# session_manager.py
import sys
import os

# 현재 파일의 부모의 부모 디렉토리(프로젝트 루트)를 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

try:
    from session_manager import UserSession
except ImportError:
    # IDE 환경에 따라 경로가 다를 수 있어 예외 처리 (필요 시 경로 조정)
    print("Warning: session_manager를 찾을 수 없습니다.")

# enrollment_input_page.py (클래스 밖에 정의)

class WorkerThread(QThread):
    # API 결과를 반환할 시그널 정의: (is_exist, error_message)
    finished = Signal(bool, str) 

    def __init__(self, name, student_id):
        super().__init__()
        self.name = name
        self.student_id = student_id
        self.api_url = f"{AWS_BASE_URL}/user/check-existence"

    def run(self):
        """API 호출 로직을 실행합니다."""
        payload = {
            "sid": self.student_id,
            "name": self.name
        }
        
        is_exist = False
        error_message = ""
        
        try:
            # 🚨 AWS 서버에 POST 요청 (동기적 호출)
            response = requests.post(
                self.api_url, 
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload)
            )
            
            if response.status_code == 409:
                # 409 Conflict: DB에 이미 존재함 (중복)
                is_exist = True
                error_message = response.json().get('detail', {}).get('message', "이미 등록된 사용자입니다.")
            
            elif response.status_code == 200:
                # 200 OK: DB에 중복 없음 (성공)
                is_exist = False
                
            else:
                # 400, 500 등 기타 오류
                error_message = f"서버 오류 ({response.status_code}): {response.json().get('detail', '알 수 없는 오류')}"
        
        except requests.exceptions.RequestException as e:
            error_message = f"네트워크 연결 오류: 서버에 접속할 수 없습니다. {e}"

        # 결과를 메인 UI 스레드로 반환
        self.finished.emit(is_exist, error_message)



class EnrollmentInputPage(BasePage):
    def __init__(self, switch_callback):
        super().__init__(switch_callback)
        self.setStyleSheet("QWidget { background: transparent; }") 

        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.addSpacing(70)

        # 안내 텍스트
        title_label = QLabel("얼굴 등록을 위해\n이름과 학번을 입력해주세요")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(TITLE_STYLE)
        main_layout.addWidget(title_label)
        
        guide_label = QLabel("입력하신 정보는 얼굴 인식 시스템 등록을 위해서만 사용됩니다")
        guide_label.setAlignment(Qt.AlignCenter)
        guide_label.setStyleSheet(LABEL_STYLE)
        main_layout.addWidget(guide_label)
        
        main_layout.addSpacing(60)

        # 중앙 입력 폼 감싸는 컨테이너
        input_container_frame = QFrame()
        input_container_frame.setFixedSize(580, 350)
        input_container_frame.setStyleSheet("""
            QFrame {
                background-color: #242424;
                border-radius: 20px;
                padding: 30px 50px;
            }
        """)
        
        # 내부 레이아웃
        design_layout = QVBoxLayout(input_container_frame)
        design_layout.setContentsMargins(0, 0, 0, 0)
        design_layout.setSpacing(0) 

        # 라벨/입력 필드 정렬 함수
        def create_input_block(label_text, placeholder_text):
            block_layout = QVBoxLayout()
            block_layout.setContentsMargins(0, 0, 0, 0)
            
            # 라벨
            label = QLabel(label_text)
            label.setStyleSheet(LABEL_STYLE)
            label.setAlignment(Qt.AlignCenter) 
            
            # 입력 필드
            input_field = QLineEdit()
            input_field.setPlaceholderText(placeholder_text)
            input_field.setStyleSheet(INPUT_STYLE)
            input_field.setAlignment(Qt.AlignCenter)
            
            block_layout.addWidget(label)
            block_layout.addWidget(input_field)
            
            return input_field, block_layout
            
        # 이름 입력 블록
        self.name_input, name_block_layout = create_input_block("이름", "김인하")
        design_layout.addLayout(name_block_layout)
        design_layout.addSpacing(25)

        # 학번 입력 블록
        self.student_id_input, id_block_layout = create_input_block("학번", "20251234")
        design_layout.addLayout(id_block_layout)
        design_layout.addSpacing(25) 

        # 중앙 입력 폼 배치
        frame_hbox = QHBoxLayout()
        frame_hbox.addStretch(1)
        frame_hbox.addWidget(input_container_frame)
        frame_hbox.addStretch(1)

        main_layout.addLayout(frame_hbox)
        main_layout.addSpacing(20)

        # 등록 시작 버튼
        start_btn = QPushButton("등록 시작하기")
        start_btn.setStyleSheet(BUTTON_STYLE)
        start_btn.clicked.connect(self.validate_and_switch)
        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 50, 0, 50)         
        button_layout.addStretch(1)
        button_layout.addWidget(start_btn)
        button_layout.addStretch(1)

        main_layout.addLayout(button_layout)
        main_layout.addStretch(1) 

    def _show_popup(self, title, body, buttons=None):
        info_message = {"title": title, "body": body, "footer": ""}
        
        if buttons is None:
            buttons = [{'text': '확인', 'style': 'confirm', 'callback': None}  ]
            
        dialog = CustomAlertDialog(info_message, self, buttons=buttons, width=450)
        dialog.exec()

    
    # 백엔드 API 연동

    # DB 확인 부분

    def handle_api_response(self, is_exist: bool, error_message: str):
            """
            워커 스레드로부터 API 응답을 받아 처리하는 함수입니다. (메인 UI 스레드에서 실행됨)
            """
            name = self.name_input.text().strip()
            student_id = self.student_id_input.text().strip()
            user_data = {"name": name, "student_id": student_id}
            
            if error_message and "네트워크 연결 오류" in error_message:
                # 🚨 네트워크 오류 처리
                self._show_popup("네트워크 오류", f"AWS 서버 접속 실패:<br>{error_message}")
                return
            
            if is_exist:
                # 🚨 409 Conflict (이미 존재함) -> 로그인 성공으로 간주하고 진행
            
                # ---------------------------------------------------------
                # [추가된 부분 2] 로그인 성공 시 세션 매니저에 정보 저장
                # ---------------------------------------------------------
                try:
                    UserSession.instance().login(user_id=student_id, name=name)
                    print(f"Session Saved: {UserSession.instance().get_user_id()}, {UserSession.instance().name}")
                except NameError:
                    print("Session Manager가 임포트되지 않아 저장에 실패했습니다.")
                # 🚨 409 Conflict 처리: 중복 발견 시
                self.switch_callback("enrollment_start", user_data)
                return
                
            elif error_message:
                # 🚨 기타 서버 오류 (500 Internal Server Error 등)
                self._show_popup("서버 오류", error_message)
                return
                
            else:
                # 5. 성공: DB에 중복 없음 확인 (200 OK)
                self._show_popup("등록 불가", error_message)

    def validate_and_switch(self):
        name = self.name_input.text().strip()
        student_id = self.student_id_input.text().strip()
        
        # 유효성 검사
        if not name:
            self._show_popup("입력 오류", "이름을 입력해 주세요.")
            return

        if not student_id or not student_id.isdigit() or len(student_id) != 8:
            self._show_popup("입력 오류", "정확한 8자리 학번을<br>입력해 주세요.")
            return
        
        # 백엔드 API 연동

        # DB 확인 부분

        # 1. [API 호출 시작] 워커 스레드 생성
        self.worker = WorkerThread(name, student_id)
        
        # 2. API 응답을 받았을 때 실행될 함수 연결
        self.worker.finished.connect(self.handle_api_response)
        
        # 3. 워커 스레드 시작 (UI는 멈추지 않음)
        self.worker.start()
        

        # 그 전 코드는 주석으로 처리

        # handle_api_response 맨 아래에 옮김
        # user_data = {"name": name, "student_id": student_id}
        # self.switch_callback("enrollment_start", user_data)