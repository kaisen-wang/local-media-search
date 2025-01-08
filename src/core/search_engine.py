from typing import List, Tuple
import traceback
from src.core.feature_extractor import FeatureExtractor
from src.database.vector_db import VectorDB
import logging
import numpy as np

log = logging.getLogger(__name__)

class SearchEngine:
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.similarity_threshold = 0.15  # 降低阈值以获取更多结果
        self.index_cache = {}  # 特征向量缓存
        self.index_built = False  # 添加索引状态标志

    def text_search(self, query_text: str, page_number: int = 1, page_size: int = 20) -> List[Tuple]:
        """文本搜索"""
        try:
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

 