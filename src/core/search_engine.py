import numpy as np
import json
from typing import List, Tuple
import traceback
from src.core.feature_extractor import FeatureExtractor
from src.database.models import Session, MediaFile, VideoFrame
import os

class SearchEngine:
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.similarity_threshold = 0.15  # 降低阈值以获取更多结果
        self.index_cache = {}  # 特征向量缓存
        self.index_built = False  # 添加索引状态标志

    def build_index(self):
        """构建搜索索引并缓存特征向量"""
        print("\n=== Building search index ===")
        session = Session()
        try:
            # 清空现有缓存
            self.index_cache.clear()
            self.index_built = False  # 重置状态标志
            
            # 缓存图片特征
            images = session.query(MediaFile).filter_by(file_type='image').all()
            print(f"Found {len(images)} images in database")
            
            for img in images:
                if img.feature_vector:
                    try:
                        features = np.array(json.loads(img.feature_vector))
                        # 验证特征向量
                        if features is not None and len(features) > 0:
                            self.index_cache[f"image_{img.id}"] = features
                    except Exception as e:
                        print(f"Error loading feature vector for image {img.id}: {str(e)}")

            # 缓存视频帧特征
            frames = session.query(VideoFrame).all()
            print(f"Found {len(frames)} video frames in database")
            
            for frame in frames:
                if frame.feature_vector:
                    try:
                        features = np.array(json.loads(frame.feature_vector))
                        # 验证特征向量
                        if features is not None and len(features) > 0:
                            self.index_cache[f"frame_{frame.id}"] = features
                    except Exception as e:
                        print(f"Error loading feature vector for frame {frame.id}: {str(e)}")

            print(f"Successfully cached {len(self.index_cache)} feature vectors")
            self.index_built = True  # 设置状态标志
            
        except Exception as e:
            print(f"Error building index: {str(e)}")
            traceback.print_exc()
            self.index_built = False
        finally:
            session.close()

    def _ensure_index_built(self):
        """确保索引已经构建"""
        if not self.index_built or len(self.index_cache) == 0:
            print("Search index not built or empty, rebuilding...")
            self.build_index()

    def text_search(self, query_text: str) -> List[Tuple]:
        """文本搜索"""
        try:
            self._ensure_index_built()  # 确保索引已构建
            print(f"\n=== Performing text search ===")
            print(f"Query text: {query_text}")
            print(f"Current index size: {len(self.index_cache)}")
            
            # 提取文本特征
            query_features = self.feature_extractor.extract_text_features(query_text)
            if query_features is None:
                print("Failed to extract text features")
                return []

            print("Successfully extracted text features")
            return self._search_with_features(query_features)

        except Exception as e:
            print(f"Error in text search: {str(e)}")
            traceback.print_exc()
            return []

    def image_search(self, query_image_path: str) -> List[Tuple]:
        """图像搜索"""
        try:
            self._ensure_index_built()  # 确保索引已构建
            print(f"\n=== Performing image search ===")
            print(f"Query image: {query_image_path}")
            print(f"Current index size: {len(self.index_cache)}")
            
            # 提取图像特征
            query_features = self.feature_extractor.extract_image_features(query_image_path)
            if query_features is None:
                print("Failed to extract image features")
                return []

            print("Successfully extracted image features")
            return self._search_with_features(query_features)

        except Exception as e:
            print(f"Error in image search: {str(e)}")
            traceback.print_exc()
            return []

    def _search_with_features(self, query_features: np.ndarray) -> List[Tuple]:
        """使用特征向量搜索"""
        try:
            results = []
            session = Session()
            
            print("\nCalculating similarities...")
            # 使用缓存的特征向量进行批量计算
            for key, features in self.index_cache.items():
                try:
                    # 打印特征向量的形状以进行调试
                    print(f"Query features shape: {query_features.shape}")
                    print(f"Index features shape for {key}: {features.shape}")
                    
                    similarity = self.feature_extractor.calculate_similarity(query_features, features)
                    
                    print(f"Similarity for {key}: {similarity}")
                    
                    if similarity >= self.similarity_threshold:
                        if key.startswith('image_'):
                            media_id = int(key.split('_')[1])
                            media_file = session.query(MediaFile).get(media_id)
                            if media_file and os.path.exists(media_file.file_path):
                                results.append((media_id, similarity, 'image', None))
                        else:  # frame
                            frame_id = int(key.split('_')[1])
                            frame = session.query(VideoFrame).get(frame_id)
                            if frame and os.path.exists(frame.frame_path):
                                results.append((frame.media_file_id, similarity, 'video', frame))

                except Exception as e:
                    print(f"Error processing {key}: {str(e)}")
                    continue

            # 按相似度排序
            results.sort(key=lambda x: x[1], reverse=True)
            return results
        except Exception as e:
            print(f"Error in feature search: {str(e)}")
            traceback.print_exc()
            return []
        finally:
            session.close()

    def verify_database(self):
        """验证数据库中的特征向量"""
        print("\n=== Verifying database ===")
        session = Session()
        try:
            # 验证图片特征
            images = session.query(MediaFile).filter_by(file_type='image').all()
            print(f"Found {len(images)} images in database")
            valid_images = 0
            
            for img in images:
                try:
                    if img.feature_vector:
                        features = np.array(json.loads(img.feature_vector))
                        if features is not None and len(features.shape) == 1:
                            valid_images += 1
                        else:
                            print(f"Invalid feature shape for image {img.id}: {features.shape}")
                except Exception as e:
                    print(f"Error verifying image {img.id}: {str(e)}")
            
            print(f"Valid images: {valid_images}/{len(images)}")
            
            # 验证视频帧特征
            frames = session.query(VideoFrame).all()
            print(f"Found {len(frames)} video frames in database")
            valid_frames = 0
            
            for frame in frames:
                try:
                    if frame.feature_vector:
                        features = np.array(json.loads(frame.feature_vector))
                        if features is not None and len(features.shape) == 1:
                            valid_frames += 1
                        else:
                            print(f"Invalid feature shape for frame {frame.id}: {features.shape}")
                except Exception as e:
                    print(f"Error verifying frame {frame.id}: {str(e)}")
            
            print(f"Valid frames: {valid_frames}/{len(frames)}")
            
        finally:
            session.close()
 