import json
import logging
import chromadb
import numpy as np
from chromadb.api.types import QueryResult
from typing import List, Optional
from src.config import VECTOR_DB_PATH
from .models import MediaFile, VideoFrame

logger = logging.getLogger(__name__)

class VectorDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.info("Creating new instance of VectorDB")
            cls._instance = super(VectorDB, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self) -> None:
        """初始化向量数据库"""
        self.client = chromadb.PersistentClient(path = VECTOR_DB_PATH)
        self.collection = self.client.get_or_create_collection('media_search')

    def add_feature_vector_media_file(self, media_file: MediaFile) -> None:
        """向集合中添加多个特征向量"""
        features = np.array(json.loads(media_file.feature_vector))
        self._add_feature_vector(
            str(media_file.id),
            features,
            {
                'id': media_file.id,
                'file_path': media_file.file_path,
                'file_type': media_file.file_type
            }
        )
    
    def add_feature_vector_video_frame(self, video_frame: VideoFrame) -> None:
        """向集合中添加多个特征向量"""
        features = np.array(json.loads(video_frame.feature_vector))
        self._add_feature_vector(
            video_frame.media_file_id + '-' + video_frame.id,
            features,
            {
                'id': video_frame.media_file_id,
                'video_frame_id': video_frame.id,
                'file_path': video_frame.frame_path,
                'file_type': 'video_frame',
                'timestamp': video_frame.timestamp
            }
        )

    def _add_feature_vector(self, id: str, embedding: List[float], metadata: dict) -> None:
        """向集合中添加单个特征向量"""
        item = self.collection.get(ids=[id])
        if item['ids'] == []:
            self.collection.add(
                ids=[id],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            # PersistentClient automatically persists changes

    def query(self, query_embeddings: List[float], page_size: int = 20, page_number: int = 1, n_results: int = 200) -> List[dict]:
        """
        查询相似向量并返回格式化结果
        :param page_size: 每页结果数
        :param page_number: 当前页码（从 1 开始）
        :param n_results: 总共需要的结果数
        """
        # offset = (page_number - 1) * page_size
        # limit = page_size

        result = self.collection.query(
            query_embeddings=[query_embeddings],
            n_results=n_results,
            include=[
                'distances',
                'metadatas'
            ]
        )

        # 将QueryResult转换为包含元数据和相似度得分的字典列表
        formatted_results = []
        for i in range(len(result['ids'][0])):
            distance = result['distances'][0][i]
            metadata = result['metadatas'][0][i]
            # 将距离转换为相似度得分 确保相似度得分在合理范围内
            score = distance
 
            logger.info(f"相似度得分 Distance: {distance}")

            formatted_results.append({
                'id': result['ids'][0][i],
                'score': score,
                'metadata': metadata
            })
        
         # 根据 score 值排序
        formatted_results = sorted(formatted_results, key=lambda x: x['score'], reverse=True)

        return formatted_results
