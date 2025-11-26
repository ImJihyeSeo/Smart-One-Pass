import onnxruntime
import numpy as np
import cv2
import os
from typing import Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(
    BASE_DIR, 
    "anti_spoofing", 
    "models", 
    "AntiSpoofing_print-replay_1.5_128.onnx"
)

INPUT_SIZE = (128, 128)
LIVE_THRESHOLD = 0.4

class AntiSpoofingDetector:
    def __init__(self):
        self.session = None
        self.input_name = 'input'
        self.output_name = 'output'
        
        try:
            self.session = onnxruntime.InferenceSession(MODEL_PATH)
            
        except Exception as e:
            print(f"[AntiSpoofing] ONNX 모델 로드 실패: {e}")
            self.session = None

    def _increased_crop(self, img_rgb: np.ndarray, bbox: tuple, bbox_inc: float = 1.5) -> np.ndarray:
        """ 얼굴 크롭, 패딩 """
        real_h, real_w = img_rgb.shape[:2]
        
        x, y, x2, y2 = bbox
        w, h = x2 - x, y2 - y
        l = max(w, h)
        
        xc, yc = x + w/2, y + h/2
        x, y = int(xc - l*bbox_inc/2), int(yc - l*bbox_inc/2)
        
        x1 = 0 if x < 0 else x 
        y1 = 0 if y < 0 else y
        x2 = real_w if x + l*bbox_inc > real_w else x + int(l*bbox_inc)
        y2 = real_h if y + l*bbox_inc > real_h else y + int(l*bbox_inc)
        
        # 크롭
        img = img_rgb[y1:y2, x1:x2, :]
        
        # 패딩
        pad_top = y1 - y
        pad_bottom = int(l * bbox_inc) - (y2 - y)
        pad_left = x1 - x
        pad_right = int(l * bbox_inc) - (x2 - x)
        
        img = cv2.copyMakeBorder(img, 
                                 pad_top, pad_bottom, 
                                 pad_left, pad_right, 
                                 cv2.BORDER_CONSTANT, value=[0, 0, 0])
        return img

    def _preprocess(self, face_roi: np.ndarray) -> np.ndarray:        
        img = cv2.resize(face_roi, INPUT_SIZE)
        img = img.astype(np.float32) / 255.0
        img = img.transpose((2, 0, 1)) 
        input_data = np.expand_dims(img, axis=0)
        
        return input_data

    def detect_spoofing(self, frame_bgr: np.ndarray, bbox: tuple) -> Tuple[bool, float]:
        """ 스푸핑 판별 """
        if self.session is None:
            return False, 0.0
            
        
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)  # RGB 변환
        cropped_padded_rgb = self._increased_crop(frame_rgb, bbox, bbox_inc=1.5)    # 크롭, 패딩
        input_data = self._preprocess(cropped_padded_rgb)   # 전처리

        # 추론
        try:
            outputs = self.session.run(
                [self.output_name], 
                {self.input_name: input_data}
            )
            output = outputs[0]
            
            if output.shape[-1] == 2:
                exp_output = np.exp(output)
                probabilities = exp_output / np.sum(exp_output, axis=1, keepdims=True)
                
                live_score = probabilities[0, 0]
                #print(f"[DEBUG] Raw Output: {output[0]}")
                #print(f"[DEBUG] Live Score (Prob[1]): {live_score:.4f}")
            else:
                live_score = output[0, 0] 

            is_live = live_score > LIVE_THRESHOLD
            
            return is_live, float(live_score)

        except Exception as e:
            print(f"[AntiSpoofing] 추론 중 오류 발생: {e}")
            return False, 0.0