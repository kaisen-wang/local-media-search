import os
from src.config import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from pathlib import Path
from typing import List, Set

class FileScanner:

    def __init__(self):
        self.indexed_paths: Set[str] = set()

    def scan_directory(self, directory: str) -> List[str]:
        """扫描目录并返回支持的媒体文件列表"""
        media_files = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                if self._is_supported_file(file_path):
                    media_files.append(str(file_path))
                    self.indexed_paths.add(str(file_path))

        return media_files

    def _is_supported_file(self, file_path: Path) -> bool:
        """检查文件是否为支持的媒体类型"""
        return (file_path.suffix.lower() in IMAGE_EXTENSIONS or file_path.suffix.lower() in VIDEO_EXTENSIONS)

    def is_image(self, file_path: str) -> bool:
        """检查文件是否为图片"""
        return Path(file_path).suffix.lower() in IMAGE_EXTENSIONS

    def is_video(self, file_path: str) -> bool:
        """检查文件是否为视频"""
        return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS 