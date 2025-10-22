import os, json, cv2, time, numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFont
from insightface.app import FaceAnalysis

# ===== 런타임 최적화 =====
os.environ["ALBUMENTATIONS_DISABLE_VERSION_CHECK"] = "1"
os.environ["OMP_NUM_THREADS"]="1"; os.environ["OPENBLAS_NUM_THREADS"]="1"
os.environ["MKL_NUM_THREADS"]="1"; os.environ["VECLIB_MAXIMUM_THREADS"]="1"
os.environ["NUMEXPR_NUM_THREADS"]="1"
cv2.setNumThreads(0)

# ===== 설정 =====
MODEL_PACK     = "buffalo_s"
DET_SIZE       = (512, 512)
CAM_INDEX      = 0
CAP_SIZE       = (640, 480)

GALLERY_DIR    = "faceid/outputs/registry"
GALLERY_PATH   = os.path.join(GALLERY_DIR, "gallery.json")

THRESHOLD      = 0.35
MARGIN_TOP2    = 0.05
MIN_SAMPLES_ID = 3

SHOW_BG        = True
MIRROR_PREVIEW = True

# --- 직사각형 가이드(세로로 긴, 모서리 둥근) ---
GUIDE_ENABLED    = True
GUIDE_W_REL      = 0.35   # 화면 너비 비율
GUIDE_H_REL      = 0.65   # 화면 높이 비율
GUIDE_Y_REL      = 0.42   # 가이드 중심의 Y 위치(화면 비율, 살짝 상단)
GUIDE_RADIUS_REL = 0.06   # 모서리 굴림 반경 (min(w,h) 비율)
GUIDE_ALPHA      = 1.0    # 바깥 디밍 강도(0~1)

GUIDE_COLOR_IDLE   = (255,255,255)  # 흰색
GUIDE_COLOR_ACTIVE = (255,180,40)   # 파란 느낌(네온 블루 톤)

FONT_PATH = "faceid/fonts/NotoSansKR-Medium.ttf"
FONT_SIZE = 15

# ===== 유틸 =====
def cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))

def ensure_dir(p): os.makedirs(p, exist_ok=True)

@dataclass
class Identity:
    name: str
    vecs: List[List[float]]
    template: List[float]

def load_gallery(path: str) -> Dict[str, Identity]:
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for k, v in raw.items():
        out[k] = Identity(name=v["name"], vecs=v["vecs"], template=v["template"])
    return out

def save_gallery(path: str, gal: Dict[str, Identity]):
    ensure_dir(os.path.dirname(path))
    raw = {k: asdict(v) for k, v in gal.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

# ---------- 가이드: 둥근 직사각형 도우미 ----------
def rrect_xyxy(H:int, W:int) -> Tuple[int,int,int,int,int]:
    """화면 크기(H,W)에서 가이드 둥근사각형 (x1,y1,x2,y2,r) 반환"""
    gw = int(W * GUIDE_W_REL)
    gh = int(H * GUIDE_H_REL)
    cx = W // 2
    cy = int(H * GUIDE_Y_REL)
    x1 = max(0, cx - gw//2); x2 = min(W-1, cx + gw//2)
    y1 = max(0, cy - gh//2); y2 = min(H-1, cy + gh//2)
    rr = int(min(gw, gh) * GUIDE_RADIUS_REL)
    return x1, y1, x2, y2, rr

def draw_rrect_border(img, x1,y1,x2,y2, r, color, thickness=3):
    """OpenCV로 둥근사각형 테두리"""
    # 네 모서리
    cv2.ellipse(img, (x1+r, y1+r), (r,r), 180, 0, 90, color, thickness, cv2.LINE_AA)
    cv2.ellipse(img, (x2-r, y1+r), (r,r), 270, 0, 90, color, thickness, cv2.LINE_AA)
    cv2.ellipse(img, (x1+r, y2-r), (r,r), 90,  0, 90, color, thickness, cv2.LINE_AA)
    cv2.ellipse(img, (x2-r, y2-r), (r,r), 0,   0, 90, color, thickness, cv2.LINE_AA)
    # 변
    cv2.line(img, (x1+r, y1), (x2-r, y1), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1+r, y2), (x2-r, y2), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y1+r), (x1, y2-r), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y1+r), (x2, y2-r), color, thickness, cv2.LINE_AA)

def dim_outside_rrect(img, x1,y1,x2,y2, r, alpha=1.0, dim_color=(0,0,0)):
    """둥근사각형 바깥을 어둡게"""
    h,w = img.shape[:2]
    shade = np.full_like(img, dim_color, np.uint8)
    mask = np.zeros((h,w), np.uint8)

    # 채워진 둥근사각형 마스크 그리기
    cv2.rectangle(mask, (x1+r, y1), (x2-r, y2), 255, -1, cv2.LINE_AA)
    cv2.rectangle(mask, (x1, y1+r), (x2, y2-r), 255, -1, cv2.LINE_AA)
    cv2.circle(mask, (x1+r, y1+r), r, 255, -1, cv2.LINE_AA)
    cv2.circle(mask, (x2-r, y1+r), r, 255, -1, cv2.LINE_AA)
    cv2.circle(mask, (x1+r, y2-r), r, 255, -1, cv2.LINE_AA)
    cv2.circle(mask, (x2-r, y2-r), r, 255, -1, cv2.LINE_AA)

    mask = cv2.GaussianBlur(mask, (0,0), sigmaX=max(2,int(r*0.35)))
    mask_f = (mask[...,None].astype(np.float32)/255.0)
    mixed = (img*mask_f + shade*(1.0-mask_f)).astype(np.uint8)
    return cv2.addWeighted(mixed, alpha, img, 1.0-alpha, 0)

def face_center_in_rrect(bbox, x1,y1,x2,y2, r) -> bool:
    """얼굴 중심이 둥근사각형 내부인지(모서리 원까지 고려)"""
    bx1,by1,bx2,by2 = map(int, bbox)
    cx = (bx1+bx2)/2.0; cy = (by1+by2)/2.0
    # 중앙 직사각형
    if (x1+r) <= cx <= (x2-r) and y1 <= cy <= y2: return True
    if x1 <= cx <= x2 and (y1+r) <= cy <= (y2-r): return True
    # 네 모서리 원
    for rx,ry in [(x1+r,y1+r),(x2-r,y1+r),(x1+r,y2-r),(x2-r,y2-r)]:
        if (cx-rx)**2 + (cy-ry)**2 <= r*r: return True
    return False

def get_faces_in_rrect(app, frame_bgr, x1,y1,x2,y2, margin=1.10):
    """둥근사각형을 포함하는 ROI만 검출 → 좌표 복원 → rrect 내부만 남김"""
    H,W = frame_bgr.shape[:2]
    cx = (x1+x2)//2; cy = (y1+y2)//2
    rr = int(max(x2-x1, y2-y1) * 0.5 * margin)
    rx1 = max(0, cx-rr); ry1 = max(0, cy-rr)
    rx2 = min(W, cx+rr); ry2 = min(H, cy+rr)

    roi = frame_bgr[ry1:ry2, rx1:rx2]
    faces = app.get(roi)
    kept=[]
    for f in faces:
        f.bbox[0]+=rx1; f.bbox[2]+=rx1
        f.bbox[1]+=ry1; f.bbox[3]+=ry1
        if getattr(f,"kps",None) is not None:
            f.kps[:,0]+=rx1; f.kps[:,1]+=ry1
        if getattr(f,"landmark_2d_106",None) is not None and f.landmark_2d_106 is not None:
            f.landmark_2d_106[:,0]+=rx1; f.landmark_2d_106[:,1]+=ry1
        # rrect 내부만 유지
        if face_center_in_rrect(f.bbox, x1,y1,x2,y2, r=int(min(x2-x1,y2-y1)*GUIDE_RADIUS_REL)):
            kept.append(f)
    return kept

# ---------- 이름 라벨 ----------
def draw_name_tag(canvas, text, bbox, mirror=False):
    x1, y1, x2, y2 = map(int, bbox)
    H, W = canvas.shape[:2]
    if mirror:
        x1, x2 = (W-1)-x2, (W-1)-x1
    x1, x2 = min(x1, x2), max(x1, x2)

    base = Image.fromarray(canvas[:, :, ::-1]).convert("RGBA")
    try: font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except: font = ImageFont.load_default()

    l,t,r,b = ImageDraw.Draw(base).textbbox((0,0), text, font=font)
    text_w, text_h = (r-l),(b-t)
    pad_x, pad_y = 8,6
    bx1 = x1
    by1 = max(0, y1 - (text_h + pad_y*2 + 6))
    bx2 = min(W-1, bx1 + text_w + pad_x*2)
    by2 = min(H-1, by1 + text_h + pad_y*2)

    overlay = Image.new("RGBA", (W,H), (0,0,0,0))
    ImageDraw.Draw(overlay).rounded_rectangle([bx1,by1,bx2,by2], radius=8, fill=(0,0,0,140))
    comp = Image.alpha_composite(base, overlay)

    draw2 = ImageDraw.Draw(comp)
    tx,ty = bx1+pad_x, by1+pad_y
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
        draw2.text((tx+dx,ty+dy), text, font=font, fill=(0,0,0,200))
    draw2.text((tx,ty), text, font=font, fill=(255,255,255,255))

    canvas[:] = np.array(comp.convert("RGB"))[:, :, ::-1]
    return canvas

# ---------- 임베딩 ----------
def embed_biggest(app, frame_bgr, rrect=None):
    """rrect=(x1,y1,x2,y2,r) 이면 그 영역에서만 검출"""
    if rrect is None:
        faces = app.get(frame_bgr)
    else:
        x1,y1,x2,y2,r = rrect
        faces = get_faces_in_rrect(app, frame_bgr, x1,y1,x2,y2)
    if not faces: return None, None
    faces.sort(key=lambda f:(f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]), reverse=True)
    f = faces[0]
    emb = getattr(f, "normed_embedding", None)
    if emb is None:
        e = f.embedding; emb = e/np.linalg.norm(e)
    return emb.astype("float32"), f

def ema_update(template: np.ndarray, new_vec: np.ndarray, alpha=0.15) -> np.ndarray:
    t = (1.0 - alpha) * template + alpha * new_vec
    return (t / np.linalg.norm(t)).astype("float32")

# ---------- 메인 ----------
def main():
    app = FaceAnalysis(name=MODEL_PACK, providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=DET_SIZE)

    gallery = load_gallery(GALLERY_PATH)
    print(f"[gallery] loaded: {list(gallery.keys())}")

    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open webcam {CAM_INDEX}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAP_SIZE[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_SIZE[1])

    mirror = MIRROR_PREVIEW
    registering = False
    name_buf = ""
    accum_vecs: List[np.ndarray] = []

    print("[keys] q/ESC quit | m mirror | g enroll start/cancel | Enter finish enroll | s save gallery | d delete last")

    while True:
        ok, frame = cap.read()
        if not ok: break
        H, W = frame.shape[:2]
        canvas = cv2.flip(frame, 1) if mirror else frame.copy()

        # --- 둥근 직사각형 가이드/디밍 ---
        x1,y1,x2,y2,r = rrect_xyxy(H,W)
        if GUIDE_ENABLED:
            # ROI에서만 검출/임베딩
            emb, face = embed_biggest(app, frame, rrect=(x1,y1,x2,y2,r))
            # 디밍 + 테두리
            canvas = dim_outside_rrect(canvas, x1,y1,x2,y2,r, alpha=GUIDE_ALPHA, dim_color=(0,0,0))
            # 활성/비활성 색상
            in_guide = False
            if face is not None:
                bx1,by1,bx2,by2 = map(int, face.bbox)
                if mirror:
                    bx1, bx2 = (W-1)-bx2, (W-1)-bx1
                    if bx1>bx2: bx1,bx2 = bx2,bx1
                in_guide = face_center_in_rrect((bx1,by1,bx2,by2), x1,y1,x2,y2,r)
            draw_rrect_border(
                canvas, x1,y1,x2,y2,r,
                GUIDE_COLOR_ACTIVE if in_guide else GUIDE_COLOR_IDLE,
                thickness=4 if in_guide else 3
            )
        else:
            emb, face = embed_biggest(app, frame)

        if not SHOW_BG:
            canvas[:] = 0

        # 등록(키보드)
        if registering:
            if emb is not None:
                accum_vecs.append(emb.copy())
            info = f"ENROLL: {name_buf}  samples={len(accum_vecs)}"
            (tw, th), _ = cv2.getTextSize(info, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
            overlay = canvas.copy()
            cv2.rectangle(overlay, (8, 10), (12+tw, 10+th+10), (0,0,0), -1)
            canvas = cv2.addWeighted(overlay, 0.45, canvas, 0.55, 0)
            cv2.putText(canvas, info, (12, 10+th), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255,255,255), 2, cv2.LINE_AA)
        # 식별
        else:
            if emb is not None and len(gallery)>0:
                sims=[]
                for name, ident in gallery.items():
                    t = np.asarray(ident.template, np.float32)
                    sims.append((name, cos_sim(emb,t)))
                sims.sort(key=lambda x:x[1], reverse=True)
                name_top, s_top = sims[0]
                s_2nd = sims[1][1] if len(sims)>1 else -1.0
                ok_match = (s_top>=THRESHOLD) and ((s_top - s_2nd)>=MARGIN_TOP2) \
                           and (len(gallery[name_top].vecs) >= MIN_SAMPLES_ID)
                if ok_match and face is not None:
                    canvas = draw_name_tag(canvas, f"{name_top}", face.bbox, mirror)

        cv2.imshow("FaceID (Demo)", canvas)
        k = cv2.waitKey(1) & 0xFF

        # 공통 키
        if k in (ord('q'), 27): break
        elif k == ord('m'): mirror = not mirror
        elif k == ord('s'): save_gallery(GALLERY_PATH, gallery); print("-> gallery saved.")
        elif k == ord('d'):
            if len(gallery)>0:
                last = list(gallery.keys())[-1]
                gallery.pop(last, None); save_gallery(GALLERY_PATH, gallery)
                print(f"-> deleted '{last}'")

        # 등록 토글 및 입력
        if k == ord('g'):
            if not registering:
                registering, name_buf, accum_vecs = True, "", []
                print("-> enrolling... type name then Enter")
            else:
                registering, name_buf, accum_vecs = False, "", []
                print("-> enrollment cancelled.")
        elif registering:
            if k in (10,13):
                if name_buf.strip() and len(accum_vecs)>=1:
                    vecs = np.stack(accum_vecs, axis=0)
                    m = vecs.mean(axis=0); tmpl = (m/np.linalg.norm(m)).astype("float32")
                    if name_buf in gallery:
                        gallery[name_buf].vecs += [v.tolist() for v in vecs]
                        old = np.asarray(gallery[name_buf].template, np.float32)
                        new = (old + tmpl); new = (new/np.linalg.norm(new))
                        gallery[name_buf].template = new.tolist()
                    else:
                        gallery[name_buf] = Identity(name=name_buf,
                                                     vecs=[v.tolist() for v in vecs],
                                                     template=tmpl.tolist())
                    save_gallery(GALLERY_PATH, gallery)
                    print(f"-> saved '{name_buf}' ({len(vecs)} samples)")
                else:
                    print("-> no name or samples. cancelled.")
                registering, name_buf, accum_vecs = False, "", []
            elif k in (8,127):
                if len(name_buf)>0: name_buf = name_buf[:-1]
            elif 32 <= k <= 126:
                name_buf += chr(k)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
