import logging
import sqlite3
from time import sleep
from src.config import DB_PATH

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
            # 创建数据库连接
            self.conn = sqlite3.connect(
                DB_PATH,
                timeout=30,
                check_same_thread=False
            )
            self.conn.execute('PRAGMA journal_mode=WAL')
            self.conn.execute('PRAGMA synchronous=NORMAL')
            self.conn.execute('PRAGMA busy_timeout=30000')
            # 测试数据库连接
            self.conn.execute("SELECT 1")
            log.info("数据库连接测试成功")
        except Exception as e:
            log.exception(f"Error initializing database:")
            raise

    def get_connection(self):
        """获取数据库连接"""
        return self.conn

    def get_cursor(self):
        """获取数据库游标"""
        max_retries = 3
        retry_delay = 1  # 秒

        for attempt in range(max_retries):
            try:
                cursor = self.get_connection().cursor()
                # 测试连接
                cursor.execute("SELECT 1")
                return cursor
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    log.warning(f"Database locked, retrying in {retry_delay} seconds...")
                    sleep(retry_delay)
                    retry_delay *= 2  # 指数回退
                    continue
                raise
