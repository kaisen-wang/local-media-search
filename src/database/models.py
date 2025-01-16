from typing import List
from datetime import datetime
from .sqlite_db import SQLiteDB
from .vector_db import VectorDB
import json
import logging

log = logging.getLogger(__name__)

class FilePath:
    def __init__(self, id=None, file_path=None, created_at=None, last_modified=None):
        self.id = id
        self.file_path = file_path
        self.created_at = created_at
        self.last_modified = last_modified

    def create_table_sql() -> str:
        """创建表SQL"""
        return """
            CREATE TABLE IF NOT EXISTS file_paths (
                id INTEGER NOT NULL, 
                file_path VARCHAR NOT NULL, 
                created_at DATETIME, 
                last_modified DATETIME, 
                PRIMARY KEY (id), 
                UNIQUE (file_path)
            )
        """
        

class MediaFile:
    def __init__(self, id=None, file_path=None, file_type=None, file_metadata=None, created_at=None, last_modified=None):
        self.id = id
        self.file_path = file_path
        self.file_type = file_type
        self.file_metadata = file_metadata
        self.created_at = created_at
        self.last_modified = last_modified

    def create_table_sql() -> str:
        """创建表SQL"""
        return """
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER NOT NULL, 
                file_path VARCHAR NOT NULL, 
                file_type VARCHAR NOT NULL, 
                file_metadata VARCHAR, 
                created_at DATETIME, 
                last_modified DATETIME, 
                PRIMARY KEY (id), 
                UNIQUE (file_path)
            )
        """
        
class VideoFrame:
    def __init__(self, id=None, media_file_id=None, frame_number=None, timestamp=None, frame_path=None):
        self.id = id
        self.media_file_id = media_file_id
        self.frame_number = frame_number
        self.timestamp = timestamp
        self.frame_path = frame_path

    def create_table_sql() -> str:
        """创建表SQL"""
        return """
            CREATE TABLE IF NOT EXISTS video_frames (
                id INTEGER NOT NULL, 
                media_file_id INTEGER, 
                frame_number INTEGER, 
                timestamp FLOAT, 
                frame_path VARCHAR, 
                PRIMARY KEY (id), 
                FOREIGN KEY(media_file_id) REFERENCES media_files (id)
            )
        """



class FilePathDao:

    def create_table() -> None:
        """不存在时创建表"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(FilePath.create_table_sql())
            conn.commit()
            cursor.close()
        except Exception as e:
            conn.rollback()
            log.error("Error creating file_paths table: ", e)

    def add_file_path(file_path: str) -> bool:
        """添加文件路径"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM file_paths WHERE file_path = ?", (file_path,))
            count = cursor.fetchone()[0]
            if count <= 0:
                cursor.execute(
                    "INSERT INTO file_paths (file_path, created_at, last_modified) VALUES (?, ?, ?)",
                    (file_path, datetime.utcnow(), datetime.utcnow())
                )
                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            log.error("Error adding file path: ", e)
        return False

    def file_path_count() -> int:
        """统计文件路径总数"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM file_paths")
            count = cursor.fetchone()[0]
            return count or 0
        except Exception as e:
            log.error("统计文件路径总数错误:", e)
            return 0

    def get_indexed_folders() -> List[str]:
        """获取所有已索引文件的目录"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM file_paths")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            log.error("Error getting indexed folders:", e)
            return []


class MediaFileDao:

    def create_table() -> None:
        """不存在时创建表"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(MediaFile.create_table_sql())
            conn.commit()
            cursor.close()
        except Exception as e:
            conn.rollback()
            log.error("Error creating media_files table: ", e)

    def is_file_indexed(file_path: str) -> bool:
        """判断文件是否已经索引过"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM media_files WHERE file_path = ?", (file_path,))
            value = cursor.fetchone()
            if value is None:
                return False
            return value[0] > 0
        except Exception as e:
            log.error("Error checking if file is indexed: ", e)
            return False

    def is_empty() -> bool:
        """判断数据库中media_files表是否为空"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM media_files")
            value = cursor.fetchone()
            if value is None:
                return True
            return value[0] == 0
        except Exception as e:
            log.error("Error checking if database is empty: ", e)
            return True

    def add_media_file(file_path: str, file_type: str, feature_list: List[float] = None, metadata: dict = None) -> MediaFile:
        """添加媒体文件"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            file_metadata = json.dumps(metadata) if metadata else None
            cursor.execute(
                "INSERT INTO media_files (file_path, file_type, file_metadata, created_at, last_modified) VALUES (?, ?, ?, ?, ?)",
                (file_path, file_type, file_metadata, datetime.utcnow(), datetime.utcnow())
            )
            media_file_id = cursor.lastrowid
            conn.commit()
            cursor.close()

            if feature_list is not None:
                VectorDB().add_feature_vector_media_file(media_file_id, file_path, file_type, feature_list)

            return MediaFile(
                id=media_file_id,
                file_path=file_path,
                file_type=file_type,
                file_metadata=file_metadata
            )
        except Exception as e:
            conn.rollback()
            log.error("Error adding media file: ", e)
            return None

    def get_media_files_by_id(id: int) -> MediaFile:
        """根据id获取媒体文件"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media_files WHERE id = ?", (id,))
            row = cursor.fetchone()
            if row:
                return MediaFile(*row)
            return None
        except Exception as e:
            log.error("Error getting media file by id: ", e)
            return None

    def get_media_files_by_folder(folder_path: str) -> List[str]:
        """获取数据库中该文件夹的所有文件"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media_files WHERE file_path LIKE ?", (f"{folder_path}%",))
            values = cursor.fetchall()
            if not values:
                return []
            return [row[1] for row in values]
        except Exception as e:
            log.error("Error getting media files by folder: ", e)
            return []

    def get_media_files_by_file_path(file_path: str) -> List[MediaFile]:
        """根据file_path获取媒体文件"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media_files WHERE file_path = ?", (file_path,))
            return [MediaFile(*row) for row in cursor.fetchall()]
        except Exception as e:
            log.error("Error getting media file by file_path: ", e)
            return []

    def delete_media_file(media_file: MediaFile):
        """删除媒体文件"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM media_files WHERE id = ?", (media_file.id,))
            conn.commit()
            VectorDB().delete_feature_vector_by_ids([str(media_file.id)])
        except Exception as e:
            conn.rollback()
            log.error("Error deleting media file: ", e)

class VideoFrameDao:

    def create_table() -> None:
        """不存在时创建表"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(VideoFrame.create_table_sql())
            conn.commit()
        except Exception as e:
            conn.rollback()
            log.error("Error creating video_frames table: ", e)

    def add_video_frame(media_file_id: int, frame_number: int, timestamp: float, frame_path: str, file_path: str, feature_list: List[float] = None) -> VideoFrame:
        """添加视频帧"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO video_frames (media_file_id, frame_number, timestamp, frame_path) VALUES (?, ?, ?, ?)",
                (media_file_id, frame_number, timestamp, frame_path)
            )
            video_frame_id = cursor.lastrowid
            conn.commit()

            if feature_list is not None:
                VectorDB().add_feature_vector_video_frame(
                    video_frame_id,
                    media_file_id,
                    frame_path,
                    file_path,
                    timestamp,
                    feature_list
                )
            
            return VideoFrame(
                id=video_frame_id,
                media_file_id=media_file_id,
                frame_number=frame_number,
                timestamp=timestamp,
                frame_path=frame_path
            )
        except Exception as e:
            conn.rollback()
            raise Exception(f"Error adding video frame: {str(e)}")

    def get_video_frames_by_media_file_id(media_file_id: int) -> List[VideoFrame]:
        """根据media_file_id获取视频帧"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM video_frames WHERE media_file_id = ?", (media_file_id,))
            return [VideoFrame(*row) for row in cursor.fetchall()]
        except Exception as e:
            log.error("Error getting video frames by media_file_id: ", e)
            return []

    def delete_video_frame(video_frame: VideoFrame):
        """删除视频帧"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM video_frames WHERE id = ?", (video_frame.id,))
            conn.commit()
            VectorDB().delete_feature_vector_by_ids([str(video_frame.media_file_id) + '-' + str(video_frame.id)])
        except Exception as e:
            conn.rollback()
            log.error("Error deleting video frame: ", e)

    def delete_video_frame_by_id(video_frame_id: int) -> None:
        """根据video_frame_id删除视频帧"""
        conn = SQLiteDB().get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM video_frames WHERE id = ?", (video_frame_id,))
            conn.commit()
            VectorDB().delete_feature_vector_by_ids([str(video_frame_id)])
        except Exception as e:
            conn.rollback()
            log.error("Error deleting video frame by id: ", e)
