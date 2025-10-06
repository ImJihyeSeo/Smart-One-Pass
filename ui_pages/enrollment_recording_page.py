from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBitmap

import cv2
import time

from config import TARGET_W, TARGET_H, BORDER_RADIUS
from ui_style import fade_in_out
from cv_tools import detect_faces
from .base_page import BasePage

# 등록 단계별 [클립 번호 / 시간 / 안내 메시지] 리스트
ENROLLMENT_STEPS = [
    {"clip": 1, "duration": 10, "instructions": [
        "정면을 보고 무표정을 5초 유지하세요", 
        "정면을 보고 미소를 5초 유지하세요"
    ]},
    {"clip": 2, "duration": 15, "instructions": [
        "고개를 천천히 왼쪽으로 돌리세요", 
        "다시 정면으로 돌아오세요",
        "고개를 천천히 오른쪽으로 돌리세요",
        "다시 정면으로 돌아오세요"
    ]},
    {"clip": 3, "duration": 10, "instructions": [
        "고개를 천천히 위로 올리세요", 
        "고개를 다시 천천히 아래로 내려 정면으로 돌아오세요"
    ]},
]

class EnrollmentRecordingPage(BasePage):
    def __init__(self, switch_callback, user_data, cap):
        super().__init__(switch_callback)
        self.switch_callback = switch_callback
        self.user_data = user_data
        self.TARGET_W, self.TARGET_H = TARGET_W, TARGET_H
        self.BORDER_RADIUS = BORDER_RADIUS
        self.setStyleSheet("QWidget { background: transparent; }") 
        self.current_step_index = 0
        self.current_instruction_index = 0
        self.clip_start_time = None
        self.frame_count = 0
        self.recording = False
        self.set_header_spacing(10) # 공통 헤더 하단 여백 조정
        self.cap = cap

        self.state = "IDLE"
        self.last_state_change_time = time.time()
        
        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)

        # 단계 표시 바 구성
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
            bar_style = self._get_step_style(i, 0) + f"""
                QLabel {{
                    min-width: {label_fixed_size}px;
                    max-width: {label_fixed_size}px;
                    margin: 0px; 
                    padding: 0px;
                }}
            """
            bar.setStyleSheet(bar_style)
            self.progress_bars.append(bar)
            
            if i > 0:
                self.step_layout.addSpacing(-2) # 단계 간격 조정

            self.step_layout.addWidget(bar)
            
            # 단계 사이 연결선
            if i < len(ENROLLMENT_STEPS) - 1:
                connector = QLabel()
                connector.setFixedSize(connector_fixed_width, 2)
                connector.setStyleSheet("""
                    background-color: #ffffff;
                    border: none;
                    margin-left: -2px;
                    margin-right: -2px;
                    padding: 0px;
                """)
                self.step_lines.append(connector)
                self.step_layout.addWidget(connector, alignment=Qt.AlignVCenter)

        main_layout.addWidget(self.step_indicator_widget, alignment=Qt.AlignCenter)
        main_layout.addSpacing(10)

        # 비디오 영역
        self.video_label = QLabel()
        self.video_label.setFixedSize(self.TARGET_W, self.TARGET_H)
        self.video_label.setStyleSheet(f"QLabel {{ background-color: #333333; border-radius: {self.BORDER_RADIUS}px; }}")

        self.overlay_frame = QFrame(self.video_label)
        self.overlay_frame.setFixedSize(self.TARGET_W, self.TARGET_H)
        self.overlay_frame.setStyleSheet(f"QFrame {{ background-color: rgba(0, 0, 0, 0); border-radius: {self.BORDER_RADIUS}px; }}")

        main_layout.addWidget(self.video_label, alignment=Qt.AlignCenter)

        # 비디오 영역 중앙에 표시할 상태 메시지 영역
        self.overlay_status_label = QLabel(self.overlay_frame)
        self.overlay_status_label.setAlignment(Qt.AlignCenter)
        self.overlay_status_label.setStyleSheet("""
            font-size: 22px; 
            color: white; 
            background-color: transparent; 
            border-radius: 10px;
            padding: 10px;
        """)
        self.overlay_status_label.setFixedSize(360, 50)
        self.overlay_status_label.move(
            (self.TARGET_W - self.overlay_status_label.width()) // 2,
            (self.TARGET_H - self.overlay_status_label.height()) // 2
        )
        self.overlay_status_label.hide()

        # 안내 메시지 영역
        self.instruction_label = QLabel()
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setStyleSheet("font-size: 18px; color: #ffffff; margin-top: 20px;")
        self.instruction_label.setText("")
        main_layout.addWidget(self.instruction_label)
        main_layout.addStretch(1)

        # 타이머 시작 (30ms 간격으로 update_frame 호출)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    # 상태 메시지 띄우는 함수
    def show_overlay_message(self, text, duration_ms=2000):
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

        fade_in_out(self.overlay_status_label, visible_ms=duration_ms) 
        
    # 단계 표시 바 스타일 정의 함수
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

    # 웹캠 화면에서 프레임 읽기, 얼굴 감지, UI 업데이트
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret: 
            return

        # ProcessingPage와 유사한 로직

        # 크롭 로직
        h, w, _ = frame.shape
        target_h, target_w = self.TARGET_H, self.TARGET_W
        
        if h > target_h:
            start_y = (h - target_h) // 2
            frame = frame[start_y:start_y + target_h, :]
        if w > target_w:
            start_x = (w - target_w) // 2
            frame = frame[:, start_x:start_x + target_w]

        # 가이드라인 좌표
        guide_width = int(target_w * 0.5) 
        guide_x1 = (target_w - guide_width) // 2
        guide_y1 = (target_h - guide_width) // 2
        guide_x2 = guide_x1 + guide_width
        guide_y2 = guide_y1 + guide_width
        corner_len = int(guide_width * 0.25) 

        # 얼굴 감지 및 가이드라인 내 얼굴 위치 확인
        faces = detect_faces(frame)
        face_in_guide = False
        for (x, y, fw, fh) in faces:
            cx, cy = x + fw // 2, y + fh // 2
            if guide_x1 < cx < guide_x2 and guide_y1 < cy < guide_y2:
                face_in_guide = True
                break

        # 가이드라인 투명도 처리 - 얼굴 들어왔을 때 투명하게, 아니면 어둡게
        if face_in_guide:
            self.overlay_frame.setStyleSheet(f"QFrame {{ background-color: rgba(0, 0, 0, 0); border-radius: {self.BORDER_RADIUS}px; }}")
            line_alpha = 255
        else:
            self.overlay_frame.setStyleSheet(f"QFrame {{ background-color: rgba(0, 0, 0, 40); border-radius: {self.BORDER_RADIUS}px; }}")
            line_alpha = 255

        # 단계 표시 바 업데이트
        for i in range(len(self.progress_bars)):
            state = 0
            if i < self.current_step_index:
                state = 2
            elif i == self.current_step_index:
                state = 1

            self.progress_bars[i].setStyleSheet(self._get_step_style(i, state))

            if i < len(self.step_lines):
                if state == 2:
                    self.step_lines[i].setStyleSheet("background-color: #005BAC; border: none;")
                else:
                    self.step_lines[i].setStyleSheet("background-color: #ffffff; border: none;")

        # 녹화 및 안내 자동 진행 로직
        now = time.time()
        current_step = ENROLLMENT_STEPS[self.current_step_index]

        # 상태 기반 흐름 제어
        if self.state == "IDLE":
            self.state = "SHOW_START_MESSAGE"
            self.last_state_change_time = now # 초기 시간 설정

        elif self.state == "SHOW_START_MESSAGE":
            self.show_overlay_message(f"{self.current_step_index + 1}번째 촬영 시작!", duration_ms=2000)
            self.last_state_change_time = now
            
            # 2초 대기 후 SHOW_INSTRUCTION으로 전환 예약
            fade_out_duration = 500
            QTimer.singleShot(2000 + fade_out_duration, self._transition_to_instruction_state) 
            self.state = "WAIT_OVERLAY" 
            self.instruction_label.setText("") # 오버레이 있는 동안 안내 메시지 띄우지 않음
        
        elif self.state == "WAIT_OVERLAY":
            pass 

        elif self.state == "SHOW_INSTRUCTION":
            # 메시지 설정 / 상태 전환 처리
            current_instruction = current_step["instructions"][self.current_instruction_index]

            try:
                if self.instruction_label.parent() and self.instruction_label.isHidden():
                    self.instruction_label.show()
            except RuntimeError:
                pass

            self.instruction_label.setText(current_instruction)
            
            self.last_state_change_time = now 
            self.state = "WAIT_INSTRUCTION_TIME"

        elif self.state == "WAIT_INSTRUCTION_TIME":
            duration_per_instruction = current_step["duration"] / len(current_step["instructions"])
            
            # 시간 경과 확인
            if now - self.last_state_change_time >= duration_per_instruction:
                self.current_instruction_index += 1
                self.last_state_change_time = now # 상태 전환 시간 갱신

                if self.current_instruction_index < len(current_step["instructions"]):
                    # 다음 안내 메시지 표시로 전환
                    self.state = "SHOW_INSTRUCTION"
                else:
                    # 현재 단계의 완료 메시지로 전환
                    self.state = "SHOW_END_MESSAGE"

        elif self.state == "SHOW_END_MESSAGE":
            self.instruction_label.setText("")
            self.show_overlay_message(f"{self.current_step_index + 1}번쨰 촬영 완료!", duration_ms=2000)
            self.last_state_change_time = now

            fade_out_duration = 500
            QTimer.singleShot(2000 + fade_out_duration, self._transition_to_next_step) 
            self.state = "WAIT_OVERLAY_END"
            
        elif self.state == "WAIT_OVERLAY_END":
            pass

        # QPixmap 변환 및 페인팅
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, frame.shape[1], frame.shape[0], 3*frame.shape[1], QImage.Format_RGB888)
        qpixmap = QPixmap.fromImage(qimg)

        painter = QPainter(qpixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        line_color_qt = QColor(0, 120, 255)
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
    
    # 다음 안내 메시지로 전환하는 함수
    def _transition_to_instruction_state(self):
        try:
            if self.current_step_index >= len(ENROLLMENT_STEPS):
                return # 모든 단계 완료

            current_step = ENROLLMENT_STEPS[self.current_step_index]
            
            if self.current_instruction_index < len(current_step["instructions"]):
                self.state = "SHOW_INSTRUCTION"
            else:
                self.state = "SHOW_END_MESSAGE"
        except RuntimeError:
            return
        
    # 다음 단계로 전환하는 함수 
    def _transition_to_next_step(self):
        try:
            self.current_step_index += 1
            if self.current_step_index < len(ENROLLMENT_STEPS):
                self.current_instruction_index = 0
                self.state = "SHOW_START_MESSAGE"
            else:
                self.show_overlay_message("촬영 완료!")
                self.timer.stop()
                self.switch_callback("result", self.user_data, mode="enroll")
        except RuntimeError:
            return
    
    # 웹캠 해제 / 타이머 정지 함수
    def closeEvent(self, event):
        # if self.cap.isOpened(): self.cap.release()
        self.timer.stop()
        super().closeEvent(event)
