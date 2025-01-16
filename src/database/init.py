from .vector_db import VectorDB
from .sqlite_db import SQLiteDB
from .models import FilePathDao, MediaFileDao, VideoFrameDao


# 初始化数据库
def init_db() -> None:
    SQLiteDB()
    VectorDB()

    FilePathDao.create_table()
    MediaFileDao.create_table()
    VideoFrameDao.create_table()
