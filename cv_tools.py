import cv2
import sys

# Haarcascade 분류기 로드
try:
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
except Exception as e:
    print(f"Error loading cascade classifier: {e}")
    sys.exit(1)

'''
OpenCV의 Haar Cascade 분류기를 사용해 주어진 웹캠 프레임에서 얼굴의 위치(좌표)를 감지
processing_page에서 사용됨 
'''
def detect_faces(frame):

    if face_cascade.empty():
        return []
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    return faces
