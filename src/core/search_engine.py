from typing import List, Tuple
from src.core.feature_extractor import FeatureExtractor
from src.database.models import MediaFileDao
from src.database.vector_db import VectorDB
import logging
import numpy as np

log = logging.getLogger(__name__)

class SearchEngine:

    def text_search(query_text: str, page_number: int = 1, page_size: int = 20) -> List[Tuple]:
        """文本搜索"""
        try:
            # 提取文本特征
            query_features = FeatureExtractor().extract_text_features(query_text)
            if query_features is None:
                log.warning("提取文本特征向量失败")
                return []
            return SearchEngine._search_with_features(query_features, page_number = page_number, page_size = page_size)
        except Exception as e:
            log.exception("Error in text search: ")
            return []

    def image_search(query_image_path: str, page_number: int = 1, page_size: int = 20) -> List[Tuple]:
        """图像搜索"""
        try:
            # 提取图像特征
            query_features = FeatureExtractor().extract_image_features(query_image_path)
            if query_features is None:
                log.warning("提取图像特征向量失败")
                return []
            return SearchEngine._search_with_features(query_features, page_number = page_number, page_size = page_size)
        except Exception as e:
            log.exception("Error in image search: ")
            return []

    def _search_with_features(query_features: np.ndarray, page_number: int = 1, page_size: int = 20) -> List[Tuple]:
        """使用特征向量搜索"""
        try:
            if MediaFileDao.is_empty():
                log.warning("没有添加文件索引")
                return None
            return VectorDB().query(query_features.tolist(), page_number = page_number, page_size = page_size)
        except Exception as e:
            log.exception("Error in feature search: ")
            return []

 