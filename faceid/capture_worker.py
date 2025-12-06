from PySide6.QtCore import QObject, Signal, Slot
import cv2

class CaptureWorker(QObject):
    frameCaptured = Signal(object)  # numpy frame

    def __init__(self, cap, parent=None):
        super().__init__(parent)
        self.cap = cap
        self._running = True

    @Slot()
    def run(self):
        # QThread.started 에 연결해서 돌릴 함수
        while self._running:
            if not self.cap.isOpened():
                # 카메라가 닫혔으면 그냥 루프 탈출
                break

            ret, frame = self.cap.read()
            if not ret:
                continue

            # 최신 프레임 emit
            self.frameCaptured.emit(frame)

    def stop(self):
        self._running = False
