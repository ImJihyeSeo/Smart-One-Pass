import cv2
import time

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout,
    QGraphicsDropShadowEffect, QFrame,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QAbstractAnimation, QEasingCurve, QSequentialAnimationGroup
from PySide6.QtGui import QPixmap, QImage, QPainter, QBitmap, QColor

from ui_style import TARGET_W, TARGET_H, MESSAGE_AREA_HEIGHT, BORDER_RADIUS, GUIDE_STYLE
from .base_page import BasePage

from faceid.face_recognizer import FaceRecognizer, rrect_xyxy


# 백엔드 API 연동
import sys
import os
import requests

# 🚨 추가: 세션 매니저 연동 (상위 폴더 접근)
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
try:
    from session_manager import UserSession
except ImportError:
    print("Warning: session_manager not found")

# 🚨 추가: API 기본 주소 (main.py 설정에 따라 다를 수 있음)
API_BASE_URL = "http://34.213.241.165:8000"

'''
웹캠 화면 표시하고, 얼굴 인식 과정을 시각적으로 처리해 결과를 result_page로 넘기는 페이지
'''
class ProcessingPage(BasePage):
    '''
    UI 구성, QTimer 시작
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

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
        
        # 성능 측정용
        self.perf_start = time.time()
        self.perf_frames = 0
        self.face_rec.reset_stats()

    def update_frame(self):
        if not self.cap.isOpened():
            self.instruction.setText("카메라 연결 실패")
            self.timer.stop()
            return

        ret, frame = self.cap.read()
        if not ret:
            return
        self.perf_frames += 1
        
        # 웹캠 화면 크롭 로직
        frame = cv2.flip(frame, 1) # 좌우 반전
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
        
        h, w, _ = frame.shape
        rrect = rrect_xyxy(h,w)
        
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
        emb, face_obj = self.face_rec.embed_biggest(frame, rrect, use_skip=True)

        # 가이드라인 영역에 얼굴 중심 있는지 확인 (InsightFace 결과만 사용)
        face_in_guide = False
        if face_obj is not None:
            bx1, by1, bx2, by2 = map(int, face_obj.bbox)
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2
            if guide_x1 < cx < guide_x2 and guide_y1 < cy < guide_y2:
                face_in_guide = True
        
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
                
                # ==== 성능 요약 출력 ====
                total_elapsed = time.time() - self.perf_start
                fps = self.perf_frames / total_elapsed if total_elapsed > 0 else 0.0
                stats = self.face_rec.get_latency_stats()
                print("[ProcessingPage] FPS={:.2f}, frames={}, elapsed={:.2f}s"
                      .format(fps, self.perf_frames, total_elapsed))
                print("[ProcessingPage] single-frame latency mean={:.2f} ms, p95={:.2f} ms, count={}"
                      .format(stats["mean_ms"], stats["p95_ms"], stats["count"]))
                # ========================

                # 기존 코드 주석 처리
                # 얼굴 식별 - AI 모델
                # success, name, similarity = self.face_rec.identify_face(emb)
                
                # 백엔드 API 연동
                
                success, found_id, similarity = self.face_rec.identify_face(emb)
                # -------------------------------------------------------
                # [API 및 세션 연동] 얼굴 인식 결과 처리
                # -------------------------------------------------------
                
                # 1. 인식된 사용자 정보 가져오기 (갤러리 조회)
                ident = self.face_rec.gallery.get(found_id)
                if ident:
                    student_id = ident.student_id # 혹은 found_id 그대로 사용
                    user_name = ident.name
                else:
                    # 인식은 됐는데 갤러리에 키가 없는 경우 (거의 없겠지만 방어 코드)
                    student_id = "99999999"
                    user_name = "Unknown"
                
                user_data = {"name": user_name, "student_id": student_id}
    
                if success:
                    # [상황 B] 좌석 예약 모드: 세션 로그인 후 예약 페이지로 이동
                    if self.mode == "auth_reservation":
                        try:
                            # 세션에 학번 저장 (다음 페이지에서 API 호출 시 사용)
                            UserSession.instance().login(user_id=student_id, name=user_name)
                            print(f"[Auth] Logged in: {user_name} ({student_id})")
                        except Exception as e:
                            print(f"Session Error: {e}")
                            
                        # 예약 페이지로 이동
                        self.switch_callback("reservation", user_data)
                        return

                    # [상황 A] 출입 인증 모드 (기본): 서버에 출입 기록 전송
                    else:
                        try:
                            # 🚨 API 호출: POST /access/record
                            payload = {"sid": student_id}
                            response = requests.post(f"{API_BASE_URL}/access/record", json=payload)
                            
                            # if response.status_code == 201:
                            #     print(f"[Access] Success: {response.json().get('message')}")
                            # else:
                            #     print(f"[Access] Failed: {response.text}")
                            
                            if response.status_code == 200 or response.status_code == 201:
                                res_json = response.json()
                                
                                # 🚨 [추가] 서버가 리스트로 보냈을 경우, 첫 번째 요소만 꺼내기
                                if isinstance(res_json, list):
                                    res_json = res_json[0]
                                    
                                # 이제 res_json은 항상 딕셔너리({})가 됩니다.
                                if res_json.get("success"):
                                    print(f"✅ [Access] Success: {res_json.get('message')}")
                                    # (성공 처리 로직...)
                                else:
                                    print(f"❌ [Access] Failed: {res_json}")
                            else:
                                print(f"❌ [Access] HTTP Error: {response.status_code}")
                                
                        except Exception as e:
                            print(f"Network Error during access record: {e}")
                            # 네트워크 오류가 나더라도 UI 흐름은 끊지 않고 결과 페이지로 이동 (선택 사항)

                        # 결과 페이지로 이동
                        result_data = (success, self.retries, user_name)
                        self.switch_callback("result", result_data, mode=self.mode)
                # 기존의 코드 주석 처리
                # # result_page로 결과 데이터 전달 (DB 연동 필요)
                # user_data = None
                
                # if success:
                #     # 실제로는 self.face_rec.gallery에서 student_id 등을 조회해야 함
                #     # 현재는 face_recognizer.py에서 name을 key로 사용
                #     ident = self.face_rec.gallery.get(name)
                #     if ident:
                #         user_data = {"name": ident.name, "student_id": ident.student_id} 
                #     else:
                #         user_data = {"name": name, "student_id": "99999999"} # 더미 학번
                
                # if success and self.mode == "auth_reservation":
                #     # print(f"DEBUG: Face recognition success in reservation mode. Skipping ResultPage.")
                #     # ReservationPage로 즉시 전환 (data에 학생 정보 전달)
                #     self.switch_callback("reservation", user_data)
                #     return
                
                
                # 예약 모드 실패 시: 4개 인자 전달
                if self.mode == "auth_reservation":
                    result_data = (success, self.retries, found_id, user_data)
                else:   # 출입 인증 모드(기본값) 및 기타 모드: 3개 인자 전달
                    result_data = (success, self.retries, found_id) 
                
                self.switch_callback("result", result_data, mode=self.mode)
        else:
            # 얼굴 미감지 시
            if self.guide_animation.state() == QAbstractAnimation.Running:
                self.guide_animation.stop()
            self.guide_opacity_effect.setOpacity(1.0) 
            self.start_time = None
            self.instruction.setText("※ 얼굴 인식을 시작하려면 화면을 바라봐주세요 ※")
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
