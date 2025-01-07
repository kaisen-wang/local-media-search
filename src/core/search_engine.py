from typing import List, Tuple
import traceback
from src.core.feature_extractor import FeatureExtractor
from src.database.models import MediaFile, VideoFrame
from src.database.sqlite_db import SQLiteDB
from src.database.vector_db import VectorDB
import os
import json
import logging
import numpy as np

log = logging.getLogger(__name__)

class SearchEngine:
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.similarity_threshold = 0.15  # 降低阈值以获取更多结果
        self.index_cache = {}  # 特征向量缓存
        self.index_built = False  # 添加索引状态标志

    def build_vector_db(self):
        log.info("=== Building vector database ===")
        self.index_built = False  # 重置状态标志
        session = SQLiteDB().get_session()
        try:
            # 图片特征
            images = session.query(MediaFile).filter_by(file_type='image').all()
            log.info(f"Found {len(images)} images in database")
            for media in images:
                if media.file_type == 'image':
                    image_path = media.file_path
                    if os.path.exists(image_path):
                        log.info(f"Processing image: {image_path}")
                        VectorDB().add_feature_vector_media_file(media)

            # 视频帧特征
            frames = session.query(VideoFrame).all()
            log.info(f"Found {len(frames)} video frames in database")
            for frame in frames:
                VectorDB().add_feature_vector_video_frame(frame)
            
            self.index_built = True  # 设置状态标志

        except Exception as e:
            log.error(f"Error retrieving media files from database: {str(e)}")
            traceback.print_exc()
            self.index_built = False
        finally:
            session.close()

    def _ensure_index_built(self):
        """确保索引已经构建"""
        if not self.index_built or len(self.index_cache) == 0:
            log.info("搜索索引未构建或为空，正在重建...")
            # self.build_index()
            # self.index_cache["null"] = []
            # self.build_vector_db()

    def text_search(self, query_text: str, page_number: int = 1, page_size: int = 20) -> List[Tuple]:
        """文本搜索"""
        try:
            self._ensure_index_built()  # 确保索引已构建
            
            # 提取文本特征
            query_features = self.feature_extractor.extract_text_features(query_text)
            if query_features is None:
                log.info("Failed to extract text features")
                return []

            log.info("Successfully extracted text features")
            return self._search_with_features(query_features, page_number = page_number, page_size = page_size)

        except Exception as e:
            log.info(f"Error in text search: {str(e)}")
            traceback.print_exc()
            return []

    def image_search(self, query_image_path: str, page_number: int = 1, page_size: int = 20) -> List[Tuple]:
        """图像搜索"""
        try:
            self._ensure_index_built()  # 确保索引已构建
            
            # 提取图像特征
            query_features = self.feature_extractor.extract_image_features(query_image_path)
            if query_features is None:
                log.info("Failed to extract image features")
                return []

            log.info("Successfully extracted image features")
            return self._search_with_features(query_features, page_number = page_number, page_size = page_size)

        except Exception as e:
            log.info(f"Error in image search: {str(e)}")
            traceback.print_exc()
            return []

    def _search_with_features(self, query_features: np.ndarray, page_number: int = 1, page_size: int = 20) -> List[Tuple]:
        """使用特征向量搜索"""
        try:
            return VectorDB().query(query_features.tolist(), page_number = page_number, page_size = page_size)
        except Exception as e:
            log.error(f"Error in feature search: {str(e)}")
            traceback.print_exc()
            return []

 