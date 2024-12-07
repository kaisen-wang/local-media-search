import numpy as np
from typing import List, Tuple
from src.database.models import Session, MediaFile, VideoFrame
from src.core.feature_extractor import FeatureExtractor
import json

class SearchEngine:
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.index = None
        self.file_ids = []
        self.build_index()  # 初始化时构建索引

    def build_index(self):
        """构建搜索索引"""
        try:
            print("Building search index...")
            session = Session()
            media_files = session.query(MediaFile).all()
            
            if not media_files:
                print("No media files found in database")
                return
            
            # 收集所有特征向量
            feature_vectors = []
            file_ids = []
            
            for media_file in media_files:
                try:
                    # 将字符串转换回numpy数组
                    features = np.array(json.loads(media_file.feature_vector))
                    feature_vectors.append(features)
                    file_ids.append(media_file.id)
                except Exception as e:
                    print(f"Error processing feature vector for file {media_file.file_path}: {e}")
                    continue
            
            if feature_vectors:
                # 将特征向量堆叠成矩阵
                self.features_matrix = np.vstack(feature_vectors)
                self.file_ids = file_ids
                print(f"Search index built with {len(self.file_ids)} files")
            else:
                print("No valid feature vectors found")
            
        except Exception as e:
            print(f"Error building search index: {e}")
        finally:
            session.close()

    def text_search(self, query_text: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """通过文本搜索"""
        try:
            print(f"Performing text search for: {query_text}")
            # 提取查询文本的特征
            query_features = self.feature_extractor.extract_text_features(query_text)
            if query_features is None:
                print("Failed to extract text features")
                return []
            
            print(f"Text features shape: {query_features.shape}")
            print(f"Text features norm: {np.linalg.norm(query_features)}")
            
            results = self._search_with_features(query_features, top_k)
            print(f"Found {len(results)} results with similarities: {[sim for _, sim in results]}")
            return results
            
        except Exception as e:
            print(f"Error in text search: {e}")
            return []

    def image_search(self, query_image_path: str, limit: int = 20) -> List[tuple]:
        """图像搜索，返回相似的图片和视频帧"""
        try:
            # 提取查询图像的特征
            query_features = self.feature_extractor.extract_image_features(query_image_path)
            if query_features is None:
                return []

            results = []
            session = Session()
            try:
                # 搜索图片
                image_files = session.query(MediaFile).filter_by(file_type='image').all()
                for media_file in image_files:
                    features = np.array(json.loads(media_file.feature_vector))
                    similarity = self.feature_extractor.calculate_similarity(query_features, features)
                    results.append((media_file.id, similarity, 'image', None))

                # 搜索视频帧
                video_frames = session.query(VideoFrame).all()
                for frame in video_frames:
                    features = np.array(json.loads(frame.feature_vector))
                    similarity = self.feature_extractor.calculate_similarity(query_features, features)
                    results.append((frame.media_file_id, similarity, 'video', frame))

                # 按相似度排序
                results.sort(key=lambda x: x[1], reverse=True)
                return results[:limit]

            finally:
                session.close()

        except Exception as e:
            print(f"Error in image search: {str(e)}")
            return []

    def _search_with_features(self, query_features: np.ndarray, top_k: int) -> List[Tuple[int, float]]:
        """使用特征向量搜索"""
        try:
            if not hasattr(self, 'features_matrix') or len(self.file_ids) == 0:
                print("Search index not built or empty")
                return []
            
            # 计算余弦相似度
            similarities = np.dot(self.features_matrix, query_features)
            # 归一化
            similarities = similarities / (
                np.linalg.norm(self.features_matrix, axis=1) * 
                np.linalg.norm(query_features)
            )
            
            # 获取top-k结果
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            # 构建结果列表
            results = []
            for idx in top_indices:
                file_id = self.file_ids[idx]
                similarity = float(similarities[idx])
                results.append((file_id, similarity))
            
            print(f"Found {len(results)} results")
            return results
            
        except Exception as e:
            print(f"Error in similarity search: {e}")
            return []
 