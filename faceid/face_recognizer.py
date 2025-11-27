import os, time, json, cv2, numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from insightface.app import FaceAnalysis

# 백엔드 API 연동 및 비동기 처리를 위한 Qt 모듈
from PySide6.QtCore import QObject, QThread, Signal, Slot
import requests

AWS_BASE_URL = "http://34.213.241.165:8000"

# ====================================================================
# 환경 설정 (그대로 유지)
# ====================================================================
os.environ["ALBUMENTATIONS_DISABLE_VERSION_CHECK"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
cv2.setNumThreads(0)

MODEL_PACK = "buffalo_s"
DET_SIZE = (512, 512)
GALLERY_DIR = "faceid/outputs/registry"
GALLERY_PATH = os.path.join(GALLERY_DIR, "gallery.json")
FRAME_SKIP = 3
THRESHOLD = 0.35
MARGIN_TOP2 = 0.05
MIN_SAMPLES_ID = 3
GUIDE_W_REL = 0.35
GUIDE_H_REL = 0.65
GUIDE_Y_REL = 0.42
GUIDE_RADIUS_REL = 0.06
FONT_PATH = "faceid/fonts/NotoSansKR-Medium.ttf"
FONT_SIZE = 15

# ====================================================================
# 유틸 함수 (그대로 유지)
# ====================================================================
def cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

@dataclass
class Identity:
    name: str
    vecs: List[List[float]]
    template: List[float]
    student_id: str = ""

def load_gallery(path: str) -> Dict[str, Identity]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    gallery = {}
    for k, v in raw.items():
        sid = v.get("student_id", "")
        if not sid: continue
        gallery[sid] = Identity(**v)
    return gallery

def save_gallery(path: str, gal: Dict[str, Identity]):
    ensure_dir(os.path.dirname(path))
    raw = {k: asdict(v) for k, v in gal.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

def rrect_xyxy(H: int, W: int) -> Tuple[int, int, int, int, int]:
    gw = int(W * GUIDE_W_REL)
    gh = int(H * GUIDE_H_REL)
    cx, cy = W // 2, int(H * GUIDE_Y_REL)
    x1, x2 = max(0, cx - gw // 2), min(W - 1, cx + gw // 2)
    y1, y2 = max(0, cy - gh // 2), min(H - 1, cy + gh // 2)
    rr = int(min(gw, gh) * GUIDE_RADIUS_REL)
    return x1, y1, x2, y2, rr

def face_center_in_rrect(bbox, x1, y1, x2, y2, r) -> bool:
    bx1, by1, bx2, by2 = map(int, bbox)
    cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2
    if (x1 + r) <= cx <= (x2 - r) and y1 <= cy <= y2: return True
    if x1 <= cx <= x2 and (y1 + r) <= cy <= (y2 - r): return True
    for rx, ry in [(x1 + r, y1 + r), (x2 - r, y1 + r), (x1 + r, y2 - r), (x2 - r, y2 - r)]:
        if (cx - rx) ** 2 + (cy - ry) ** 2 <= r * r: return True
    return False

def get_faces_in_rrect(app, frame_bgr, x1, y1, x2, y2, margin=1.10):
    H, W = frame_bgr.shape[:2]
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    rr = int(max(x2 - x1, y2 - y1) * 0.5 * margin)
    rx1, ry1 = max(0, cx - rr), max(0, cy - rr)
    rx2, ry2 = min(W, cx + rr), min(H, cy + rr)
    roi = frame_bgr[ry1:ry2, rx1:rx2]
    faces = app.get(roi)
    kept = []
    for f in faces:
        f.bbox[0] += rx1; f.bbox[2] += rx1
        f.bbox[1] += ry1; f.bbox[3] += ry1
        if face_center_in_rrect(f.bbox, x1, y1, x2, y2, int(min(x2 - x1, y2 - y1) * GUIDE_RADIUS_REL)):
            kept.append(f)
    return kept

def draw_name_tag(canvas, text, bbox, mirror=False):
    # (생략: 기존 코드와 동일함)
    x1, y1, x2, y2 = map(int, bbox)
    H, W = canvas.shape[:2]
    if mirror:
        x1, x2 = (W - 1) - x2, (W - 1) - x1
        x1, x2 = min(x1, x2), max(x1, x2)
    base = Image.fromarray(canvas[:, :, ::-1]).convert("RGBA")
    try: font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except: font = ImageFont.load_default()
    l, t, r, b = ImageDraw.Draw(base).textbbox((0, 0), text, font=font)
    text_w, text_h = (r - l), (b - t)
    pad_x, pad_y = 8, 6
    bx1 = x1
    by1 = max(0, y1 - (text_h + pad_y * 2 + 6))
    bx2 = min(W - 1, bx1 + text_w + pad_x * 2)
    by2 = min(H - 1, by1 + text_h + pad_y * 2)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle([bx1, by1, bx2, by2], radius=8, fill=(0, 0, 0, 140))
    comp = Image.alpha_composite(base, overlay)
    draw2 = ImageDraw.Draw(comp)
    tx, ty = bx1 + pad_x, by1 + pad_y
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        draw2.text((tx + dx, ty + dy), text, font=font, fill=(0, 0, 0, 200))
    draw2.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    canvas[:] = np.array(comp.convert("RGB"))[:, :, ::-1]
    return canvas

# ====================================================================
# [추가] 네트워크 워커 (백그라운드 스레드용)
# ====================================================================
class EnrollmentWorker(QObject):
    """
    메인 화면을 멈추지 않고 백그라운드에서 AWS 서버로 데이터를 전송하는 비서입니다.
    """
    def __init__(self):
        super().__init__()

    @Slot(str, list)
    def send_sample(self, sid, embedding):
        """ [API] 샘플 전송 """
        try:
            payload = {"sid": sid, "embedding": embedding}
            url = f"{AWS_BASE_URL}/user/enroll/sample"
            
            # 별도 스레드에서 실행되므로 UI 멈춤 없음
            response = requests.post(url, json=payload, timeout=2.0)
            
            if response.status_code == 200:
                print(f"📤 [Worker] Sample sent success for {sid}")
            else:
                print(f"⚠️ [Worker] Sample send failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ [Worker] Network Error (Sample): {e}")

    @Slot(str, str)
    def finish_session(self, sid, name):
        """ [API] 등록 완료 요청 """
        try:
            payload = {"sid": sid, "name": name}
            url = f"{AWS_BASE_URL}/user/enroll/finish"
            
            response = requests.post(url, json=payload, timeout=5.0)
            
            if response.status_code == 200:
                print(f"✅ [Worker] Enrollment FINISHED for {name}({sid})")
            else:
                print(f"⚠️ [Worker] Finish failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ [Worker] Network Error (Finish): {e}")


# ====================================================================
# FaceRecognizer 클래스 (QThread 비동기 버전)
# ====================================================================

class FaceRecognizer(QObject): # 💡 QObject 상속 필수
    """얼굴 인식 및 등록 기능을 담당하는 클래스"""
    
    # 비서에게 보낼 신호(Signal) 정의
    sig_send_sample = Signal(str, list)   # (학번, 임베딩리스트)
    sig_finish_enroll = Signal(str, str)  # (학번, 이름)

    def __init__(self):
        super().__init__() # QObject 초기화
        
        # 1. AI 모델 초기화
        self.app = FaceAnalysis(name=MODEL_PACK, providers=["CPUExecutionProvider"])
        self.app.prepare(ctx_id=0, det_size=DET_SIZE)
        self.gallery = load_gallery(GALLERY_PATH) # 로컬 갤러리 (인증용)
        print(f"[FaceRecognizer] Gallery loaded: {list(self.gallery.keys())}")

        # 2. 비서(Worker) 및 쓰레드 생성
        self.thread = QThread()
        self.worker = EnrollmentWorker()
        self.worker.moveToThread(self.thread) # 비서를 별도 쓰레드로 이동
        
        # 3. 신호 연결 (선생님 명령 -> 비서 실행)
        self.sig_send_sample.connect(self.worker.send_sample)
        self.sig_finish_enroll.connect(self.worker.finish_session)
        
        # 4. 쓰레드 시작
        self.thread.start()
        print("[FaceRecognizer] Background worker thread started.")

        # 등록 상태 변수
        self.is_enrolling = False
        self.enroll_name = ""
        self.enroll_id = ""
        self.accum_vecs = []
        
        # 성능/프레임 스킵 상태
        self.frame_idx = 0
        self.last_emb: Optional[np.ndarray] = None
        self.last_face = None
        self.infer_times_ms: List[float] = []

    # ---------------- 임베딩 추출 ----------------
    def _embed_biggest_once(self, frame_bgr: np.ndarray, rrect: Optional[Tuple] = None) -> Tuple[Optional[np.ndarray], Optional[dict]]:
        """실제 추론 실행"""
        faces = self.app.get(frame_bgr) if rrect is None else get_faces_in_rrect(self.app, frame_bgr, *rrect)
        if not faces: return None, None
        
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        f = faces[0]
        
        emb = getattr(f, "normed_embedding", None)
        if emb is None:
            e = f.embedding
            emb = e / np.linalg.norm(e)
        return emb.astype("float32"), f

    def embed_biggest(self, frame_bgr: np.ndarray, rrect: Optional[Tuple] = None, use_skip: bool = False) -> Tuple[Optional[np.ndarray], Optional[dict]]:
        """프레임 스킵 적용 임베딩 추출"""
        self.frame_idx += 1
        run_infer = (not use_skip) or (self.frame_idx % FRAME_SKIP == 0) or (self.last_emb is None)

        if run_infer:
            t0 = time.perf_counter()
            emb, face = self._embed_biggest_once(frame_bgr, rrect)
            t1 = time.perf_counter()
            if emb is not None: self.infer_times_ms.append((t1 - t0) * 1000.0)
            self.last_emb, self.last_face = emb, face
        else:
            emb, face = self.last_emb, self.last_face
        return emb, face

    # ---------------- 인증 (로컬 갤러리 사용) ----------------
    def identify_face(self, embedding: np.ndarray) -> Tuple[bool, Optional[str], Optional[float]]:
        # if not self.gallery: return False, None, 0.0
        
        # sims = []
        # for sid, ident in self.gallery.items():
        #     sims.append((sid, cos_sim(embedding, np.asarray(ident.template, np.float32))))
            
        # sims.sort(key=lambda x: x[1], reverse=True)
        # found_id, s_top = sims[0]
        # s_2nd = sims[1][1] if len(sims) > 1 else -1.0
        
        # ok_match = (s_top >= THRESHOLD and (s_top - s_2nd) >= MARGIN_TOP2 and len(self.gallery[found_id].vecs) >= MIN_SAMPLES_ID)
        # return (True, found_id, s_top) if ok_match else (False, None, s_top)
        """
        [수정됨] 로컬 갤러리 대신 중앙 서버(API)에 물어봅니다.
        """
        try:
            # 1. 보낼 데이터 준비 (Numpy 배열을 일반 리스트로 변환)
            payload = {
                "embedding": embedding.tolist()
            }
            
            # 2. 서버에 "이 사람 누구예요?" 하고 물어봄 (동기 요청)
            # 주의: 너무 자주 호출하면 렉이 걸릴 수 있으므로 UI에서 조절 필요
            url = f"{AWS_BASE_URL}/access/identify"
            response = requests.post(url, json=payload, timeout=1.0) # 1초 안에 답 안 오면 포기
            
            # if response.status_code == 200:
            #     res_json = response.json()
            #     data = res_json.get("data", {})

            # [수정 후 코드] (이걸로 교체하세요!)
            if response.status_code == 200:
                res_json = response.json()
                
                # 🚨 [방어 코드 추가] 리스트로 오면 첫 번째 요소(딕셔너리)를 꺼냅니다.
                if isinstance(res_json, list):
                    res_json = res_json[0]
                    
                data = res_json.get("data", {})
                
                if data.get("found") is True:
                    found_sid = data.get("sid")
                    # 서버 인증은 유사도 점수를 따로 안 줄 수도 있어서 1.0(확실함)으로 가정하거나,
                    # 필요하면 API에서 점수도 같이 보내게 수정 가능. 여기선 일단 성공 처리.
                    print(f"🔍 [Server Auth] Found: {found_sid}")
                    return True, found_sid, 0.99 
                else:
                    return False, None, 0.0
            else:
                print(f"⚠️ Server Identify Failed: {response.status_code}")
                return False, None, 0.0

        except Exception as e:
            print(f"❌ Network Error during Identify: {e}")
            return False, None, 0.0
        

    # ---------------- 등록 (AWS 서버 연동 + 쓰레드) ----------------
    def start_enrollment(self, name: str, student_id: str = ""):
        """등록 시작 (로컬 초기화)"""
        self.is_enrolling = True
        self.enroll_name = name
        self.enroll_id = student_id
        self.accum_vecs = []
        print(f"-> Start enrollment locally for {name} ({student_id})")

    def accumulate_sample(self, frame_bgr: np.ndarray, rrect: Optional[Tuple] = None) -> Tuple[bool, int]:
        """등록 샘플 수집 및 비동기 전송"""
        if not self.is_enrolling: return False, 0

        # 1. 얼굴 특징 추출 (CPU 작업 - 메인 쓰레드)
        # (이 부분은 불가피하게 메인 스레드에서 해야 하지만, InsightFace가 빨라서 괜찮음)
        emb, _ = self.embed_biggest(frame_bgr, rrect, use_skip=False)
        
        if emb is not None:
            # 2. 로컬 카운팅을 위해 저장
            self.accum_vecs.append(emb)

            # 3. [핵심] 비서에게 "서버로 보내!" 신호 발송 (Non-blocking)
            # (이 함수는 즉시 리턴되므로 화면이 멈추지 않음)
            self.sig_send_sample.emit(self.enroll_id, emb.tolist())
            
            return True, len(self.accum_vecs)
            
        return False, len(self.accum_vecs)

    def finish_enrollment(self) -> bool:
        """등록 완료 요청"""
        self.is_enrolling = False
        if len(self.accum_vecs) < MIN_SAMPLES_ID:
            print("-> Not enough samples.")
            return False

        # 4. [핵심] 비서에게 "등록 마쳐!" 신호 발송
        self.sig_finish_enroll.emit(self.enroll_id, self.enroll_name)
        
        # 5. 로컬 갤러리에도 저장 (오프라인 인증용)
        vecs = np.stack(self.accum_vecs, axis=0)
        tmpl = (vecs.mean(axis=0) / np.linalg.norm(vecs.mean(axis=0))).astype("float32")
        
        if self.enroll_id in self.gallery:
            self.gallery[self.enroll_id].vecs += [v.tolist() for v in vecs]
            old = np.asarray(self.gallery[self.enroll_id].template, np.float32)
            new = (old + tmpl) / np.linalg.norm(old + tmpl)
            self.gallery[self.enroll_id].template = new.tolist()
            self.gallery[self.enroll_id].name = self.enroll_name
        else:
            self.gallery[self.enroll_id] = Identity(
                name=self.enroll_name,
                vecs=[v.tolist() for v in vecs],
                template=tmpl.tolist(),
                student_id=self.enroll_id
            )
        save_gallery(GALLERY_PATH, self.gallery)
        
        # UI 전환을 위해 즉시 True 반환
        return True

    # ---------------- 기타 ----------------
    def reset_stats(self):
        self.frame_idx = 0
        self.last_emb = None
        self.last_face = None
        self.infer_times_ms.clear()

    def get_latency_stats(self):
        if not self.infer_times_ms: return {"count": 0, "mean_ms": 0.0, "p95_ms": 0.0}
        arr = np.asarray(self.infer_times_ms, dtype=np.float32)
        return {"count": int(len(arr)), "mean_ms": float(arr.mean()), "p95_ms": float(np.percentile(arr, 95))}

    def __del__(self):
        """종료 시 쓰레드 정리"""
        if hasattr(self, 'thread'):
            self.thread.quit()
            self.thread.wait()