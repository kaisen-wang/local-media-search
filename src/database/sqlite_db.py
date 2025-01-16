import os
import logging
import sqlite3
from src.config import DB_PATH
from time import sleep

log = logging.getLogger(__name__)

class SQLiteDB:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            log.info("创建 SQLiteDB 实例")
            cls._instance = super(SQLiteDB, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self) -> None:
        """初始化数据库"""
        try:
            self.db_path = DB_PATH
            
            # 如果数据库文件存在但无法写入，尝试删除它
            if os.path.exists(self.db_path):
                try:
                    # 测试写入权限
                    with open(self.db_path, 'a'):
                        pass
                except PermissionError:
                    log.error(f"No write permission for {self.db_path}, attempting to remove...")
                    os.remove(self.db_path)
                    log.error(f"Removed old database at {self.db_path}")
            
            # 创建数据库连接
            self.conn = sqlite3.connect(
                self.db_path,
                timeout=30,
                check_same_thread=False
            )
            self.conn.execute('PRAGMA journal_mode=WAL')
            self.conn.execute('PRAGMA synchronous=NORMAL')
            self.conn.execute('PRAGMA busy_timeout=30000')
            
            # 设置数据库文件权限为 600 (只有用户可以读写)
            os.chmod(self.db_path, 0o600)
            
            # 测试数据库连接
            self.conn.execute("SELECT 1")
            log.info("数据库连接测试成功")
            
        except Exception as e:
            log.error(f"Error initializing database:", e)
            raise

    def get_connection(self):
        """获取数据库连接"""
        return self.conn
        # max_retries = 3
        # retry_delay = 1  # 秒
        
        # for attempt in range(max_retries):
        #     try:
        #         # 测试连接
        #         self.conn.execute("SELECT 1")
        #         return self.conn
        #     except sqlite3.OperationalError as e:
        #         if "database is locked" in str(e) and attempt < max_retries - 1:
        #             log.warning(f"Database locked, retrying in {retry_delay} seconds...")
        #             sleep(retry_delay)
        #             retry_delay *= 2  # 指数回退
        #             continue
        #         raise

    def get_cursor(self):
        """获取数据库游标"""
        return self.get_connection().cursor()