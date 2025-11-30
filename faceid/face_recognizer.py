import os, time, json, cv2, numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from insightface.app import FaceAnalysis
from .anti_spoofing_detector import AntiSpoofingDetector

# ====================================================================
# 환경 설정
# ====================================================================

# 런타임 최적화
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
# 유틸 / 데이터 구조
# ====================================================================

def cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    """코사인 유사도 계산"""
    return float(np.dot(a, b))

def ensure_dir(p: str):
    """디렉토리 존재 여부 확인 및 생성"""
    os.makedirs(p, exist_ok=True)

@dataclass
class Identity:
    """개인 정보 및 얼굴 벡터 저장용 구조체"""
    name: str
    student_id: str # 학번 추가
    vecs: List[List[float]]
    template: List[float]

def load_gallery(path: str) -> Dict[str, Identity]:
    """등록된 얼굴 데이터 로드"""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {k: Identity(**v) for k, v in raw.items()}

def save_gallery(path: str, gal: Dict[str, Identity]):
    """얼굴 데이터 저장"""
    ensure_dir(os.path.dirname(path))
    raw = {k: asdict(v) for k, v in gal.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

def rrect_xyxy(H: int, W: int) -> Tuple[int, int, int, int, int]:
    """프레임 크기(H, W) 기준으로 가이드 둥근 사각형 좌표 반환"""
    gw = int(W * GUIDE_W_REL)
    gh = int(H * GUIDE_H_REL)
    cx, cy = W // 2, int(H * GUIDE_Y_REL)
    x1, x2 = max(0, cx - gw // 2), min(W - 1, cx + gw // 2)
    y1, y2 = max(0, cy - gh // 2), min(H - 1, cy + gh // 2)
    rr = int(min(gw, gh) * GUIDE_RADIUS_REL)
    return x1, y1, x2, y2, rr

def face_center_in_rrect(bbox, x1, y1, x2, y2, r) -> bool:
    """얼굴 중심이 가이드 영역(둥근 사각형) 내부에 있는지 확인"""
    bx1, by1, bx2, by2 = map(int, bbox)
    cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2

    # 직사각형 및 모서리 원 영역 검사
    if (x1 + r) <= cx <= (x2 - r) and y1 <= cy <= y2:
        return True
    if x1 <= cx <= x2 and (y1 + r) <= cy <= (y2 - r):
        return True
    for rx, ry in [(x1 + r, y1 + r), (x2 - r, y1 + r), (x1 + r, y2 - r), (x2 - r, y2 - r)]:
        if (cx - rx) ** 2 + (cy - ry) ** 2 <= r * r:
            return True
    return False

def get_faces_in_rrect(app, frame_bgr, x1, y1, x2, y2, margin=1.10):
    """가이드 영역 주변 ROI에서 얼굴 검출"""
    H, W = frame_bgr.shape[:2]
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    rr = int(max(x2 - x1, y2 - y1) * 0.5 * margin)
    rx1, ry1 = max(0, cx - rr), max(0, cy - rr)
    rx2, ry2 = min(W, cx + rr), min(H, cy + rr)

    roi = frame_bgr[ry1:ry2, rx1:rx2]
    faces = app.get(roi)
    kept = []

    for f in faces:
        # 원본 프레임 좌표로 복원
        f.bbox[0] += rx1; f.bbox[2] += rx1
        f.bbox[1] += ry1; f.bbox[3] += ry1

        # 가이드 영역 내 얼굴만 유지
        if face_center_in_rrect(f.bbox, x1, y1, x2, y2, int(min(x2 - x1, y2 - y1) * GUIDE_RADIUS_REL)):
            kept.append(f)
    return kept

def draw_name_tag(canvas, text, bbox, mirror=False):
    """인식된 얼굴 위에 이름 태그(텍스트) 표시"""
    x1, y1, x2, y2 = map(int, bbox)
    H, W = canvas.shape[:2]

    # 좌우 반전된 영상일 경우 좌표 반전
    if mirror:
        x1, x2 = (W - 1) - x2, (W - 1) - x1
        x1, x2 = min(x1, x2), max(x1, x2)

    # OpenCV → PIL 변환
    base = Image.fromarray(canvas[:, :, ::-1]).convert("RGBA")
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except:
        font = ImageFont.load_default()

    # 텍스트 크기 및 박스 계산
    l, t, r, b = ImageDraw.Draw(base).textbbox((0, 0), text, font=font)
    text_w, text_h = (r - l), (b - t)
    pad_x, pad_y = 8, 6
    bx1 = x1
    by1 = max(0, y1 - (text_h + pad_y * 2 + 6))
    bx2 = min(W - 1, bx1 + text_w + pad_x * 2)
    by2 = min(H - 1, by1 + text_h + pad_y * 2)

    # 반투명 배경 생성
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle([bx1, by1, bx2, by2], radius=8, fill=(0, 0, 0, 140))
    comp = Image.alpha_composite(base, overlay)

    # 텍스트 그림자 및 본문 출력
    draw2 = ImageDraw.Draw(comp)
    tx, ty = bx1 + pad_x, by1 + pad_y
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        draw2.text((tx + dx, ty + dy), text, font=font, fill=(0, 0, 0, 200))
    draw2.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))

    # PIL → OpenCV 변환
    canvas[:] = np.array(comp.convert("RGB"))[:, :, ::-1]
    return canvas

# ====================================================================
# FaceRecognizer 클래스
# ====================================================================

class FaceRecognizer:
    """얼굴 인식 및 등록 기능을 담당하는 클래스"""
    
    def __init__(self):
        # 모델 초기화
        self.app = FaceAnalysis(name=MODEL_PACK, providers=["CPUExecutionProvider"])
        self.app.prepare(ctx_id=0, det_size=DET_SIZE)
        self.gallery = load_gallery(GALLERY_PATH)
        self.anti_spoof_detector = AntiSpoofingDetector() 
        print(f"[FaceRecognizer] Gallery loaded: {list(self.gallery.keys())}")

        # 등록 상태 변수
        self.is_enrolling = False
        self.enroll_name = ""
        self.enroll_id = ""
        self.accum_vecs = []
        
        # ===== 성능/프레임 스킵 상태 =====
        self.frame_idx = 0
        self.last_emb: Optional[np.ndarray] = None
        self.last_face = None
        self.infer_times_ms: List[float] = []

        # ===== 스푸핑 안정화 변수 =====
        self.SCORE_WINDOW_SIZE = 5
        self.score_history = []
        self.SPOOF_WINDOW_SIZE = 5
        self.spoof_counter = 0

    # ---------------- 임베딩 추출 ----------------
    def _embed_biggest_once(self, frame_bgr: np.ndarray, rrect: Optional[Tuple] = None) -> Tuple[Optional[np.ndarray], Optional[dict]]:
        """프레임스킵/캐시 없이, 실제로 한 번 추론"""
        faces = self.app.get(frame_bgr) if rrect is None else get_faces_in_rrect(self.app, frame_bgr, *rrect)
        if not faces:
            return None, None, 1.0

        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        f = faces[0]

        # 스푸핑 검사
        _, live_score = self.anti_spoof_detector.detect_spoofing(frame_bgr, f.bbox)

        if self.frame_idx == 0:
            live_score = 1.0
        
        # print(f"[AntiSpoofing] Score: {live_score:.4f}")
        
        emb = getattr(f, "normed_embedding", None)
        if emb is None:
            e = f.embedding
            emb = e / np.linalg.norm(e)
        return emb.astype("float32"), f, live_score

    def embed_biggest(self, frame_bgr: np.ndarray, rrect: Optional[Tuple] = None, use_skip: bool = False) -> Tuple[Optional[np.ndarray], Optional[dict], bool]:
        """
        use_skip=False  : 매 호출마다 실제 추론 (Baseline / 등록용)
        use_skip=True   : FRAME_SKIP에 따라 추론 간헐 실행 + 결과 캐시
        """
        # 프레임 인덱스 증가
        self.frame_idx += 1

        run_infer = (not use_skip) or (self.frame_idx % FRAME_SKIP == 0) or (self.last_emb is None)
        is_live = True

        if run_infer:
            t0 = time.perf_counter()
            emb, face, live_score = self._embed_biggest_once(frame_bgr, rrect)
            t1 = time.perf_counter()

            if emb is not None:
                self.infer_times_ms.append((t1 - t0) * 1000.0)  # ms 기록

            if face is not None:
                self.score_history.append(live_score)
                if len(self.score_history) > self.SCORE_WINDOW_SIZE:
                    self.score_history.pop(0)

            # 스푸핑 판정
            current_score = np.mean(self.score_history) if self.score_history else 0.0
            if current_score < self.anti_spoof_detector.LIVE_THRESHOLD:
                self.spoof_counter += 1
            else:
                self.spoof_counter = 0
            is_live = (self.spoof_counter < self.SPOOF_WINDOW_SIZE)

            self.last_emb, self.last_face = emb, face
            self.last_is_live = is_live
        else:
            # 추론 스킵 → 직전 결과 재사용
            emb, face = self.last_emb, self.last_face
            is_live = getattr(self, 'last_is_live', True)

        return emb, face, is_live

    # ---------------- 인증 ----------------
    def identify_face(self, embedding: np.ndarray) -> Tuple[bool, Optional[str], Optional[float]]:
        """임베딩을 이용한 얼굴 식별"""
        if not self.gallery:
            return False, None, 0.0

        sims = [(name, cos_sim(embedding, np.asarray(ident.template, np.float32))) for name, ident in self.gallery.items()]
        sims.sort(key=lambda x: x[1], reverse=True)
        name_top, s_top = sims[0]
        s_2nd = sims[1][1] if len(sims) > 1 else -1.0

        # 인증 조건
        ok_match = (
            s_top >= THRESHOLD
            and (s_top - s_2nd) >= MARGIN_TOP2
            and len(self.gallery[name_top].vecs) >= MIN_SAMPLES_ID
        )
        return (True, name_top, s_top) if ok_match else (False, None, s_top)

    # ---------------- 등록 ----------------
    def start_enrollment(self, name: str, student_id: str = ""):
        """등록 시작"""
        self.is_enrolling = True
        self.enroll_name = name
        self.enroll_id = student_id
        self.accum_vecs = []

    def accumulate_sample(self, frame_bgr: np.ndarray, rrect: Optional[Tuple] = None) -> Tuple[bool, int]:
        """등록 샘플 누적 (항상 실제 추론 실행)"""
        if not self.is_enrolling:
            return False, 0

        emb, _ = self.embed_biggest(frame_bgr, rrect, use_skip=False)
        if emb is not None:
            self.accum_vecs.append(emb.copy())
            return True, len(self.accum_vecs)
        return False, len(self.accum_vecs)

    def finish_enrollment(self) -> bool:
        """등록 완료 후 템플릿 생성 및 저장"""
        self.is_enrolling = False
        if not self.enroll_name.strip() or len(self.accum_vecs) < MIN_SAMPLES_ID:
            print(f"-> Enrollment failed: Not enough samples ({len(self.accum_vecs)}/{MIN_SAMPLES_ID}) or invalid name.")
            return False

        vecs = np.stack(self.accum_vecs, axis=0)
        tmpl = (vecs.mean(axis=0) / np.linalg.norm(vecs.mean(axis=0))).astype("float32")

        # 기존 인물 갤러리 업데이트 or 신규 등록
        if self.enroll_name in self.gallery:
            self.gallery[self.enroll_name].vecs += [v.tolist() for v in vecs]
            old = np.asarray(self.gallery[self.enroll_name].template, np.float32)
            new = (old + tmpl) / np.linalg.norm(old + tmpl)
            self.gallery[self.enroll_name].template = new.tolist()
            self.gallery[self.enroll_name].student_id = self.enroll_id
        else:
            self.gallery[self.enroll_name] = Identity(
                name=self.enroll_name,
                student_id=self.enroll_id,
                vecs=[v.tolist() for v in vecs],
                template=tmpl.tolist(),
            )
            
    def reset_stats(self):
        self.frame_idx = 0
        self.last_emb = None
        self.last_face = None
        self.infer_times_ms.clear()
        self.score_history.clear()
        self.spoof_counter = 0

    def get_latency_stats(self):
        if not self.infer_times_ms:
            return {"count": 0, "mean_ms": 0.0, "p95_ms": 0.0}
        arr = np.asarray(self.infer_times_ms, dtype=np.float32)
        return {
            "count": int(len(arr)),
            "mean_ms": float(arr.mean()),
            "p95_ms": float(np.percentile(arr, 95)),
        }

        save_gallery(GALLERY_PATH, self.gallery)
        print(f"-> Saved '{self.enroll_name}' ({len(vecs)} samples)")
        return True
