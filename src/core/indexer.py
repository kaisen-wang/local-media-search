from src.core.file_scanner import FileScanner
from src.core.feature_extractor import FeatureExtractor
from src.database.models import MediaFileDao, VideoFrameDao
from src.config import CACHE_DIR, VIDEO_FRAME_INTERVAL
from src.utils import delete_folder
from typing import List
import numpy as np
import concurrent.futures
import cv2
import os
import logging

log = logging.getLogger(__name__)

class Indexer:

    def index_directory(self, directory: str) -> List[str]:
        """索引目录中的所有媒体文件"""
        media_files = FileScanner.scan_directory(directory)
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
                    log.error(f"Error indexing file {file_path}:", e)

        return indexed_files

    def index_single_file(self, file_path: str) -> bool:
        """索引单个文件"""
        try:
            # 检查文件是否已经索引
            if MediaFileDao.is_file_indexed(file_path):
                log.warning(f"索引已存在 文件:{file_path}")
                return True
            
            # 确定文件类型
            file_type = 'image' if FileScanner.is_image(file_path) else 'video'
            
            if file_type == 'image':
                return self._index_image(file_path)
            elif file_type == 'video':
                return self._index_video(file_path)
    
        except Exception as e:
            log.error(f"Error indexing file {file_path}: ", e)
    
        return False

    def _index_image(self, file_path: str) -> bool:
        """索引图片文件"""
        try:
            log.info(f"=== 图片索引: {file_path} ===")
            features = FeatureExtractor().extract_image_features(file_path)
            
            if features is not None:
                # 验证特征向量
                if not isinstance(features, np.ndarray):
                    log.warning(f"无效的要素类型: {type(features)}")
                    return False
                    
                if len(features.shape) != 1:
                    log.warning(f"无效的特征形状: {features.shape}")
                    return False
                
                log.info(f"特征向量形状: {features.shape}")

                # 将特征向量转换为列表并保存
                MediaFileDao.add_media_file(
                    file_path=file_path,
                    file_type='image',
                    feature_list=features.tolist()
                )

                log.info(f"成功索引图像: {file_path}")
                return True
                
            else:
                log.warning(f"无法从图像中提取特征: {file_path}")
                return False
                
        except Exception as e:
            log.error(f"Error indexing image {file_path}: ", e)
            return False

    def _index_video(self, file_path: str) -> bool:
        """索引视频文件"""
        try:
            log.info(f"=== 索引视频文件路径: {file_path} ===")
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                log.warning(f"无法打开视频文件: {file_path}")
                return False

            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_interval = int(fps / float(VIDEO_FRAME_INTERVAL))
            
            log.debug(f"视频帧率 fps: {fps}; total_frames: {total_frames}; frame_interval: {frame_interval}")
            
            if fps <= 0 or total_frames <= 0:
                log.warning(f"视频元数据无效: fps={fps}, total_frames={total_frames}")
                return False

            # 创建视频文件记录
            media_file = MediaFileDao.add_media_file(
                file_path=file_path,
                file_type='video',
                metadata={
                    'fps': fps,
                    'total_frames': total_frames,
                    'duration': total_frames / fps
                }
            )

            if media_file is None:
                log.warning(f"无法创建视频文件记录数据库保存失败！file_path: {file_path}")
                return False

            try:
                frame_count = 0
                successful_frames = 0
                
                # 创建帧保存目录
                frames_dir = os.path.join(CACHE_DIR, 'video_frames', str(media_file.id))
                os.makedirs(frames_dir, exist_ok=True)

                log.info(f"创建帧保存目录 frames_dir: {frames_dir}")

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    if frame_count % frame_interval == 0:
                        try:
                            frame_path = os.path.join(frames_dir, f'frame_{frame_count}.jpg')
                            cv2.imwrite(frame_path, frame)
                            
                            # 提取特征
                            features = FeatureExtractor().extract_frame_features(frame)
                            
                            if features is not None:
                                # 验证特征向量
                                if not isinstance(features, np.ndarray):
                                    log.warning(f"Invalid feature type for frame {frame_count}")
                                    continue
                                    
                                if len(features.shape) != 1:
                                    log.warning(f"Invalid feature shape for frame {frame_count}: {features.shape}")
                                    continue
                                
                                # 将特征向量转换为列表并保存
                                video_frame = VideoFrameDao.add_video_frame(
                                    media_file_id=media_file.id,
                                    frame_number=frame_count,
                                    timestamp=frame_count / fps,
                                    file_path=file_path,
                                    frame_path=frame_path,
                                    feature_list=features.tolist()
                                )

                                if video_frame is not None:
                                    successful_frames += 1

                        except Exception as e:
                            log.error(f"Error processing frame {frame_count}: ", e)
                            if os.path.exists(frame_path):
                                os.remove(frame_path)
                            continue

                    frame_count += 1

                # 如果没有成功处理任何帧，则删除视频记录和帧目录
                if successful_frames == 0:
                    delete_folder(frames_dir)
                    log.warning(f"No frames were successfully processed for {file_path}")
                    return False

                log.info(f"成功索引视频 {file_path} 共 {successful_frames} 帧")
                return True

            except Exception as e:
                # 清理创建的目录
                delete_folder(frames_dir)
                log.error(f"Error indexing video {file_path}: ", e)
                return False
            
            finally:
                cap.release()

        except Exception as e:
            log.error(f"Error indexing video {file_path}: ", e)
            return False
