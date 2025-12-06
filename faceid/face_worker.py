from PySide6.QtCore import QObject, Signal, Slot
import numpy as np

class FaceWorker(QObject):
    resultReady = Signal(object)  # dict 등 아무 객체나

    def __init__(self, face_rec, parent=None):
        super().__init__(parent)
        self.face_rec = face_rec

    @Slot(object)
    def process_frame(self, data):
        """
        data: {'frame': np.ndarray, 'rrect': tuple, 'mode': str, 'retries': int}
        """
        frame = data["frame"]
        rrect = data["rrect"]

        # 1) 얼굴 임베딩 + 라이브니스
        emb, face_obj, is_live = self.face_rec.embed_biggest(frame, rrect, use_skip=True)

        # 2) 식별(여기서까지 같이 해버릴 수도 있음)
        success = False
        found_id = None
        similarity = None
        user_name = None
        student_id = None

        if emb is not None and is_live:
            success, found_id, similarity = self.face_rec.identify_face(emb)
            ident = self.face_rec.gallery.get(found_id) if found_id is not None else None
            if ident:
                student_id = ident.student_id
                user_name = ident.name

        result = {
            "emb": emb,
            "face_obj": face_obj,
            "is_live": is_live,
            "success": success,
            "found_id": found_id,
            "similarity": similarity,
            "user_name": user_name,
            "student_id": student_id,
            "mode": data["mode"],
            "retries": data["retries"],
        }
        self.resultReady.emit(result)
