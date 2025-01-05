import os
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from typing import List
from datetime import datetime
from .vector_db import VectorDB
from .sqlite_db import SQLiteDB

Base = declarative_base()

# 初始化数据库
SQLITE_DB = SQLiteDB()
VECTOR_DB = VectorDB()

class MediaFile(Base):
    __tablename__ = 'media_files'

    id = Column(Integer, primary_key=True)
    file_path = Column(String, unique=True, nullable=False)
    file_type = Column(String, nullable=False)  # 'image' or 'video'
    feature_vector = Column(String)  # 存储特征向量的序列化字符串
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
    feature_vector = Column(String) # 特征向量
    
    media_file = relationship("MediaFile", back_populates="frames")
