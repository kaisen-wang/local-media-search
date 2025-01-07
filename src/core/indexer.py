from src.core.file_scanner import FileScanner
from src.core.feature_extractor import FeatureExtractor
from src.database.models import MediaFile, VideoFrame
from src.database.sqlite_db import SQLiteDB
from src.database.vector_db import VectorDB
from src.config import CACHE_DIR
from typing import List
import numpy as np
import concurrent.futures
import json
import cv2
import os
import traceback
import logging

log = logging.getLogger(__name__)

class Indexer:
    def __init__(self):
        self.file_scanner = FileScanner()
        self.feature_extractor = FeatureExtractor()
        self.frame_interval = 1  # 每秒提取的帧数

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
                    log.error(f"Error indexing file {file_path}: {str(e)}")

        return indexed_files

    def index_single_file(self, file_path: str) -> bool:
        """索引单个文件"""
        try:
            # 确定文件类型
            file_type = 'image' if self.file_scanner.is_image(file_path) else 'video'
            
            if file_type == 'image':
                return self._index_image(file_path)
            elif file_type == 'video':
                return self._index_video(file_path)
    
        except Exception as e:
            log.error(f"Error indexing file {file_path}: {str(e)}")
            return False
    
        return False

    def _index_image(self, file_path: str) -> bool:
        """索引图片文件"""
        try:
            log.info(f"=== Indexing image: {file_path} ===")
            features = self.feature_extractor.extract_image_features(file_path)
            
            if features is not None:
                # 验证特征向量
                if not isinstance(features, np.ndarray):
                    log.info(f"Invalid feature type: {type(features)}")
                    return False
                    
                if len(features.shape) != 1:
                    log.info(f"Invalid feature shape: {features.shape}")
                    return False
                
                log.info(f"Feature vector shape: {features.shape}")

                session = SQLiteDB().get_session()
                
                # 将特征向量转换为列表并保存
                feature_list = features.tolist()
                media_file = MediaFile(
                    file_path=file_path,
                    file_type='image',
                    feature_vector=json.dumps(feature_list)
                )
                
                session.add(media_file)
                session.flush()
                session.commit()
                session.close()

                VectorDB().add_feature_vector_media_file(media_file)

                log.info(f"Successfully indexed image: {file_path}")
                return True
                
            else:
                log.info(f"Failed to extract features from image: {file_path}")
                return False
                
        except Exception as e:
            log.error(f"Error indexing image {file_path}: {str(e)}")
            traceback.print_exc()
            return False

    def _index_video(self, file_path: str) -> bool:
        """索引视频文件"""
        try:
            log.info(f"=== Indexing video: {file_path} ===")
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                log.info(f"Could not open video file: {file_path}")
                return False

            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_interval = int(fps / self.frame_interval)  # 每隔多少帧提取一帧
            
            if fps <= 0 or total_frames <= 0:
                log.info(f"Invalid video metadata: fps={fps}, total_frames={total_frames}")
                return False

            # 创建视频文件记录
            media_file = MediaFile(
                file_path=file_path,
                file_type='video',
                metadata=json.dumps({
                    'fps': fps,
                    'total_frames': total_frames,
                    'duration': total_frames / fps
                })
            )

            session = SQLiteDB().get_session()
            try:
                # 保存视频文件记录
                session.add(media_file)
                session.flush()  # 获取media_file的ID
                
                frame_count = 0
                frames_data = []
                successful_frames = 0
                
                # 创建帧保存目录
                frames_dir = os.path.join(CACHE_DIR, 'video_frames', str(media_file.id))
                os.makedirs(frames_dir, exist_ok=True)

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    if frame_count % frame_interval == 0:
                        try:
                            frame_path = os.path.join(frames_dir, f'frame_{frame_count}.jpg')
                            cv2.imwrite(frame_path, frame)
                            
                            # 提取特征
                            features = self.feature_extractor.extract_frame_features(frame)
                            
                            if features is not None:
                                # 验证特征向量
                                if not isinstance(features, np.ndarray):
                                    log.info(f"Invalid feature type for frame {frame_count}")
                                    continue
                                    
                                if len(features.shape) != 1:
                                    log.info(f"Invalid feature shape for frame {frame_count}: {features.shape}")
                                    continue
                                
                                # 将特征向量转换为列表并保存
                                feature_list = features.tolist()
                                video_frame = VideoFrame(
                                    media_file_id=media_file.id,
                                    frame_number=frame_count,
                                    timestamp=frame_count / fps,
                                    frame_path=frame_path,
                                    feature_vector=json.dumps(feature_list)
                                )
                                
                                frames_data.append(video_frame)
                                successful_frames += 1

                        except Exception as e:
                            log.error(f"Error processing frame {frame_count}: {str(e)}")
                            if os.path.exists(frame_path):
                                os.remove(frame_path)
                            continue

                    frame_count += 1

                # 如果没有成功处理任何帧，则删除视频记录和帧目录
                if successful_frames == 0:
                    session.rollback()
                    if os.path.exists(frames_dir):
                        import shutil
                        shutil.rmtree(frames_dir)
                    log.info(f"No frames were successfully processed for {file_path}")
                    return False

                # 批量保存帧记录
                session.bulk_save_objects(frames_data)
                session.commit()
                log.info(f"Successfully indexed video {file_path} with {successful_frames} frames")
                self.batch_vector_video_frames_insert(media_file.id)
                return True

            except Exception as e:
                session.rollback()
                # 清理创建的目录
                if os.path.exists(frames_dir):
                    import shutil
                    shutil.rmtree(frames_dir)
                log.error(f"Error indexing video {file_path}: {str(e)}")
                return False
            
            finally:
                session.close()
                cap.release()

        except Exception as e:
            log.error(f"Error indexing video {file_path}: {str(e)}")
            return False

    def batch_vector_video_frames_insert(self, media_file_id: int):
        """批量插入向量数据库"""
        if not media_file_id:
            return False
        session = SQLiteDB().get_session()
        try:
            frames = session.query(VideoFrame).filter_by(media_file_id = media_file_id).all()
            
            for video_frame in frames:
                VectorDB().add_feature_vector_video_frame(video_frame)

        except Exception as e:
            session.rollback()
            log.error(f"Error during batch insert: {str(e)}")
        finally:
            session.close()
    