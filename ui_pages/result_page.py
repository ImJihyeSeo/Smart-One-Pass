import cv2
import time
import os
import sys

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QSize, QByteArray, QPropertyAnimation, QAbstractAnimation
from PySide6.QtGui import QPixmap, QPainter

'''
얼굴 인식 성공/실패 결과 표시하는 페이지
'''
class ResultPage(QWidget):

    '''
    결과 데이터(success, retries)에 따라 아이콘 파일과 안내 메시지 결정
    '''
    def __init__(self, switch_callback, result_data):
        super().__init__()
        self.switch_callback = switch_callback
        self.success, current_retries = result_data
        
        # 애니메이션 객체 초기화
        self.scale_animation = None
        self.fade_animation = None
        
        remaining_retries = current_retries - 1 if not self.success else current_retries
        
        self.setStyleSheet("background-color: #1a1a1a;")

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_size = 150
        
        if self.success:
            icon_file = "resources/check.png" 
            main_message = f"환영합니다, ooo님!\n출입문이 열립니다." 
            sub_message = ""
            timeout_ms = 3000
        
        elif remaining_retries > 0:
            icon_file = "resources/alert.png" 
            main_message = f"인식 실패! 다시 시도해주세요."
            sub_message = f"남은 횟수: {remaining_retries}회"
            timeout_ms = 4000

        else: # 최종 실패 (remaining_retries == 0)
            icon_file = "resources/alert.png" 
            main_message = f"인식에 최종 실패했습니다."
            sub_message = "학생증을 이용해 주세요."
            timeout_ms = 6000

        # 1. 중앙 아이콘
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent;")
        
        circle_pixmap = QPixmap(icon_size, icon_size)
        circle_pixmap.fill(Qt.transparent)
        
        painter = QPainter(circle_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawEllipse(0, 0, icon_size, icon_size)
        
        # 아이콘 이미지 로드 및 그리기
        try:
            icon_pixmap = QPixmap(icon_file) 
            if icon_pixmap.isNull():
                 raise FileNotFoundError(f"Icon file not found or failed to load: {icon_file}")
            
            checkmark_size = QSize(int(icon_size * 0.6), int(icon_size * 0.6))
            scaled_icon = icon_pixmap.scaled(checkmark_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            icon_x = (icon_size - scaled_icon.width()) // 2
            icon_y = (icon_size - scaled_icon.height()) // 2
            painter.drawPixmap(icon_x, icon_y, scaled_icon)
            
        except Exception as e:
            # 아이콘 파일 로드 실패 시 대체 텍스트 표시
            self.icon_label.setText("?")
            self.icon_label.setStyleSheet("font-size: 80px; color: white;")
            print(f"아이콘 로드 실패: {e}")
        
        painter.end()
        self.icon_label.setPixmap(circle_pixmap)
        
        main_layout.addStretch(1)
        main_layout.addWidget(self.icon_label)

        # 2. 메시지 라벨 - 메인 메시지
        self.name_label = QLabel(main_message)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("""
            font-size: 22px; color: #ffffff; font-weight: bold; margin-top: 30px; background-color: rgba(0, 0, 0, 0); 
        """)
        main_layout.addWidget(self.name_label)

        # 3. 메시지 라벨 - 서브 메시지
        self.action_label = QLabel(sub_message)
        self.action_label.setAlignment(Qt.AlignCenter)
        self.action_label.setStyleSheet("""
            font-size: 18px; color: #ffffff; margin-top: 10px; background-color: rgba(0, 0, 0, 0); 
        """)
        
        # 투명도 효과
        self.opacity_effect = QGraphicsOpacityEffect(self.action_label)
        self.action_label.setGraphicsEffect(self.opacity_effect)
        
        main_layout.addWidget(self.action_label)

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
        
        # 애니메이션 시작
        self.create_and_start_animation()


    '''
    메시지 라벨에 투명도 깜박임 효과 적용하는 함수
    '''
    def create_and_start_animation(self):
        self.fade_animation = QPropertyAnimation(self.opacity_effect, QByteArray(b"opacity"))
        self.fade_animation.setDuration(800) 
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.4)
        self.fade_animation.setLoopCount(1)
        self.fade_animation.finished.connect(self.start_fade_backward)
        self.fade_animation.start()


    '''
    투명도 애니메이션 끝날 때마다 서로 호출해 부드러운 깜박임 반복
    '''
    def start_fade_backward(self):
        self.fade_animation.setStartValue(0.4)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.finished.disconnect()
        self.fade_animation.finished.connect(self.start_fade_forward)
        self.fade_animation.start()

    def start_fade_forward(self):
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.4)
        self.fade_animation.finished.disconnect()
        self.fade_animation.finished.connect(self.start_fade_backward)
        self.fade_animation.start()

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