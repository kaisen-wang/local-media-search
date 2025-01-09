from typing import List
from sqlalchemy import Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from datetime import datetime
from .sqlite_db import SQLiteDB
from .vector_db import VectorDB
from .base import Base
import json
import logging

log = logging.getLogger(__name__)

class FilePath(Base):
    __tablename__ = 'file_paths'

    id = Column(Integer, primary_key=True)
    file_path = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class MediaFile(Base):
    __tablename__ = 'media_files'

    id = Column(Integer, primary_key=True)
    file_path = Column(String, unique=True, nullable=False)
    file_type = Column(String, nullable=False)  # 'image' or 'video'
    # feature_vector = Column(String)  # 存储特征向量的序列化字符串
    file_metadata = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    frames = relationship("VideoFrame", back_populates="media_file")

class VideoFrame(Base):
    """视频帧模型"""
    __tablename__ = 'video_frames'

    id = Column(Integer, primary_key=True)
    media_file_id = Column(Integer, ForeignKey('media_files.id'))
    frame_number = Column(Integer)  # 帧号
    timestamp = Column(Float)       # 时间戳（秒）
    frame_path = Column(String)     # 帧图像保存路径
    # feature_vector = Column(String) # 特征向量
    
    media_file = relationship("MediaFile", back_populates="frames")



class FilePathDao:

    def add_file_path(file_path: str) -> bool:
        """添加文件路径"""
        session = SQLiteDB().get_session()
        try:
            count = session.query(func.count(FilePath.id)).filter_by(file_path=file_path).scalar()
            if count <= 0:
                session.add(FilePath(file_path=file_path))
                session.commit()
                return True
        except Exception as e:
            session.rollback()
            log.error("Error adding file path: ", e)
        finally:
            session.close()
        return False

    def file_path_count() -> int:
        """统计文件路径总数"""
        log.info("统计文件路径总数")
        session = SQLiteDB().get_session()
        try:
            count = session.query(func.count(FilePath.id)).scalar()
            log.info(f"统计文件路径总数: {str(count)}")
            if count is None:
                return 0
            return count
        except Exception as e:
            log.error("统计文件路径总数错误:", e)
            return 0
        finally:
            session.close()

    # 获取所有已索引文件的目录
    def get_indexed_folders() -> List[str]:
        """获取所有已索引文件的目录"""
        log.info("获取所有已索引文件的目录")
        session = SQLiteDB().get_session()
        try:
            file_path_list = session.query(FilePath).all()
            log.info(f"获取所有已索引文件的目录: {str(file_path_list)}")
            return [file_path.file_path for file_path in file_path_list]
        except Exception as e:
            print(f"Error getting indexed folders: {e}")
            return []
        finally:
            session.close()


class MediaFileDao:

    def is_file_indexed(file_path: str) -> bool:
        """判断文件是否已经索引过"""
        session = SQLiteDB().get_session()
        try:
            count = session.query(func.count(MediaFile.id)).filter_by(file_path=file_path).scalar()
            return count > 0
        except Exception as e:
            log.error("Error checking if file is indexed: ", e)
            return False
        finally:
            session.close()

    def add_media_file(file_path: str, file_type: str, feature_list: List[float] = None, metadata: dict = None) -> MediaFile:
        """添加媒体文件"""
        session = SQLiteDB().get_session()
        try:
            # feature_vector = None
            # if feature_list is not None:
            #     feature_vector = json.dumps(feature_list)

            media_file = MediaFile(
                file_path=file_path,
                file_type=file_type,
                # feature_vector=feature_vector,
                file_metadata=json.dumps(metadata) if metadata else None
            )

            session.add(media_file)
            session.flush()

            if feature_list is not None:
                VectorDB().add_feature_vector_media_file(media_file.id, media_file.file_path, media_file.file_type, feature_list)

            return media_file
        except Exception as e:
            session.rollback()
            log.error("Error adding media file: ", e)
        finally:
            session.commit()
            session.close()

    def get_media_files_by_id(id: int) -> MediaFile:
        """根据id获取媒体文件"""
        session = SQLiteDB().get_session()
        try:
            return session.query(MediaFile).get(id)
        except Exception as e:
            log.error("Error getting media file by id: ", e)
        finally:
            session.close()

    def get_media_files_by_folder(folder_path: str) -> List[MediaFile]:
        """获取数据库中该文件夹的所有文件"""
        session = SQLiteDB().get_session()
        try:
            return session.query(MediaFile).filter(MediaFile.file_path.like(f"{folder_path}%")).all()
        except Exception as e:
            log.error("Error getting media files by folder: ", e)
        finally:
            session.close()

    def get_media_files_by_file_path(file_path: str) -> List[MediaFile]:
        """根据file_path获取媒体文件"""
        session = SQLiteDB().get_session()
        try:
            return session.query(MediaFile).filter_by(MediaFile=MediaFile).all()
        except Exception as e:
            log.error("Error getting media file by file_path: ", e)
        finally:
            session.close()

    def delete_media_file(media_file: MediaFile):
        """删除媒体文件"""
        session = SQLiteDB().get_session()
        try:
            session.delete(media_file)
            session.commit()

            VectorDB().delete_feature_vector_by_ids([str(media_file.id)])
        except Exception as e:
            session.rollback()
            log.error("Error deleting media file: ", e)
        finally:
            session.close()

class VideoFrameDao:

    def add_video_frame(media_file_id: int, frame_number: int, timestamp: float, frame_path: str, file_path: str, feature_list: List[float] = None) -> VideoFrame:
        """添加视频帧"""
        session = SQLiteDB().get_session()
        try:
            # feature_vector = None
            # if feature_list is not None:
            #     feature_vector = json.dumps(feature_list)

            video_frame = VideoFrame(
                media_file_id=media_file_id,
                frame_number=frame_number,
                timestamp=timestamp,
                frame_path=frame_path,
                # feature_vector=feature_vector
            )

            session.add(video_frame)
            session.flush()

            if feature_list is not None:
                VectorDB().add_feature_vector_video_frame(
                    video_frame.id,
                    media_file_id,
                    frame_path,
                    file_path,
                    timestamp,
                    feature_list
                )
            
            return video_frame
        except Exception as e:
            session.rollback()
            raise Exception(f"Error adding video frame: {str(e)}")
        finally:
            session.commit()
            session.close()
    
    def get_video_frames_by_media_file_id(media_file_id: int) -> List[VideoFrame]:
        """根据media_file_id获取视频帧"""
        session = SQLiteDB().get_session()
        try:
            return session.query(VideoFrame).filter_by(media_file_id=media_file_id).all()
        except Exception as e:
            log.error("Error getting video frames by media_file_id: ", e)
        finally:
            session.close()
    
    def delete_video_frame(video_frame: VideoFrame):
        """删除视频帧"""
        session = SQLiteDB().get_session()
        try:
            session.delete(video_frame)
            session.commit()

            VectorDB().delete_feature_vector_by_ids([str(video_frame.media_file_id) + '-' + str(video_frame.id)])
        except Exception as e:
            log.error("Error deleting video frame: ", e)
        finally:
            session.close()

    def delete_video_frame_by_id(video_frame_id: int) -> None:
        """根据video_frame_id删除视频帧"""
        session = SQLiteDB().get_session()
        try:
            video_frame = session.query(VideoFrame).filter_by(id=video_frame_id).first()
            if video_frame is not None:
                session.delete(video_frame)
                session.commit()

                VectorDB().delete_feature_vector_by_ids([str(video_frame.media_file_id) + '-' + str(video_frame.id)])
        except Exception as e:
            log.error("Error deleting video frame by id: ", e)
        finally:
            session.close()
