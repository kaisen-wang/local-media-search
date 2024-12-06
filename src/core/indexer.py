from src.core.file_scanner import FileScanner
from src.core.feature_extractor import FeatureExtractor
from src.database.models import Session, MediaFile
from typing import List
import numpy as np
import concurrent.futures
import json

class Indexer:
    def __init__(self):
        self.file_scanner = FileScanner()
        self.feature_extractor = FeatureExtractor()

    def index_directory(self, directory: str) -> List[str]:
        """索引目录中的所有媒体文件"""
        media_files = self.file_scanner.scan_directory(directory)
        indexed_files = []

        # 使用线程池并行处理文件
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.index_single_file, file_path): file_path for file_path in media_files}
            for future in concurrent.futures.as_completed(futures):
                file_path = futures[future]
                try:
                    if future.result():
                        indexed_files.append(file_path)
                except Exception as e:
                    print(f"Error indexing file {file_path}: {str(e)}")

        return indexed_files

    def index_single_file(self, file_path: str) -> bool:
        """索引单个文件"""
        try:
            # 确定文件类型
            file_type = 'image' if self.file_scanner.is_image(file_path) else 'video'
            
            if file_type == 'image':
                # 提取特征
                features = self.feature_extractor.extract_image_features(file_path)
                if features is not None:
                    # 创建数据库记录
                    media_file = MediaFile(
                        file_path=file_path,
                        file_type=file_type,
                        feature_vector=json.dumps(features.tolist())
                    )
                    # 使用批量插入
                    self.batch_insert([media_file])
                    return True
    
        except Exception as e:
            print(f"Error indexing file {file_path}: {str(e)}")
            return False
    
        return False

    def batch_insert(self, media_files: List[MediaFile]):
        """批量插入数据库记录"""
        session = Session()
        try:
            session.bulk_save_objects(media_files)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error during batch insert: {str(e)}")
        finally:
            session.close()