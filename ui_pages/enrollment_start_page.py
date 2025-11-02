from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QPainter
from ui_style import BUTTON_STYLE, TITLE_STYLE, GUIDE_STYLE, LABEL_STYLE
from .base_page import BasePage

class EnrollmentStartPage(BasePage):
    def __init__(self, switch_callback, user_data):
        super().__init__(switch_callback)
        self.switch_callback = switch_callback
        self.user_data = user_data  # enrollment_input 페이지에서 전달 받은 이름/학번
        self.setStyleSheet("QWidget { background: transparent; }") 

        main_layout = self.get_content_layout()
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.addSpacing(40)
                
        # 시작 안내
        title_label = QLabel("얼굴 등록을 시작합니다!")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(TITLE_STYLE)
        main_layout.addWidget(title_label)
        main_layout.addSpacing(40)
        
        # 유의사항 안내
        guidance_box = QFrame()
        guidance_box.setStyleSheet("""
            QFrame {
                background-color: #242424;
                border-radius: 12px;
                padding: 0px 15px;
            }
        """)
        guidance_box.setFixedSize(700, 530)
        guidance_layout = QVBoxLayout(guidance_box)
        guidance_layout.setAlignment(Qt.AlignCenter)
        guidance_layout.setSpacing(10)
        guidance_layout.setContentsMargins(10, 10, 10, 10)

        guidance_title = QLabel("촬영시 유의사항")
        guidance_title.setStyleSheet("font-size: 34px; color: white;")
        guidance_title.setAlignment(Qt.AlignCenter)

        guidance_text_1 = QLabel("정확한 인증을 위해 총 3단계의 촬영이 진행됩니다.")
        guidance_text_2 = QLabel(
            "각 단계는 10~15초 정도 소요됩니다.\n"
            "선글라스, 모자, 마스크는 벗어주세요.\n"
            "몸은 고정하고 고개만 움직여주세요."
        )
        guidance_text_1.setAlignment(Qt.AlignCenter)
        guidance_text_1.setStyleSheet(LABEL_STYLE)
        guidance_text_2.setAlignment(Qt.AlignCenter)
        guidance_text_2.setStyleSheet(LABEL_STYLE)

        guidance_layout.addWidget(guidance_title)
        guidance_layout.addSpacing(10)
        guidance_layout.addWidget(guidance_text_1)
        guidance_layout.addWidget(guidance_text_2)
        guidance_layout.addSpacing(20)

        # 금지 이미지
        IMAGE_BASE_PATH = "resources/"
        IMAGE_SIZE = QSize(160, 140)

        prohibit_glasses = self.create_prohibit_overlay(
            base_image_path=IMAGE_BASE_PATH + "glasses.png",
            overlay_image_path=IMAGE_BASE_PATH + "prohibit.png",
            size=IMAGE_SIZE
        ) 
        prohibit_hat = self.create_prohibit_overlay(
            base_image_path=IMAGE_BASE_PATH + "hat.png",
            overlay_image_path=IMAGE_BASE_PATH + "prohibit.png",
            size=IMAGE_SIZE
        )
        prohibit_mask = self.create_prohibit_overlay(
            base_image_path=IMAGE_BASE_PATH + "mask.png",
            overlay_image_path=IMAGE_BASE_PATH + "prohibit.png",
            size=IMAGE_SIZE
        )

        image_hbox = QHBoxLayout()
        image_hbox.setSpacing(0)
        image_hbox.setContentsMargins(0, 0, 0, 0)
        image_hbox.addWidget(prohibit_glasses)
        image_hbox.addWidget(prohibit_hat)
        image_hbox.addWidget(prohibit_mask)
        
        guidance_layout.addLayout(image_hbox)

        # guidance_box 가운데 정렬
        guidance_container = QHBoxLayout()
        guidance_container.addStretch(1)
        guidance_container.addWidget(guidance_box)
        guidance_container.addStretch(1)

        main_layout.addLayout(guidance_container)
        main_layout.addSpacing(60)

        # 버튼
        start_btn = QPushButton("촬영 시작하기")
        start_btn.setStyleSheet(BUTTON_STYLE)
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(start_btn)
        button_layout.addStretch(1)

        main_layout.addLayout(button_layout)
        main_layout.addStretch(1)

        # enrollment_recording 페이지로 이동
        start_btn.clicked.connect(lambda: self.switch_callback("enrollment_recording", self.user_data))
    
    
    def create_prohibit_overlay(self, base_image_path, overlay_image_path, size=QSize(80, 80)):
        """
        기본 이미지 위에 금지 아이콘 덧씌운 QLabel 생성
        """
        try:
            base_pixmap = QPixmap(base_image_path)
            overlay_pixmap = QPixmap(overlay_image_path)

            if base_pixmap.isNull() or overlay_pixmap.isNull():
                print(f"[create_prohibit_overlay] Error: missing {base_image_path} or {overlay_image_path}")
                placeholder = QLabel("?")
                placeholder.setStyleSheet("font-size: 40px; color: red;")
                placeholder.setAlignment(Qt.AlignCenter)
                placeholder.setFixedSize(size)
                return placeholder

            # 스케일링 – 비율 유지하면서 target size 안에 맞춤
            scaled_base = base_pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled_overlay = overlay_pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            # 최종 픽스맵
            target = QPixmap(size)
            target.fill(Qt.transparent)

            # 중앙 정렬 위치 계산
            bx = (size.width() - scaled_base.width()) // 2
            by = (size.height() - scaled_base.height()) // 2
            ox = (size.width() - scaled_overlay.width()) // 2
            oy = (size.height() - scaled_overlay.height()) // 2

            # 합성
            painter = QPainter(target)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.drawPixmap(bx, by, scaled_base)
            painter.drawPixmap(ox, oy, scaled_overlay)
            painter.end()

            # QLabel 설정
            label = QLabel()
            label.setPixmap(target)
            label.setScaledContents(True)  # 픽스맵 전체를 라벨 크기에 맞게 표시
            label.setFixedSize(size)
            label.setAlignment(Qt.AlignCenter)
            return label

        except Exception as e:
            print(f"[create_prohibit_overlay] error: {e}")
            placeholder = QLabel("?")
            placeholder.setStyleSheet("font-size: 40px; color: gray;")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setFixedSize(size)
            return placeholder