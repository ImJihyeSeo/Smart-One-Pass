from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QFrame, QGraphicsOpacityEffect,
    QVBoxLayout
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QSequentialAnimationGroup, QEasingCurve, QAbstractAnimation
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBitmap

import cv2
import time

from ui_style import TARGET_W, TARGET_H, BORDER_RADIUS, fade_in_out, scale_value
from cv_tools import detect_faces
from .base_page import BasePage

from faceid.face_recognizer import FaceRecognizer

# 단계별 최소 샘플 수
MIN_SAMPLES_PER_INSTRUCTION = 4

# 등록 단계별 [클립 번호 / 시간 / 안내 메시지] 리스트
ENROLLMENT_STEPS = [
    {"clip": 1, "duration": 10, "instructions": [
        {"text": "정면을 보고 무표정을 유지하세요", "min_samples": MIN_SAMPLES_PER_INSTRUCTION},
        {"text": "정면을 보고 미소를 유지하세요", "min_samples": MIN_SAMPLES_PER_INSTRUCTION}
    ]},
    {"clip": 2, "duration": 15, "instructions": [
        {"text": "고개를 왼쪽으로 살짝 돌리세요", "min_samples": MIN_SAMPLES_PER_INSTRUCTION},
        {"text": "정면으로 돌아오세요", "min_samples": MIN_SAMPLES_PER_INSTRUCTION},
        {"text": "고개를 오른쪽으로 살짝 돌리세요", "min_samples": MIN_SAMPLES_PER_INSTRUCTION},
        {"text": "정면으로 돌아오세요", "min_samples": MIN_SAMPLES_PER_INSTRUCTION}
    ]},
    {"clip": 3, "duration": 10, "instructions": [
        {"text": "고개를 위로 살짝 올리세요", "min_samples": MIN_SAMPLES_PER_INSTRUCTION},
        {"text": "정면으로 돌아오세요", "min_samples": MIN_SAMPLES_PER_INSTRUCTION},
        {"text": "고개를 아래로 살짝 내리세요", "min_samples": MIN_SAMPLES_PER_INSTRUCTION},
        {"text": "정면으로 돌아오세요", "min_samples": MIN_SAMPLES_PER_INSTRUCTION}
    ]},
]

class EnrollmentRecordingPage(BasePage):
    def __init__(self, switch_callback, user_data, cap, face_rec: FaceRecognizer):
        super().__init__(switch_callback)
        self.switch_callback = switch_callback
        self.user_data = user_data
        self.cap = cap
        self.face_rec = face_rec    # AI 모델 인스턴스

        self.TARGET_W, self.TARGET_H = TARGET_W, TARGET_H
        self.BORDER_RADIUS = BORDER_RADIUS

        self.current_step_index = 0
        self.current_instruction_index = 0
        self.set_header_spacing(10)
        self.state = "IDLE"
        self.last_state_change_time = time.time()
        self.clip_start_time = None
       
        # 샘플 관련 초기화
        total_instructions = sum(len(step['instructions']) for step in ENROLLMENT_STEPS)
        self.MAX_SAMPLES = total_instructions * MIN_SAMPLES_PER_INSTRUCTION
        self.accum_samples_count = 0
        self.accum_samples_count_current_instruction = 0

        # 얼굴 등록 시작
        self.face_rec.start_enrollment(user_data['name'], user_data.get('student_id', ''))

        self.setStyleSheet("QWidget { background: transparent; }")
        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)
        self.set_header_spacing(scale_value(-10))

        # --------------------------
        # 단계 표시 바
        # --------------------------
        self._init_step_bar(main_layout)

        # --------------------------
        # 비디오 영역
        # --------------------------
        self.video_label = QLabel()
        self.video_label.setFixedSize(self.TARGET_W, self.TARGET_H)
        self.video_label.setStyleSheet(f"QLabel {{ background-color: #333333; border-radius: {self.BORDER_RADIUS}px; }}")
        main_layout.addWidget(self.video_label, alignment=Qt.AlignCenter)

        # 오버레이 프레임
        self.overlay_frame = QFrame(self.video_label)
        self.overlay_frame.setFixedSize(self.TARGET_W, self.TARGET_H)
        self.set_overlay_opacity(40)  
        self.overlay_frame.setStyleSheet(f"QFrame {{ border-radius: {self.BORDER_RADIUS}px; }}")

        # 상태 메시지 라벨
        self.overlay_status_label = QLabel(None)
        self.overlay_status_label.setStyleSheet("""
            font-size: 22px;
            color: white;
            background-color: transparent;
            border-radius: 10px;
            padding: 10px;
        """)
        self.overlay_status_label.hide()
       
        # 안내 메시지 라벨
        self.instruction_label = QLabel()
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setStyleSheet("font-size: 22px; color: #ffffff; margin-top: 20px;")
       
        message_container = QWidget()
        message_layout = QVBoxLayout(message_container)
        message_layout.addWidget(self.overlay_status_label, alignment=Qt.AlignCenter)
        message_layout.addWidget(self.instruction_label, alignment=Qt.AlignCenter)

        main_layout.addWidget(message_container)
        main_layout.addStretch(1)

        # --------------------------
        # 가이드라인
        # --------------------------
        self.guide_image_label = QLabel(self.video_label)
        GUIDE_IMAGE_SIZE = scale_value(130)
        self.guide_image_label.setFixedSize(GUIDE_IMAGE_SIZE, GUIDE_IMAGE_SIZE)
        self.guide_image_label.setStyleSheet("background: transparent;")
        self.guide_image_label.move(
            (self.TARGET_W - GUIDE_IMAGE_SIZE) // 2,
            (self.TARGET_H - GUIDE_IMAGE_SIZE) // 2
        )
        guide_pixmap = QPixmap("resources/guide_frame.png")
        if not guide_pixmap.isNull():
            self.guide_image_label.setPixmap(
                guide_pixmap.scaled(GUIDE_IMAGE_SIZE, GUIDE_IMAGE_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        self.guide_opacity_effect = QGraphicsOpacityEffect(self.guide_image_label)
        self.guide_image_label.setGraphicsEffect(self.guide_opacity_effect)

        anim1 = QPropertyAnimation(self.guide_opacity_effect, b"opacity")
        anim1.setDuration(1200); anim1.setStartValue(0.8); anim1.setEndValue(0.2); anim1.setEasingCurve(QEasingCurve.InOutQuad)
        anim2 = QPropertyAnimation(self.guide_opacity_effect, b"opacity")
        anim2.setDuration(1200); anim2.setStartValue(0.2); anim2.setEndValue(0.8); anim2.setEasingCurve(QEasingCurve.InOutQuad)

        self.guide_animation = QSequentialAnimationGroup(self.guide_image_label)
        self.guide_animation.addAnimation(anim1)
        self.guide_animation.addAnimation(anim2)
        self.guide_animation.setLoopCount(-1)

        # --------------------------
        # 프레임 업데이트 타이머
        # --------------------------
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
       
        self._transition_to_instruction_state()

    # 오버레이 투명도 설정
    def set_overlay_opacity(self, alpha: int):
        self.overlay_frame.setStyleSheet(
            f"QFrame {{ background-color: rgba(0, 0, 0, {alpha}); border-radius: {self.BORDER_RADIUS}px; }}"
        )

    # 단계별 진행 바 초기화
    def _init_step_bar(self, parent_layout):
        self.step_indicator_widget = QWidget()
        self.step_layout = QHBoxLayout(self.step_indicator_widget)
        self.step_layout.setSpacing(0)
        self.step_layout.setContentsMargins(0, 0, 0, 0)

        self.progress_bars = []
        self.step_lines = []

        label_fixed_size = 28
        connector_fixed_width = 50

        for i in range(len(ENROLLMENT_STEPS)):
            bar = QLabel(f"{i+1}")
            bar.setFixedSize(label_fixed_size, label_fixed_size)
            bar.setAlignment(Qt.AlignCenter)
            bar.setStyleSheet(self._get_step_style(i, 0))
            self.progress_bars.append(bar)

            if i > 0:
                self.step_layout.addSpacing(-2)

            self.step_layout.addWidget(bar)

            if i < len(ENROLLMENT_STEPS) - 1:
                connector = QLabel()
                connector.setFixedSize(connector_fixed_width, 2)
                connector.setStyleSheet("background-color: #ffffff; border: none; margin:0; padding:0;")
                self.step_lines.append(connector)
                self.step_layout.addWidget(connector, alignment=Qt.AlignVCenter)

        parent_layout.addWidget(self.step_indicator_widget, alignment=Qt.AlignCenter)
        parent_layout.addSpacing(10)

    # 단계별 진행 바 스타일
    def _get_step_style(self, index, state):
        if state in (1, 2):
            bg_color = "#005BAC"
            text_color = "#ffffff"
        else:
            bg_color = "#ffffff"
            text_color = "#000000"
        return f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 5px;
                font-weight: bold;
                border: none;
                padding: 0px;
                margin: 0px;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }}
        """

    # --------------------------
    # 프레임 업데이트
    # --------------------------
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret: return

        frame = cv2.flip(frame, 1)  # 좌우 반전
        h, w, _ = frame.shape
        target_h, target_w = self.TARGET_H, self.TARGET_W

        frame_ratio = w / h
        target_ratio = target_w / target_h
        
        if frame_ratio > target_ratio:
            # 웹캠 영상이 타겟보다 넓은 경우 (좌우 크롭)
            new_w = int(h * target_ratio)
            start_x = (w - new_w) // 2
            frame = frame[:, start_x:start_x + new_w]
        elif frame_ratio < target_ratio:
            # 웹캠 영상이 타겟보다 좁은 경우 (상하 크롭)
            new_h = int(w / target_ratio)
            start_y = (h - new_h) // 2
            frame = frame[start_y:start_y + new_h, :]

        # 크롭된 프레임 타겟 크기로 리사이즈해서 채우기
        frame = cv2.resize(frame, (target_w, target_h))

        # 얼굴 감지 (UI 상태 관리)
        guide_width = int(target_w * 0.5)
        guide_x1 = (target_w - guide_width) // 2
        guide_y1 = (target_h - guide_width) // 2
        guide_x2 = guide_x1 + guide_width
        guide_y2 = guide_y1 + guide_width

        faces = detect_faces(frame)
        face_in_guide = False
        for (x, y, fw, fh) in faces:
            cx, cy = x + fw // 2, y + fh // 2
            if guide_x1 < cx < guide_x2 and guide_y1 < cy < guide_y2:
                face_in_guide = True
                break
       
        emb, _ = self.face_rec.embed_biggest(frame)

        # UI 상태 전환 / 샘플 누적 처리
        if self.current_step_index >= len(ENROLLMENT_STEPS):
            self.timer.stop()
            self.show_overlay_message("등록 완료 (시스템 오류 방지)", 1000)
            return

        current_step = ENROLLMENT_STEPS[self.current_step_index]

        if self.state in ["SHOW_INSTRUCTION", "WAIT_INSTRUCTION_TIME"]:
            if self.current_instruction_index >= len(current_step["instructions"]):
                self._transition_instruction_complete()
                return

            current_instruction_data = current_step["instructions"][self.current_instruction_index]
            current_instruction = current_instruction_data["text"]
            required_samples = current_instruction_data["min_samples"]

            # 얼굴 감지 시 샘플 누적
            if self.accum_samples_count_current_instruction < required_samples:
                if face_in_guide and emb is not None:
                    self.set_overlay_opacity(0)
                    if self.guide_animation.state() != QAbstractAnimation.Running:
                        self.guide_animation.start()

                    _, self.accum_samples_count = self.face_rec.accumulate_sample(frame)
                    self.accum_samples_count_current_instruction += 1

                    self.instruction_label.setText(f"{current_instruction}\n")
                    self.state = "WAIT_INSTRUCTION_TIME"
                else:
                    # 얼굴 미감지 시 누적 안 함
                    self.set_overlay_opacity(40)
                    if self.guide_animation.state() == QAbstractAnimation.Running:
                        self.guide_animation.stop()
                    self.guide_opacity_effect.setOpacity(1.0)
                    self.instruction_label.setText(f"{current_instruction}\n※ 화면 중앙에 얼굴을 위치시켜주세요 ※")
                    self.state = "SHOW_INSTRUCTION"
            else:
                # 샘플 확보 -> 다음 지침/단계
                self._transition_instruction_complete()
                return

        elif self.state == "IDLE":
            self.state = "SHOW_START_MESSAGE"
            self.last_state_change_time = time.time()

        elif self.state == "SHOW_START_MESSAGE":
            self.show_overlay_message(f"{self.current_step_index + 1}번째 촬영 시작!", duration_ms=2000, finished_callback=self._transition_to_instruction_state)
            self.last_state_change_time = time.time()
            self.state = "WAIT_OVERLAY"

        elif self.state == "WAIT_OVERLAY":
            pass
       
        elif self.state == "SHOW_END_MESSAGE":
            self.instruction_label.setText("")
            self.show_overlay_message(f"{self.current_step_index + 1}번째 촬영 완료!", duration_ms=2000)
            QTimer.singleShot(2500, self._transition_to_next_step)
            self.state = "WAIT_OVERLAY_END"

        elif self.state == "WAIT_OVERLAY_END":
            pass

        # --------------------------
        # QPixmap 변환
        # --------------------------
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, frame.shape[1], frame.shape[0], 3*frame.shape[1], QImage.Format_RGB888)
        qpixmap = QPixmap.fromImage(qimg)
        mask = QBitmap(qpixmap.size())
        mask.fill(Qt.color0)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.color1)
        painter.drawRoundedRect(mask.rect(), self.BORDER_RADIUS, self.BORDER_RADIUS)
        painter.end()
        qpixmap.setMask(mask)
        self.video_label.setPixmap(qpixmap)

    # 현재 지침 완료 시 상태 전환
    def _transition_instruction_complete(self):
        self.progress_bars[self.current_step_index].setStyleSheet(self._get_step_style(self.current_step_index, 2))
        current_step = ENROLLMENT_STEPS[self.current_step_index]
        self.current_instruction_index += 1
        self.accum_samples_count_current_instruction = 0
        self.last_state_change_time = time.time()
       
        # 다음 지침 남았는지 확인
        if self.current_instruction_index < len(current_step["instructions"]):
            self.state = "SHOW_INSTRUCTION"
        else:
            self.state = "SHOW_END_MESSAGE" # 다음 단계 전환
            return

    # SHOW_START_MESSAGE -> SHOW_INSTRUCTION로 상태 전환
    def _transition_to_instruction_state(self):
        try:
            if self.current_step_index < len(ENROLLMENT_STEPS) and self.accum_samples_count < self.MAX_SAMPLES:
                self.current_instruction_index = 0
                self.accum_samples_count_current_instruction = 0
                self.progress_bars[self.current_step_index].setStyleSheet(self._get_step_style(self.current_step_index, 1))
                self.instruction_label.show()
                self.state = "SHOW_INSTRUCTION"
                self.last_state_change_time = time.time()
            else:
                self.state = "SHOW_END_MESSAGE"
                self.last_state_change_time = time.time()
        except RuntimeError:
            pass

    # 다음 단계로 이동
    def _transition_to_next_step(self):
        try:
            if self.current_step_index < len(self.step_lines):
                self.step_lines[self.current_step_index].setStyleSheet("background-color: #005BAC; border: none; margin:0; padding:0;")
            if self.current_step_index < len(ENROLLMENT_STEPS):
                self.progress_bars[self.current_step_index].setStyleSheet(self._get_step_style(self.current_step_index, 2))

            self.current_step_index += 1
           
            if self.current_step_index < len(ENROLLMENT_STEPS) and self.accum_samples_count < self.MAX_SAMPLES:
                self.current_instruction_index = 0
                self.accum_samples_count_current_instruction = 0
                self.state = "SHOW_START_MESSAGE"
            else:
                self.show_overlay_message("촬영 완료!")
                self.timer.stop()
                success = self.face_rec.finish_enrollment()
                self.switch_callback("result", self.user_data, mode="enroll")
        except RuntimeError:
            pass

    def show_overlay_message(self, text, duration_ms=2000, finished_callback=None):
        try:
            if self.instruction_label.parent():
                self.instruction_label.hide()
        except RuntimeError:
            pass
        self.overlay_status_label.setText(text)
        try:
            effect = self.overlay_status_label.graphicsEffect()
            if effect:
                effect.setOpacity(0.0)
        except RuntimeError:
            pass
        fade_in_out(self.overlay_status_label, visible_ms=duration_ms, finished_callback=finished_callback)

    def closeEvent(self, event):
        self.timer.stop()
        if hasattr(self, 'guide_animation') and self.guide_animation.state() == QAbstractAnimation.Running:
            self.guide_animation.stop()
        if hasattr(self, 'guide_animation'):
            self.guide_animation.deleteLater()
        super().closeEvent(event)
