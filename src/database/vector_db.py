import logging
import chromadb
from typing import List, Optional
from src.config import VECTOR_DB_PATH

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

    def create_collection(self, name: str) -> None:
        """创建新的集合"""
        self.collection = self.client.get_or_create_collection(name)
        
    def add_feature_vector(self, id: str, embedding: List[float], metadata: dict) -> None:
        """向集合中添加单个特征向量"""
        self.collection.add(
            ids=[id],
            embeddings=[embedding],
            metadatas=[metadata]
        )

    def add_vectors(self, ids: List[str], embeddings: List[List[float]], 
                   metadatas: Optional[List[dict]] = None) -> None:
        """将向量添加到集合中"""
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
    def query(self, query_embeddings: List[List[float]], n_results: int = 20) -> dict:
        """查询相似向量"""
        return self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results
        )
        
    def persist(self) -> None:
        """将数据保存到磁盘"""
        self.client.persist()
