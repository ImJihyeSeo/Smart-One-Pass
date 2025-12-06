import cv2
import time

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout,
    QGraphicsDropShadowEffect, QFrame,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QPropertyAnimation, QAbstractAnimation, QEasingCurve, QSequentialAnimationGroup, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QPainter, QBitmap, QColor

from ui_style import TARGET_W, TARGET_H, MESSAGE_AREA_HEIGHT, BORDER_RADIUS, GUIDE_STYLE
from .base_page import BasePage

from faceid.face_recognizer import FaceRecognizer, rrect_xyxy
from faceid.face_worker import FaceWorker
from faceid.capture_worker import CaptureWorker

import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
try:
    from session_manager import UserSession
except ImportError:
    print("Warning: session_manager not found")

API_BASE_URL = "http://34.213.241.165:8000"

'''
웹캠 화면 표시하고, 얼굴 인식 과정을 시각적으로 처리해 결과를 result_page로 넘기는 페이지
'''
class ProcessingPage(BasePage):
    requestInference = Signal(object)   # UI → Worker 로 프레임 보내는 시그널
    '''
    UI 구성
    '''
    def __init__(self, switch_callback, cap, retries, face_rec: FaceRecognizer, mode=None):
        super().__init__(switch_callback)

        # 상태 변수 초기화
        self.cap = cap
        self.retries = retries
        self.face_rec = face_rec  # AI 모델 인스턴스
        self.mode = mode

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
        GUIDE_IMAGE_SIZE = 220

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
        shadow.setBlurRadius(50)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.video_label.setGraphicsEffect(shadow)     

        # 메시지 영역
        self.message_container = QWidget()
        self.message_container.setFixedHeight(MESSAGE_AREA_HEIGHT)
        self.message_container.setStyleSheet("background: transparent;")

        message_layout = QVBoxLayout(self.message_container)
        message_layout.setContentsMargins(0, 0, 0, 0)
        
        self.instruction = QLabel("※ 얼굴 인식을 시작하려면 화면을 바라봐주세요 ※")
        self.instruction.setAlignment(Qt.AlignCenter)
        self.instruction.setStyleSheet(GUIDE_STYLE)
        
        message_layout.addWidget(self.instruction)
        
        main_layout.addStretch(1)
        main_layout.addWidget(self.video_label, 0, Qt.AlignCenter)
        main_layout.addStretch(1)
        main_layout.addWidget(self.message_container)
        main_layout.addStretch(1)
        main_layout.setContentsMargins(0, 0, 0, 0) 

        self.setLayout(main_layout)

        # ---- Worker/QThread 설정 (추론) ----
        self.worker_thread = QThread(self)
        self.worker = FaceWorker(self.face_rec)
        self.worker.moveToThread(self.worker_thread)

        self.requestInference.connect(self.worker.process_frame)
        self.worker.resultReady.connect(self.on_face_result)

        self.worker_thread.start()
        self.worker_busy = False

        # ---- Capture QThread 설정 ----
        self.capture_thread = QThread(self)
        self.capture_worker = CaptureWorker(self.cap)
        self.capture_worker.moveToThread(self.capture_thread)

        # capture_thread 가 시작되면 worker.run() 실행
        self.capture_thread.started.connect(self.capture_worker.run)
        # 새 프레임 들어올 때마다 on_new_frame 호출
        self.capture_worker.frameCaptured.connect(self.on_new_frame)

        self.capture_thread.start()

        # 성능 측정
        self.perf_start = time.time()
        self.perf_frames = 0
        self.face_rec.reset_stats()
        
    def on_new_frame(self, frame):
        # 여기서는 cap.read() 하지 않고, 캡처 스레드가 준 frame만 사용
        if frame is None:
            return

        self.perf_frames += 1

        # 웹캠 화면 크롭 로직
        frame = cv2.flip(frame, 1)  # 좌우 반전
        h, w, _ = frame.shape
        target_h, target_w = self.TARGET_H, self.TARGET_W
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

        h, w, _ = frame.shape
        rrect = rrect_xyxy(h, w)

        # --------- 화면 그리기만 UI 스레드에서 ---------
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(
            rgb_frame.data, frame.shape[1], frame.shape[0],
            3 * frame.shape[1], QImage.Format_RGB888
        )
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

        # --------- 여기서부터는 Worker에게만 맡김 ---------
        if not self.worker_busy:
            data = {
                "frame": frame.copy(),   # Worker에서 쓸 복사본
                "rrect": rrect,
                "mode": self.mode,
                "retries": self.retries,
            }
            self.worker_busy = True
            self.requestInference.emit(data)

        # --------- 화면 그리기만 UI 스레드에서 ---------
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, frame.shape[1], frame.shape[0],
                      3 * frame.shape[1], QImage.Format_RGB888)
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
        
    def on_face_result(self, result: dict):
        # Worker 한 번 끝났으니 다음 프레임 요청 가능
        self.worker_busy = False

        emb         = result.get("emb")
        face_obj    = result.get("face_obj")
        is_live     = result.get("is_live")
        success     = result.get("success")
        found_id    = result.get("found_id")
        user_name   = result.get("user_name")
        student_id  = result.get("student_id")
        mode        = result.get("mode") or self.mode
        retries     = result.get("retries", self.retries)

        target_w, target_h = self.TARGET_W, self.TARGET_H
        guide_width = int(target_w * 0.5)
        guide_x1 = (target_w - guide_width) // 2
        guide_y1 = (target_h - guide_width) // 2
        guide_x2 = guide_x1 + guide_width
        guide_y2 = guide_y1 + guide_width

        face_in_guide = False
        if face_obj is not None:
            bx1, by1, bx2, by2 = map(int, face_obj.bbox)
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2
            if guide_x1 < cx < guide_x2 and guide_y1 < cy < guide_y2:
                face_in_guide = True

        # -----------------------------------
        # 1) 스푸핑 (가이드 안에 얼굴은 있는데 live 아님)
        # -----------------------------------
        if face_in_guide and not is_live:
            if self.guide_animation.state() == QAbstractAnimation.Running:
                self.guide_animation.stop()
            self.guide_opacity_effect.setOpacity(1.0)
            self.start_time = None
            self.instruction.setText("※ 실제 얼굴이 아닙니다! ※")
            self.instruction.setStyleSheet(f"{GUIDE_STYLE} color: #ff4444;")
            self.overlay_frame.setStyleSheet(
                f"QFrame {{ background-color: rgba(255, 0, 0, 150); "
                f"border-radius: {self.BORDER_RADIUS}px; }}"
            )
            return

        # -----------------------------------
        # 2) 정상 얼굴 + 라이브
        #    → 3초 동안 안정적으로 잡히면 최종 판정
        # -----------------------------------
        if face_in_guide and emb is not None and is_live:
            if self.start_time is None:
                self.start_time = time.time()
                self.overlay_frame.setStyleSheet(
                    f"QFrame {{ background-color: rgba(0, 0, 0, 40); "
                    f"border-radius: {self.BORDER_RADIUS}px; }}"
                )

            if self.guide_image_label.isVisible() and \
               self.guide_animation.state() != QAbstractAnimation.Running:
                self.guide_animation.start()

            self.instruction.setText("얼굴을 인식 중입니다. 잠시만 기다려주세요.")
            self.instruction.setStyleSheet(GUIDE_STYLE)

            elapsed = time.time() - self.start_time
            if elapsed < self.duration:
                # 아직 3초 안 됨 → 계속 관찰
                return
            
            if elapsed >= self.duration:
                # 3초 채웠을 때
                if self.guide_animation.state() == QAbstractAnimation.Running:
                    self.guide_animation.stop()

            # ---- 여기서부터는 3초 동안 안정적으로 인식된 상태 → 최종 종료 처리 ----
            total_elapsed = time.time() - self.perf_start
            fps = self.perf_frames / total_elapsed if total_elapsed > 0 else 0.0
            stats = self.face_rec.get_latency_stats()
            print("[ProcessingPage] FPS={:.2f}, frames={}, elapsed={:.2f}s"
                  .format(fps, self.perf_frames, total_elapsed))
            print("[ProcessingPage] single-frame latency mean={:.2f} ms, "
                  "p95={:.2f} ms, count={}"
                  .format(stats["mean_ms"], stats["p95_ms"], stats["count"]))

            # ---- 성공 케이스 ----
            if success and student_id and user_name:
                if mode == "auth_reservation":
                    # 좌석 예약 모드: 세션 로그인 후 예약 페이지로 이동
                    try:
                        UserSession.instance().login(user_id=student_id, name=user_name)
                    except Exception as e:
                        print(f"Session Error: {e}")

                    user_data = {"name": user_name, "student_id": student_id}
                    self._finish_and_go("reservation", user_data)
                    return
                else:
                    # 출입 인증 모드: 서버에 출입 기록 전송
                    try:
                        payload = {"sid": student_id}
                        response = requests.post(f"{API_BASE_URL}/access/record", json=payload)
                        if response.status_code in (200, 201):
                            res_json = response.json()
                            if isinstance(res_json, list):
                                res_json = res_json[0]
                            if res_json.get("success"):
                                print(f"✅ [Access] Success: {res_json.get('message')}")
                            else:
                                print(f"❌ [Access] Failed: {res_json}")
                        else:
                            print(f"❌ [Access] HTTP Error: {response.status_code}")
                    except Exception as e:
                        print(f"Network Error during access record: {e}")

                    result_data = (success, retries, user_name)
                    self._finish_and_go("result", result_data, mode=mode)
                    return

            # ---- 인식 실패 케이스 (3초는 채웠는데 success=False 등) ----
            if mode == "auth_reservation":
                user_data = {"name": user_name, "student_id": student_id}
                result_data = (success, retries, found_id, user_data)
            else:
                result_data = (success, retries, found_id)

            self._finish_and_go("result", result_data, mode=mode)
            return

        # -----------------------------------
        # 3) 얼굴 없음 / 가이드 밖
        #    → 페이지 유지, 안내 문구만 초기화
        # -----------------------------------
        if self.guide_animation.state() == QAbstractAnimation.Running:
            self.guide_animation.stop()
        self.guide_opacity_effect.setOpacity(1.0)
        self.start_time = None
        self.instruction.setText("※ 얼굴 인식을 시작하려면 화면을 바라봐주세요 ※")
        self.instruction.setStyleSheet(GUIDE_STYLE)
        self.overlay_frame.setStyleSheet(
            f"QFrame {{ background-color: rgba(0, 0, 0, 80); "
            f"border-radius: {self.BORDER_RADIUS}px; }}"
        )

        
    def _stop_worker_thread(self):
        # 이미 정리됐으면 무시
        if hasattr(self, "worker_thread") and self.worker_thread is not None:
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait()
                
    def _stop_capture_thread(self):
        if hasattr(self, "capture_worker") and self.capture_worker is not None:
            self.capture_worker.stop()
        if hasattr(self, "capture_thread") and self.capture_thread is not None:
            if self.capture_thread.isRunning():
                self.capture_thread.quit()
                self.capture_thread.wait()

                
    def _finish_and_go(self, target_page: str, *args, **kwargs):
        self._cleanup_threads_and_timer()
        self.switch_callback(target_page, *args, **kwargs)


    def _cleanup_threads_and_timer(self):
        # 추론 스레드
        if hasattr(self, "worker_thread") and self.worker_thread is not None:
            if self.worker_thread.isRunning():
                # FaceWorker에 stop() 같은 게 있으면 먼저 호출
                if hasattr(self, "worker") and hasattr(self.worker, "stop"):
                    try:
                        self.worker.stop()
                    except Exception as e:
                        print("[ProcessingPage] worker.stop() error:", e)
                self.worker_thread.quit()
                self.worker_thread.wait()

        # 캡처 스레드
        if hasattr(self, "capture_worker") and self.capture_worker is not None:
            try:
                self.capture_worker.stop()  # self._running = False
            except Exception as e:
                print("[ProcessingPage] capture_worker.stop() error:", e)

        if hasattr(self, "capture_thread") and self.capture_thread is not None:
            if self.capture_thread.isRunning():
                self.capture_thread.quit()
                self.capture_thread.wait()
           
            
    def closeEvent(self, event):
        if hasattr(self, 'guide_animation') and self.guide_animation.state() == QAbstractAnimation.Running:
            self.guide_animation.stop()
        self._cleanup_threads_and_timer()
        super().closeEvent(event)