from .vector_db import VectorDB
from .sqlite_db import SQLiteDB


# 初始化数据库
def init_db() -> None:
    SQLiteDB()
    VectorDB()

