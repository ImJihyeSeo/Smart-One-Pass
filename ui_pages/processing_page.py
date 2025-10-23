import cv2
import time

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout,
    QGraphicsDropShadowEffect, QFrame,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QAbstractAnimation, QEasingCurve, QSequentialAnimationGroup
from PySide6.QtGui import QPixmap, QImage, QPainter, QBitmap, QColor

from ui_style import TARGET_W, TARGET_H, MESSAGE_AREA_HEIGHT, BORDER_RADIUS 
from cv_tools import detect_faces
from .base_page import BasePage

from faceid.face_recognizer import FaceRecognizer


'''
웹캠 화면 표시하고, 얼굴 인식 과정을 시각적으로 처리해 결과를 result_page로 넘기는 페이지
'''
class ProcessingPage(BasePage):
    '''
    UI 구성, QTimer 시작
    '''
    def __init__(self, switch_callback, cap, retries, face_rec: FaceRecognizer): 
        super().__init__(switch_callback)

        # 상태 변수 초기화
        self.cap = cap
        self.retries = retries
        self.face_rec = face_rec  # AI 모델 인스턴스

        self.start_time = None
        self.duration = 3.0

        self.TARGET_W, self.TARGET_H = TARGET_W, TARGET_H 
        self.BORDER_RADIUS = BORDER_RADIUS
        self.set_header_spacing(10) # 공통 헤더 하단 여백 조정
        self.setStyleSheet("QWidget { background: transparent; }")

        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)

        # 비디오 영역
        self.video_label = QLabel()
        self.video_label.setFixedSize(self.TARGET_W, self.TARGET_H)
        self.video_label.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                border-radius: {self.BORDER_RADIUS}px;
            }}
        """)

        # 가이드라인
        GUIDE_IMAGE_SIZE = 130

        self.guide_image_label = QLabel(self.video_label) # video_label을 부모로 설정
        self.guide_image_label.setFixedSize(GUIDE_IMAGE_SIZE, GUIDE_IMAGE_SIZE)
        self.guide_image_label.setStyleSheet("background: transparent;")

        self.guide_image_label.move(
            (self.TARGET_W - GUIDE_IMAGE_SIZE) // 2,
            (self.TARGET_H - GUIDE_IMAGE_SIZE) // 2
        )

        self.guide_pixmap = QPixmap("resources/guide_frame.png")
        if not self.guide_pixmap.isNull():
            scaled_pixmap = self.guide_pixmap.scaled(
                GUIDE_IMAGE_SIZE, GUIDE_IMAGE_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.guide_image_label.setPixmap(scaled_pixmap)
        else:
            print("경고: 가이드라인 PNG 파일을 로드할 수 없습니다.")

        self.guide_opacity_effect = QGraphicsOpacityEffect(self.guide_image_label)
        self.guide_image_label.setGraphicsEffect(self.guide_opacity_effect)

        # 가이드라인 애니메이션
        anim1 = QPropertyAnimation(self.guide_opacity_effect, b"opacity")
        anim1.setDuration(1200); anim1.setStartValue(0.8); anim1.setEndValue(0.2); anim1.setEasingCurve(QEasingCurve.InOutQuad)
        anim2 = QPropertyAnimation(self.guide_opacity_effect, b"opacity")
        anim2.setDuration(1200); anim2.setStartValue(0.2); anim2.setEndValue(0.8); anim2.setEasingCurve(QEasingCurve.InOutQuad)

        self.guide_animation = QSequentialAnimationGroup()
        self.guide_animation.setParent(self)
        self.guide_animation.addAnimation(anim1)
        self.guide_animation.addAnimation(anim2)
        self.guide_animation.setLoopCount(-1)

        # 반투명 오버레이 프레임
        self.overlay_frame = QFrame(self.video_label) 
        self.overlay_frame.setFixedSize(self.TARGET_W, self.TARGET_H)
        self.overlay_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 80); 
                border-radius: {self.BORDER_RADIUS}px;
            }}
        """)

        # 입체감 부여
        shadow = QGraphicsDropShadowEffect(self.video_label)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.video_label.setGraphicsEffect(shadow)     

        # 메시지 영역
        self.message_container = QWidget()
        self.message_container.setFixedHeight(MESSAGE_AREA_HEIGHT)
        self.message_container.setStyleSheet("background: transparent;")

        message_layout = QVBoxLayout(self.message_container)
        message_layout.setContentsMargins(0, 0, 0, 0)
        
        self.instruction = QLabel("얼굴 인식을 시작하려면 화면을 바라봐주세요.")
        self.instruction.setAlignment(Qt.AlignCenter)
        self.instruction.setStyleSheet("font-size: 18px; color: #ffffff; background: transparent;")
        
        message_layout.addWidget(self.instruction)
        
        main_layout.addStretch(1)
        main_layout.addWidget(self.video_label, 0, Qt.AlignCenter)
        main_layout.addStretch(1)
        main_layout.addWidget(self.message_container)
        main_layout.addStretch(1)
        main_layout.setContentsMargins(0, 0, 0, 0) 

        self.setLayout(main_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self):
        if not self.cap.isOpened():
            self.instruction.setText("카메라 연결 실패")
            self.timer.stop()
            return

        ret, frame = self.cap.read()
        if not ret:
            return
        
        # 웹캠 화면 크롭 로직
        frame = cv2.flip(frame, 1) # 좌우 반전
        h, w, _ = frame.shape
        target_h, target_w = self.TARGET_H, self.TARGET_W
        
        if h > target_h:
            start_y = (h - target_h) // 2
            frame = frame[start_y:start_y + target_h, :]
        if w > target_w:
            start_x = (w - target_w) // 2
            frame = frame[:, start_x:start_x + target_w]

        # --------------------------
        # AI 모델 / 감지 로직
        # --------------------------
        # 가이드 영역
        guide_width = int(target_w * 0.5)
        guide_x1 = (target_w - guide_width) // 2
        guide_y1 = (target_h - guide_width) // 2
        guide_x2 = guide_x1 + guide_width
        guide_y2 = guide_y1 + guide_width
        
        # 얼굴 감지 / 임베딩 추출
        emb, face_obj = self.face_rec.embed_biggest(frame)

        # 가이드라인 영역에 얼굴 중심 있는지 확인하는 로직으로 UI 상태만 제어
        faces_legacy = detect_faces(frame)
        face_in_guide = False
        for (x, y, fw, fh) in faces_legacy:
            cx, cy = x + fw // 2, y + fh // 2
            if guide_x1 < cx < guide_x2 and guide_y1 < cy < guide_y2:
                face_in_guide = True
                break
        
        # --------------------------
        # UI 상태 제어
        # --------------------------
        if face_in_guide and emb is not None: # 얼굴이 UI 가이드라인 내 + AI가 임베딩을 추출
            # 얼굴 인식 중
            if self.start_time is None:
                self.start_time = time.time()
                self.overlay_frame.setStyleSheet(f"QFrame {{ background-color: rgba(0, 0, 0, 40); border-radius: {self.BORDER_RADIUS}px; }}")

            if self.guide_image_label.isVisible() and self.guide_animation.state() != QAbstractAnimation.Running:
                self.guide_animation.start()
                
            self.instruction.setText(f"얼굴을 인식 중입니다. 잠시만 기다려주세요.")

            elapsed = time.time() - self.start_time
            if elapsed >= self.duration:
                self.timer.stop()
                self.guide_animation.stop()

                # 얼굴 식별 - AI 모델
                success, name, similarity = self.face_rec.identify_face(emb)
                
                # result_page로 결과 데이터 전달
                result_data = (success, self.retries, name) 
                self.switch_callback("result", result_data) 
        else:
            # 얼굴 미감지 시
            if self.guide_animation.state() == QAbstractAnimation.Running:
                self.guide_animation.stop()
            self.guide_opacity_effect.setOpacity(1.0) 
            self.start_time = None
            self.instruction.setText("얼굴 인식을 시작하려면 화면을 바라봐주세요.")
            self.overlay_frame.setStyleSheet(f"QFrame {{ background-color: rgba(0, 0, 0, 80); border-radius: {self.BORDER_RADIUS}px; }}")

        # QPixmap으로 변환
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, frame.shape[1], frame.shape[0], 3*frame.shape[1], QImage.Format_RGB888)
        qpixmap = QPixmap.fromImage(qimg)
        
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

    def closeEvent(self, event):
        if hasattr(self, 'guide_animation') and self.guide_animation.state() == QAbstractAnimation.Running:
            self.guide_animation.stop()
        self.timer.stop()
        super().closeEvent(event)
