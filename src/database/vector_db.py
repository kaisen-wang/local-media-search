import logging
import chromadb
from typing import List
from src.config import VECTOR_DB_PATH

logger = logging.getLogger(__name__)

class VectorDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.info("创建 VectorDB 实例")
            cls._instance = super(VectorDB, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self) -> None:
        """初始化向量数据库"""
        self.client = chromadb.PersistentClient(path = VECTOR_DB_PATH)
        self.collection = self.client.get_or_create_collection(name='media_search', metadata={"hnsw:space": "cosine"})

    def add_feature_vector_media_file(self, id: int, file_path: str, file_type: str, feature_list: List[float]) -> None:
        """向集合中添加多个特征向量"""
        self._add_feature_vector(
            str(id),
            feature_list,
            {
                'id': id,
                'file_path': file_path,
                'file_type': file_type
            }
        )
    
    def add_feature_vector_video_frame(self, id: int, media_file_id: int, frame_path: str, timestamp: float, feature_list: List[float]) -> None:
        """向集合中添加多个特征向量"""
        self._add_feature_vector(
            str(media_file_id) + '-' + str(id),
            feature_list,
            {
                'id': media_file_id,
                'video_frame_id': id,
                'file_path': frame_path,
                'file_type': 'video_frame',
                'timestamp': timestamp
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

    def delete_feature_vector_by_ids(self, ids: List[str]) -> None:
        """删除集合中的特征向量"""
        self.collection.delete(ids=ids)

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
