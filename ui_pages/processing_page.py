import cv2
import random
import time

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGraphicsDropShadowEffect, QPushButton, QFrame
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QImage, QPainter, QBitmap, QColor, QPen

from config import TARGET_W, TARGET_H, MESSAGE_AREA_HEIGHT, BORDER_RADIUS 
from cv_tools import detect_faces

'''
웹캠 화면 표시하고, 얼굴 인식 과정을 시각적으로 처리해 결과를 result_page로 넘기는 페이지
'''
class ProcessingPage(QWidget):
    '''
    UI 구성, QTimer 시작
    '''
    def __init__(self, switch_callback, cap, retries):
        super().__init__()

        # 상태 변수 초기화
        self.switch_callback = switch_callback
        self.cap = cap
        self.retries = retries

        self.start_time = None
        self.duration = 3.0

        self.TARGET_W, self.TARGET_H = TARGET_W, TARGET_H 
        self.BORDER_RADIUS = BORDER_RADIUS 
        self.setStyleSheet("QWidget { background: transparent; }") 

        # 가이드라인 투명도 애니메이션 상태변수 
        self.fade_speed = 8.0        # 투명도 변화 속도
        self.current_alpha = 255.0   # 현재 투명도 (255: 불투명)
        self.fade_direction = -1     # -1: 감소 (페이드 아웃)

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        
        # 1. 상단 바 (X 버튼 포함)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch(1)
        
        exit_btn = QPushButton("X")
        exit_btn.setFixedSize(40, 40)
        exit_btn.setStyleSheet("""
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
        exit_btn.clicked.connect(lambda: self.switch_callback("idle"))
        top_bar.addWidget(exit_btn)

        # 2. 웹캠 위 정보 영역 (로고/텍스트)
        self.info_container = QWidget()
        self.info_container.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(self.info_container)
        info_layout.setAlignment(Qt.AlignCenter)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # 2-1. 로고 이미지
        self.info_logo = QLabel()
        try:
            pixmap = QPixmap("resources/header_logo.png") 
            logo_size = QSize(50, 50)
            if not pixmap.isNull():
                self.info_logo.setPixmap(pixmap.scaled(logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.info_logo.setStyleSheet("background: transparent;")
                self.info_logo.setAlignment(Qt.AlignCenter)
            else:
                raise FileNotFoundError("QPixmap failed to load the image.")
        except Exception as e:
            self.info_logo.setText("LOGO")
            self.info_logo.setStyleSheet("font-size: 16px; color: yellow; background: transparent; padding: 5px;")
 
        # 2-2. 텍스트
        self.info_text = QLabel("JeongSeok Smart One-Pass")
        self.info_text.setAlignment(Qt.AlignCenter)
        self.info_text.setStyleSheet("font-size: 14px; color: #aaaaaa; margin-top: 5px; background: transparent;")
        
        info_layout.addWidget(self.info_logo)
        info_layout.addWidget(self.info_text)

        # 3. 비디오 영역
        self.video_label = QLabel()
        self.video_label.setFixedSize(self.TARGET_W, self.TARGET_H)
        self.video_label.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                border-radius: {self.BORDER_RADIUS}px;
            }}
        """)

        # 3-1. 반투명 오버레이 프레임 씌우기
        self.overlay_frame = QFrame(self.video_label) # video_label을 부모로 설정하여 겹침
        self.overlay_frame.setFixedSize(self.TARGET_W, self.TARGET_H)
        self.overlay_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 80); 
                border-radius: {self.BORDER_RADIUS}px;
            }}
        """)

        # 3-2. 입체감 부여
        shadow = QGraphicsDropShadowEffect(self.video_label)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.video_label.setGraphicsEffect(shadow)     

        # 4. 메시지 영역
        self.message_container = QWidget()
        self.message_container.setFixedHeight(MESSAGE_AREA_HEIGHT)
        self.message_container.setStyleSheet("background: transparent;")

        message_layout = QVBoxLayout(self.message_container)
        message_layout.setContentsMargins(0, 0, 0, 0)
        
        self.instruction = QLabel("얼굴 인식을 시작하려면 화면을 바라봐주세요.")
        self.instruction.setAlignment(Qt.AlignCenter)
        self.instruction.setStyleSheet("font-size: 18px; color: #ffffff; background: transparent;")
        
        message_layout.addWidget(self.instruction)
        
        main_layout.addLayout(top_bar)
        main_layout.addStretch(1)
        main_layout.addWidget(self.info_container, 0, Qt.AlignCenter)
        main_layout.addStretch(2)
        main_layout.addWidget(self.video_label, 0, Qt.AlignCenter)
        main_layout.addStretch(1)
        main_layout.addWidget(self.message_container)
        main_layout.setContentsMargins(0, 0, 0, 0) 

        self.setLayout(main_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)


    '''
    웹캠 메인 루프. QTimer에 의해 30ms마다 호출
    1. 웹캠 프레임 로드 및 크롭
    2. L자 가이드라인 그리고 얼굴 감지
    3. 가이드라인 투명도 계산 및 업데이트
    4. 얼굴 감지 성공 시 타이머 시작 및 result_page로 전환
    '''
    def update_frame(self):
        if not self.cap.isOpened():
            self.instruction.setText("카메라 연결 실패")
            self.timer.stop()
            return

        ret, frame = self.cap.read()
        if not ret:
            return
        
        # 웹캠 화면 크롭 로직
        h, w, _ = frame.shape
        target_h, target_w = self.TARGET_H, self.TARGET_W
        
        if h > target_h:
            start_y = (h - target_h) // 2
            frame = frame[start_y:start_y + target_h, :]
        if w > target_w:
            start_x = (w - target_w) // 2
            frame = frame[:, start_x:start_x + target_w]

        # 가이드라인 좌표 계산
        guide_width = int(target_w * 0.5) 
        guide_x1 = (target_w - guide_width) // 2
        guide_y1 = (target_h - guide_width) // 2
        guide_x2 = guide_x1 + guide_width
        guide_y2 = guide_y1 + guide_width
        guide = [guide_x1, guide_y1, guide_x2, guide_y2] 
        corner_len = int(guide_width * 0.25) 

        # 얼굴 감지 로직
        faces = detect_faces(frame)
        face_in_guide = False
        for (x, y, fw, fh) in faces:
            cx, cy = x + fw // 2, y + fh // 2
            if guide[0] < cx < guide[2] and guide[1] < cy < guide[3]:
                face_in_guide = True
                break

        # 투명도/상태 제어 로직
        if face_in_guide:
            # 얼굴 인식 중 (깜박임 활성화 / 오버레이 밝게)
            if self.start_time is None:
                self.start_time = time.time()
                self.overlay_frame.setStyleSheet(f"QFrame {{ background-color: rgba(0, 0, 0, 40); border-radius: {self.BORDER_RADIUS}px; }}")

            # 투명도 업데이트 (50 ~ 255 사이에서 왕복)
            self.current_alpha += self.fade_speed * self.fade_direction 
            
            if self.current_alpha <= 50:
                self.current_alpha = 50
                self.fade_direction = 1  # 밝아짐
            elif self.current_alpha >= 255:
                self.current_alpha = 255
                self.fade_direction = -1 # 어두워짐
                
            line_alpha = int(self.current_alpha)

            elapsed = time.time() - self.start_time
            self.instruction.setText(f"얼굴을 인식 중입니다. 잠시만 기다려주세요.")

            '''
            인식 성공 로직 => random.choice를 AI 모델로 대체해야
            현재는 얼굴이 가이드라인 내에 있는지 기준으로 70%확률로 랜덤 성공하도록 설계함
            '''
            if elapsed >= self.duration:
                self.timer.stop()

                # =============================
                # AI 모델 연동 및 인식 시도 부분
                # =============================

                success = random.choice([True, False])
                self.switch_callback("result", (success, self.retries)) 
        else:
            # 얼굴 미감지 시 (깜박임 정지 / 오버레이 어둡게)
            self.start_time = None
            self.instruction.setText("얼굴 인식을 시작하려면 화면을 바라봐주세요.")
            self.overlay_frame.setStyleSheet(f"QFrame {{ background-color: rgba(0, 0, 0, 80); border-radius: {self.BORDER_RADIUS}px; }}")
            self.current_alpha = 255.0 
            line_alpha = 255 

        # L자 코너 가이드라인 그리기

        # QPixmap으로 변환
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, frame.shape[1], frame.shape[0], 3*frame.shape[1], QImage.Format_RGB888)
        qpixmap = QPixmap.fromImage(qimg)
        
        painter = QPainter(qpixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 펜 설정
        line_color_qt = QColor(0, 120, 255, line_alpha) 
        line_thickness = 5
        
        painter.setPen(QPen(line_color_qt, line_thickness, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush) 
        
        # L자 코너 그리기
        painter.drawLine(guide_x1 + corner_len, guide_y1, guide_x1, guide_y1) 
        painter.drawLine(guide_x1, guide_y1 + corner_len, guide_x1, guide_y1)
        painter.drawLine(guide_x2 - corner_len, guide_y1, guide_x2, guide_y1)
        painter.drawLine(guide_x2, guide_y1 + corner_len, guide_x2, guide_y1)
        painter.drawLine(guide_x1 + corner_len, guide_y2, guide_x1, guide_y2)
        painter.drawLine(guide_x1, guide_y2 - corner_len, guide_x1, guide_y2)
        painter.drawLine(guide_x2 - corner_len, guide_y2, guide_x2, guide_y2)
        painter.drawLine(guide_x2, guide_y2 - corner_len, guide_x2, guide_y2)

        painter.end()
        
        # QBitmap 마스킹
        mask = QBitmap(qpixmap.size())
        mask.fill(Qt.color0)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.color1)
        painter.drawRoundedRect(mask.rect(), self.BORDER_RADIUS, self.BORDER_RADIUS)
        painter.end()
        qpixmap.setMask(mask)

        self.video_label.setPixmap(qpixmap)