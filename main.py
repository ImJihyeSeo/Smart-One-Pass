import sys
import cv2
from PySide6.QtWidgets import (
    QApplication, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer

from ui_style import TOTAL_ATTEMPTS, CustomAlertDialog, TARGET_W_MAIN, TARGET_H_MAIN
from ui_pages.idle_page import IdlePage
from ui_pages.processing_page import ProcessingPage
from ui_pages.result_page import ResultPage
from ui_pages.enrollment_input_page import EnrollmentInputPage
from ui_pages.enrollment_start_page import EnrollmentStartPage
from ui_pages.enrollment_recording_page import EnrollmentRecordingPage
from ui_pages.reservation_page import ReservationPage, SeatMapPage
from ui_pages.return_page import ReturnSeatPage
from ui_pages.seat_map_page import ReadingRoom1SeatMapPage, ReadingRoom2_1SeatMapPage, ReadingRoom2_2SeatMapPage, ReadingRoom2_2GradSeatMapPage
from ui_pages.extend_page import ExtendSeatPage

from faceid.face_recognizer import FaceRecognizer


''' 
출입 애플리케이션 메인 컨테이너
모든 UI 페이지 관리, 웹캠 초기화, 다크 테마 적용
'''
class MainWindow(QStackedWidget):
    '''
    웹캠 초기화
    idle_page 로드
    창 크기/테두리 설정
    QApplication 스타일 적용
    '''
    def __init__(self):
        super().__init__()
        self.retries = TOTAL_ATTEMPTS 
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("경고: 웹캠을 열 수 없습니다.")

        self.face_rec = FaceRecognizer()    # AI 모델 인스턴스

        self.idle_page = IdlePage(self.switch_page)
        self.addWidget(self.idle_page)
        self.setCurrentWidget(self.idle_page)
        self.setWindowTitle("얼굴 인식 기반 시스템")
        self.setFixedSize(TARGET_W_MAIN, TARGET_H_MAIN)
        self.setWindowFlags(Qt.FramelessWindowHint) 
        self.setStyleSheet("""
            MainWindow {
                background-color: #1a1a1a; 
                border-radius: 20px;
            }
            QWidget { 
                background: transparent;
            }
        """)
        self.show()


    '''
    페이지 간 전환 함수
    idle_page 복귀 시 남은 시도 횟수 초기화
    processing_page/result_page 동적 생성 및 제거
    '''
    def switch_page(self, page_name, data=None, mode=None, popup_msg=None):
        
        # 현재 남은 시도 횟수 업데이트
        if isinstance(data, int):
            self.retries = data 
             
        current_widget = self.currentWidget()

        if current_widget != self.idle_page and current_widget is not None:
            self.removeWidget(current_widget)
            current_widget.deleteLater()

        if page_name == "enrollment_input":
            self.enrollment_input_page = EnrollmentInputPage(self.switch_page)
            self.addWidget(self.enrollment_input_page)
            self.setCurrentWidget(self.enrollment_input_page)
    
        elif page_name == "enrollment_start":
            # data는 user_data (학번/이름)
            self.enrollment_start_page = EnrollmentStartPage(self.switch_page, data)
            self.addWidget(self.enrollment_start_page)
            self.setCurrentWidget(self.enrollment_start_page)
            
        elif page_name == "enrollment_recording":
            # self.face_rec 전달
            self.enrollment_recording_page = EnrollmentRecordingPage(self.switch_page, data, self.cap, self.face_rec)
            self.addWidget(self.enrollment_recording_page)
            self.setCurrentWidget(self.enrollment_recording_page)
        
        elif page_name == "processing":
            # self.face_rec 전달
            self.processing_page = ProcessingPage(self.switch_page, self.cap, self.retries, self.face_rec) 
            self.addWidget(self.processing_page)
            self.setCurrentWidget(self.processing_page)
        
        elif page_name == "result":
            if mode:
                result_page = ResultPage(self.switch_page, data, mode=mode)
            else:
                result_page = ResultPage(self.switch_page, data)

            self.addWidget(result_page)
            self.setCurrentWidget(result_page)

        elif page_name == "reservation":
            self.reservation_page = ReservationPage(self.switch_page) 
            self.addWidget(self.reservation_page)
            self.setCurrentWidget(self.reservation_page)
        
        # 반납 페이지
        elif page_name == "return_seat":
            self.return_page = ReturnSeatPage(self.switch_page) 
            self.addWidget(self.return_page)
            self.setCurrentWidget(self.return_page)

        # 연장 페이지
        elif page_name == "extend_seat":
            self.extend_page = ExtendSeatPage(self.switch_page)   
            self.addWidget(self.extend_page)
            self.setCurrentWidget(self.extend_page)
        
        # 열람실 배치도 페이지
        elif page_name == "seat_map":
            if data == "제1열람실":
                self.seat_map_page = ReadingRoom1SeatMapPage(self.switch_page, data)
            elif data == "제2-1열람실":
                self.seat_map_page = ReadingRoom2_1SeatMapPage(self.switch_page, data)
            elif data == "제2-2열람실":
                self.seat_map_page = ReadingRoom2_2SeatMapPage(self.switch_page, data)
            elif data == "제2-2열람실\n(대학원생 전용)":
                self.seat_map_page = ReadingRoom2_2GradSeatMapPage(self.switch_page, data)
            else:
                # 기타 열람실 - 임시 페이지 사용 (수정 필요)
                self.seat_map_page = SeatMapPage(self.switch_page, data)
                
            self.addWidget(self.seat_map_page)
            self.setCurrentWidget(self.seat_map_page)
                
        elif page_name == "idle":
            self.retries = TOTAL_ATTEMPTS # 초기화
            self.setCurrentWidget(self.idle_page)
        
        if popup_msg:
            QTimer.singleShot(100, lambda: self._show_transient_popup(popup_msg))

    def _show_transient_popup(self, msg):
        dialog = CustomAlertDialog(msg, self) 
        dialog.exec()
        QTimer.singleShot(2000, dialog.accept)

    '''
    메인 창 종료 시 웹캠 리소스 해제
    '''
    def closeEvent(self, event):
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)

if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
