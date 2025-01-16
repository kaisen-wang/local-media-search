from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel
from src.config import CURRENT_OS
import os
import logging

log = logging.getLogger(__name__)

class ImageLabel(QLabel):
    """可点击的图片标签"""
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self.setMaximumSize(200, 200)
        self.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
            }
            QLabel:hover {
                border: 1px solid #999;
            }
        """)
        self.load_image()

    def load_image(self):
        """加载并显示图片"""
        try:
            pixmap = QPixmap(self.file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    190, 190,  # 略小于标签大小，留出边距
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.setPixmap(scaled_pixmap)
                # 设置工具提示显示文件路径
                self.setToolTip(self.file_path)
            else:
                self.setText("无法加载图片")
        except Exception as e:
            self.setText("加载错误")
            log.error(f"Error loading image {self.file_path}:", e)

    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 在默认图片查看器中打开图片
            if CURRENT_OS == 'linux':
                os.system(f'xdg-open "{self.file_path}"')  # Linux
            elif CURRENT_OS == 'windows':
                os.startfile(self.file_path) # Windows
            elif CURRENT_OS == 'macos':
                os.system(f'open "{self.file_path}"')   # MacOS
            else:
                raise ValueError("Unsupported OS")
