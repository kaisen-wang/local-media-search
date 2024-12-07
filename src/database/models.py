import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from src.config import DB_PATH
# import tempfile
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

# def get_db_path():
#     """获取数据库路径"""
#     # 使用用户主目录下的 .config 目录
#     user_home = os.path.expanduser("~")
#     app_config_dir = os.path.join(user_home, '.config', 'LocalMediaSearch')
#     db_path = os.path.join(app_config_dir, 'media_search.db')

#     try:
#         # 创建配置目录（如果不存在）
#         os.makedirs(app_config_dir, exist_ok=True)
#         # 设置目录权限为 700 (只有用户可以读写)
#         os.chmod(app_config_dir, 0o700)
        
#         # 如果数据库文件存在，确保它有正确的权限
#         if os.path.exists(db_path):
#             os.chmod(db_path, 0o600)
            
#         print(f"Application directory setup complete at {app_config_dir}")
        
#     except Exception as e:
#         print(f"Error setting up application directory: {str(e)}")
#         # 如果无法创建目录，使用临时目录
#         db_path = os.path.join(tempfile.gettempdir(), 'media_search.db')
#         print(f"Falling back to temporary directory: {db_path}")

#     return db_path

# 获取数据库路径
# DB_PATH = get_db_path()

Base = declarative_base()

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

# 创建数据库引擎
engine = create_engine(f'sqlite:///{DB_PATH}', echo=True)
Session = sessionmaker(bind=engine)

def init_db():
    """初始化数据库"""
    try:
        # 如果数据库文件存在但无法写入，尝试删除它
        if os.path.exists(DB_PATH):
            try:
                # 测试写入权限
                with open(DB_PATH, 'a'):
                    pass
            except PermissionError:
                print(f"No write permission for {DB_PATH}, attempting to remove...")
                os.remove(DB_PATH)
                print(f"Removed old database at {DB_PATH}")
        
        # 创建新的数据库和表
        Base.metadata.create_all(engine)
        print(f"Created new database at {DB_PATH}")
        
        # 设置数据库文件权限为 600 (只有用户可以读写)
        os.chmod(DB_PATH, 0o600)
        
        # 测试数据库连接
        session = Session()
        try:
            session.execute(text("SELECT 1"))
            session.commit()
            print("Database connection test successful")
        finally:
            session.close()
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise