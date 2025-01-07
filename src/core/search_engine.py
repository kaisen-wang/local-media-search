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

    def build_index(self):
        """构建搜索索引并缓存特征向量"""
        log.info("=== Building search index ===")
        session = SQLiteDB().get_session()
        try:
            # 清空现有缓存
            self.index_cache.clear()
            self.index_built = False  # 重置状态标志
            
            # 缓存图片特征
            images = session.query(MediaFile).filter_by(file_type='image').all()
            log.info(f"Found {len(images)} images in database")
            
            for img in images:
                if img.feature_vector:
                    try:
                        features = np.array(json.loads(img.feature_vector))
                        # 验证特征向量
                        if features is not None and len(features) > 0:
                            self.index_cache[f"image_{img.id}"] = features
                    except Exception as e:
                        log.error(f"Error loading feature vector for image {img.id}: {str(e)}")

            # 缓存视频帧特征
            frames = session.query(VideoFrame).all()
            log.info(f"Found {len(frames)} video frames in database")
            
            for frame in frames:
                if frame.feature_vector:
                    try:
                        features = np.array(json.loads(frame.feature_vector))
                        # 验证特征向量
                        if features is not None and len(features) > 0:
                            self.index_cache[f"frame_{frame.id}"] = features
                    except Exception as e:
                        log.error(f"Error loading feature vector for frame {frame.id}: {str(e)}")

            log.info(f"Successfully cached {len(self.index_cache)} feature vectors")
            self.index_built = True  # 设置状态标志
            
        except Exception as e:
            log.error(f"Error building index: {str(e)}")
            traceback.print_exc()
            self.index_built = False
        finally:
            session.close()
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
            results = []
            session = SQLiteDB().get_session()
            
            log.info("Calculating similarities...")
            # 使用缓存的特征向量进行批量计算
            # for key, features in self.index_cache.items():
            #     try:
            #         # 打印特征向量的形状以进行调试
            #         log.info(f"Query features shape: {query_features.shape}")
            #         log.info(f"Index features shape for {key}: {features.shape}")
                    
            #         similarity = self.feature_extractor.calculate_similarity(query_features, features)
                    
            #         log.info(f"Similarity for {key}: {similarity}")
                    
            #         if similarity >= self.similarity_threshold:
            #             if key.startswith('image_'):
            #                 media_id = int(key.split('_')[1])
            #                 media_file = session.query(MediaFile).get(media_id)
            #                 if media_file and os.path.exists(media_file.file_path):
            #                     results.append((media_id, similarity, 'image', None))
            #             else:  # frame
            #                 frame_id = int(key.split('_')[1])
            #                 frame = session.query(VideoFrame).get(frame_id)
            #                 if frame and os.path.exists(frame.frame_path):
            #                     results.append((frame.media_file_id, similarity, 'video', frame))
            #     except Exception as e:
            #         log.error(f"Error processing {key}: {str(e)}")
            #         continue

            # # 按相似度排序
            # results = sorted(results, key=lambda x: x.score, reverse=True)

            results = VectorDB().query(query_features.tolist(), page_number = page_number, page_size = page_size)
            return results
        except Exception as e:
            log.error(f"Error in feature search: {str(e)}")
            traceback.print_exc()
            return []
        finally:
            session.close()

    def verify_database(self):
        """验证数据库中的特征向量"""
        log.info("=== Verifying database ===")
        session = SQLiteDB().get_session()
        try:
            # 验证图片特征
            images = session.query(MediaFile).filter_by(file_type='image').all()
            log.info(f"Found {len(images)} images in database")
            valid_images = 0
            
            for img in images:
                try:
                    if img.feature_vector:
                        features = np.array(json.loads(img.feature_vector))
                        if features is not None and len(features.shape) == 1:
                            valid_images += 1
                        else:
                            log.info(f"Invalid feature shape for image {img.id}: {features.shape}")
                except Exception as e:
                    log.error(f"Error verifying image {img.id}: {str(e)}")
            
            log.info(f"Valid images: {valid_images}/{len(images)}")
            
            # 验证视频帧特征
            frames = session.query(VideoFrame).all()
            log.info(f"Found {len(frames)} video frames in database")
            valid_frames = 0
            
            for frame in frames:
                try:
                    if frame.feature_vector:
                        features = np.array(json.loads(frame.feature_vector))
                        if features is not None and len(features.shape) == 1:
                            valid_frames += 1
                        else:
                            log.info(f"Invalid feature shape for frame {frame.id}: {features.shape}")
                except Exception as e:
                    log.error(f"Error verifying frame {frame.id}: {str(e)}")
            
            log.info(f"Valid frames: {valid_frames}/{len(frames)}")
            
        finally:
            session.close()
 