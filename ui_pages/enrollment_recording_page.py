from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QFrame, QGraphicsOpacityEffect,
    QVBoxLayout
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QSequentialAnimationGroup, QEasingCurve, QAbstractAnimation
from PySide6.QtGui import QPixmap, QImage, QPainter, QBitmap

import cv2
import time

from ui_style import TARGET_W, TARGET_H, BORDER_RADIUS, fade_in_out, GUIDE_STYLE
from .base_page import BasePage

from faceid.face_recognizer import FaceRecognizer, rrect_xyxy

# 단계별 최소 샘플 수 (테스트용으로 4장)
MIN_SAMPLES_PER_INSTRUCTION = 4

# 등록 단계 설정
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
        self.face_rec = face_rec    

        self.TARGET_W, self.TARGET_H = TARGET_W, TARGET_H
        self.BORDER_RADIUS = BORDER_RADIUS

        self.current_step_index = 0
        self.current_instruction_index = 0
        self.set_header_spacing(10)
        self.state = "IDLE"
        self.last_state_change_time = time.time()

        # 🚨 [추가] 마지막으로 샘플을 찍은 시간을 기록할 변수
        self.last_sample_time = 0 
        self.sample_interval = 1  # 0.5초마다 한 장씩 찍기 (속도 조절은 여기서!)
       
        # 샘플 수 계산
        total_instructions = sum(len(step['instructions']) for step in ENROLLMENT_STEPS)
        self.MAX_SAMPLES = total_instructions * MIN_SAMPLES_PER_INSTRUCTION
        self.accum_samples_count = 0
        self.accum_samples_count_current_instruction = 0

        # 얼굴 등록 세션 시작
        self.face_rec.start_enrollment(user_data['name'], user_data.get('student_id', ''))

        self.setStyleSheet("QWidget { background: transparent; }")
        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)
        self.set_header_spacing(-10)

        # 1. 단계 표시 바
        self._init_step_bar(main_layout)
        main_layout.addSpacing(30)

        # 2. 비디오 영역
        self.video_label = QLabel()
        self.video_label.setFixedSize(self.TARGET_W, self.TARGET_H)
        self.video_label.setStyleSheet(f"QLabel {{ background-color: #333333; border-radius: {self.BORDER_RADIUS}px; }}")
        main_layout.addWidget(self.video_label, alignment=Qt.AlignCenter)
        main_layout.addSpacing(60)

        # 3. 오버레이 및 메시지
        self.overlay_frame = QFrame(self.video_label)
        self.overlay_frame.setFixedSize(self.TARGET_W, self.TARGET_H)
        self.set_overlay_opacity(40)  
        self.overlay_frame.setStyleSheet(f"QFrame {{ border-radius: {self.BORDER_RADIUS}px; }}")

        self.overlay_status_label = QLabel(None)
        self.overlay_status_label.setStyleSheet(GUIDE_STYLE)
        self.overlay_status_label.hide()
       
        self.instruction_label = QLabel()
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setStyleSheet(GUIDE_STYLE)
       
        message_container = QWidget()
        message_layout = QVBoxLayout(message_container)
        message_layout.addWidget(self.overlay_status_label, alignment=Qt.AlignCenter)
        message_layout.addWidget(self.instruction_label, alignment=Qt.AlignCenter)

        main_layout.addWidget(message_container)
        main_layout.addStretch(1)

        # 4. 가이드라인 이미지 (동그란 박스)
        self.guide_image_label = QLabel(self.video_label)
        GUIDE_IMAGE_SIZE = 240 # 가이드 크기 살짝 키움
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

        # 5. 타이머 시작
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
       
        self._transition_to_instruction_state()

    def set_overlay_opacity(self, alpha: int):
        self.overlay_frame.setStyleSheet(
            f"QFrame {{ background-color: rgba(0, 0, 0, {alpha}); border-radius: {self.BORDER_RADIUS}px; }}"
        )

    def _init_step_bar(self, parent_layout):
        self.step_indicator_widget = QWidget()
        self.step_layout = QHBoxLayout(self.step_indicator_widget)
        self.step_layout.setSpacing(0)
        self.step_layout.setContentsMargins(0, 0, 0, 0)

        self.progress_bars = []
        self.step_lines = []

        label_fixed_size = 100
        connector_fixed_width = 120

        for i in range(len(ENROLLMENT_STEPS)):
            bar = QLabel(f"{i+1}")
            bar.setFixedSize(label_fixed_size, label_fixed_size)
            bar.setAlignment(Qt.AlignCenter)
            bar.setStyleSheet(self._get_step_style(i, 0))
            self.progress_bars.append(bar)

            if i > 0: self.step_layout.addSpacing(-2)
            self.step_layout.addWidget(bar)

            if i < len(ENROLLMENT_STEPS) - 1:
                connector = QLabel()
                connector.setFixedSize(connector_fixed_width, 3)
                connector.setStyleSheet("background-color: #ffffff; border: none; margin:0; padding:0;")
                self.step_lines.append(connector)
                self.step_layout.addWidget(connector, alignment=Qt.AlignVCenter)

        parent_layout.addWidget(self.step_indicator_widget, alignment=Qt.AlignCenter)
        parent_layout.addSpacing(20)

    def _get_step_style(self, index, state):
        if state in (1, 2):
            bg_color = "#005BAC"
            text_color = "#ffffff"
        else:
            bg_color = "#ffffff"
            text_color = "#000000"
        return f"QLabel {{ background-color: {bg_color}; color: {text_color}; border-radius: 5px; font-size: 22px; border: none; padding: 5px; margin: 0px; min-width: 36px; min-height: 36px; }}"

    def update_frame(self):
        """매 프레임마다 호출되어 얼굴 인식 및 UI 갱신"""
        ret, frame = self.cap.read()
        if not ret: return

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rrect = rrect_xyxy(h,w)
        target_h, target_w = self.TARGET_H, self.TARGET_W

        # 비율 맞춰 크롭
        frame_ratio = w / h
        target_ratio = target_w / target_h
        if frame_ratio > target_ratio:
            new_w = int(h * target_ratio)
            start_x = (w - new_w) // 2
            frame = frame[:, start_x:start_x + new_w]
        elif frame_ratio < target_ratio:
            new_h = int(w / target_ratio)
            start_y = (h - new_h) // 2
            frame = frame[start_y:start_y + new_h, :]
        frame = cv2.resize(frame, (target_w, target_h))

        # 🚨 [수정] 1. AI 모델로 얼굴 특징 및 정보 추출 (가장 중요한 부분)
        # detect_faces 없이 여기서 나온 face_obj를 바로 사용합니다.
        emb, face_obj, is_live = self.face_rec.embed_biggest(frame, rrect, use_skip=True)

        # 🚨 [수정] 2. 가이드 영역 내 얼굴 확인 로직 단순화
        face_in_guide = False
        
        if face_obj is not None:
            bx1, by1, bx2, by2 = map(int, face_obj.bbox)
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2
            
            # 가이드 박스 범위 (화면 중앙 기준 50% 영역)
            guide_margin_w = target_w * 0.25 # 좌우 25%씩 여백 -> 중앙 50%
            guide_margin_h = target_h * 0.20 # 상하 20%씩 여백
            
            if (guide_margin_w < cx < target_w - guide_margin_w) and \
               (guide_margin_h < cy < target_h - guide_margin_h):
                face_in_guide = True

        # --- 상태 진행 로직 ---
        if self.current_step_index >= len(ENROLLMENT_STEPS):
            self.timer.stop()
            self.show_overlay_message("등록 완료!", 1000)
            return

        current_step = ENROLLMENT_STEPS[self.current_step_index]

        if self.state in ["SHOW_INSTRUCTION", "WAIT_INSTRUCTION_TIME"]:
            if self.current_instruction_index >= len(current_step["instructions"]):
                self._transition_instruction_complete()
                return

            current_instruction_data = current_step["instructions"][self.current_instruction_index]
            current_instruction = current_instruction_data["text"]
            required_samples = current_instruction_data["min_samples"]

            if self.accum_samples_count_current_instruction < required_samples:
                # 🚨 [수정] 가이드 안에 있고 + AI가 특징을 뽑았으면(emb) -> 저장

                # 현재 시간 확인
                current_time = time.time()

                if face_in_guide and emb is not None:

                    # 🚨 [추가] 마지막 촬영 후 0.5초가 지났는지 확인
                    if current_time - self.last_sample_time >= self.sample_interval:
                        self.last_sample_time = current_time  # 촬영 시간 갱신

                        self.set_overlay_opacity(0)
                        if self.guide_animation.state() != QAbstractAnimation.Running:
                            self.guide_animation.start()

                        # 샘플 저장 및 전송
                        _, self.accum_samples_count = self.face_rec.accumulate_sample(frame)
                        self.accum_samples_count_current_instruction += 1

                        self.instruction_label.setText(f"{current_instruction}\n({self.accum_samples_count_current_instruction}/{required_samples})")
                        self.state = "WAIT_INSTRUCTION_TIME"
                    else:
                        # 0.5초가 아직 안 지났으면, 화면은 정상이지만 저장은 안 함 (그냥 통과)
                        # 사용자에게는 "잘 하고 있어요" 느낌만 줌
                        self.set_overlay_opacity(0)
                        self.overlay_frame.setStyleSheet(f"QFrame {{ background-color: transparent; border-radius: {self.BORDER_RADIUS}px; }}")
                        pass
                else:
                    self.set_overlay_opacity(40)
                    if self.guide_animation.state() == QAbstractAnimation.Running:
                        self.guide_animation.stop()
                    self.guide_opacity_effect.setOpacity(1.0)
                    self.instruction_label.setText(f"{current_instruction}\n※ 화면 중앙에 얼굴을 맞춰주세요 ※")
                    self.state = "SHOW_INSTRUCTION"
            else:
                self._transition_instruction_complete()
                return

        elif self.state == "IDLE":
            self.state = "SHOW_START_MESSAGE"
            self.last_state_change_time = time.time()

        elif self.state == "SHOW_START_MESSAGE":
            self.show_overlay_message(f"{self.current_step_index + 1}단계 촬영 시작!", duration_ms=2000, finished_callback=self._transition_to_instruction_state)
            self.last_state_change_time = time.time()
            self.state = "WAIT_OVERLAY"

        elif self.state == "WAIT_OVERLAY":
            pass
       
        elif self.state == "SHOW_END_MESSAGE":
            self.instruction_label.setText("")
            self.show_overlay_message(f"{self.current_step_index + 1}단계 완료!", duration_ms=2000)
            QTimer.singleShot(2500, self._transition_to_next_step)
            self.state = "WAIT_OVERLAY_END"

        elif self.state == "WAIT_OVERLAY_END":
            pass

        # 화면 그리기
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, frame.shape[1], frame.shape[0], 3*frame.shape[1], QImage.Format_RGB888)
        qpixmap = QPixmap.fromImage(qimg)
        
        # 둥근 모서리 마스킹
        mask = QBitmap(qpixmap.size())
        mask.fill(Qt.color0)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.color1)
        painter.drawRoundedRect(mask.rect(), self.BORDER_RADIUS, self.BORDER_RADIUS)
        painter.end()
        qpixmap.setMask(mask)
        self.video_label.setPixmap(qpixmap)

    def _transition_instruction_complete(self):
        self.progress_bars[self.current_step_index].setStyleSheet(self._get_step_style(self.current_step_index, 2))
        current_step = ENROLLMENT_STEPS[self.current_step_index]
        self.current_instruction_index += 1
        self.accum_samples_count_current_instruction = 0
        self.last_state_change_time = time.time()
       
        if self.current_instruction_index < len(current_step["instructions"]):
            self.state = "SHOW_INSTRUCTION"
        else:
            self.state = "SHOW_END_MESSAGE"
            return

    def _transition_to_instruction_state(self):
        try:
            if self.current_step_index < len(ENROLLMENT_STEPS) and self.accum_samples_count < self.MAX_SAMPLES:
                self.current_instruction_index = 0
                self.accum_samples_count_current_instruction = 0
                self.progress_bars[self.current_step_index].setStyleSheet(self._get_step_style(self.current_step_index, 1))
                self.instruction_label.show()
                self.state = "SHOW_INSTRUCTION"
            else:
                self.state = "SHOW_END_MESSAGE"
        except RuntimeError: pass

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
                # 🚨 [수정] 등록 완료 처리
                success = self.face_rec.finish_enrollment()
                if success:
                    self.switch_callback("result", self.user_data, mode="enroll")
                else:
                    self.switch_callback("enrollment_input") # 실패시 처음으로
        except RuntimeError: pass

    def show_overlay_message(self, text, duration_ms=2000, finished_callback=None):
        try:
            if self.instruction_label.parent(): self.instruction_label.hide()
        except RuntimeError: pass
        self.overlay_status_label.setText(text)
        try:
            effect = self.overlay_status_label.graphicsEffect()
            if effect: effect.setOpacity(0.0)
        except RuntimeError: pass
        fade_in_out(self.overlay_status_label, visible_ms=duration_ms, finished_callback=finished_callback)

    def closeEvent(self, event):
        self.timer.stop()
        if hasattr(self, 'guide_animation') and self.guide_animation.state() == QAbstractAnimation.Running:
            self.guide_animation.stop()
        if hasattr(self, 'guide_animation'):
            self.guide_animation.deleteLater()
        super().closeEvent(event)