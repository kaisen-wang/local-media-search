import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config import DB_PATH
from .base import Base

logger = logging.getLogger(__name__)

class SQLiteDB:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            logger.info("创建 SQLiteDB 实例")
            cls._instance = super(SQLiteDB, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self) -> None:
        """初始化数据库"""
        try:
            self.db_path = DB_PATH
            # 使用连接池和超时配置引擎
            self.engine = create_engine(
                f'sqlite:///{DB_PATH}',
                echo=True,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                connect_args={
                    'timeout': 30,  # 最多等待 30 秒进行锁定
                    'check_same_thread': False  # 允许多个线程
                }
            )
            
            # 启用 WAL 模式以获得更好的并发性
            def _enable_wal(dbapi_conn, connection_record):
                dbapi_conn.execute('PRAGMA journal_mode=WAL')
                dbapi_conn.execute('PRAGMA synchronous=NORMAL')
                dbapi_conn.execute('PRAGMA busy_timeout=30000')  # 30 秒超时
                
            from sqlalchemy import event
            event.listen(self.engine, 'connect', _enable_wal)
            
            self.Session = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )

            # 如果数据库文件存在但无法写入，尝试删除它
            if os.path.exists(self.db_path):
                try:
                    # 测试写入权限
                    with open(self.db_path, 'a'):
                        pass
                except PermissionError:
                    logging.error(f"No write permission for {self.db_path}, attempting to remove...")
                    os.remove(self.db_path)
                    logging.error(f"Removed old database at {self.db_path}")
            
            # 创建新的数据库和表
            Base.metadata.create_all(self.engine)
            logging.info(f"Created new database at {self.db_path}")
            
            # 设置数据库文件权限为 600 (只有用户可以读写)
            os.chmod(self.db_path, 0o600)
            
            # 测试数据库连接
            session = self.Session()
            try:
                session.execute(text("SELECT 1"))
                session.commit()
                logging.info("数据库连接测试成功")
            finally:
                session.close()
            
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
            raise

    def get_session(self):
        """获取新的数据库会话"""
        session = self.Session()
        # 为数据库锁添加重试逻辑
        from sqlalchemy.exc import OperationalError
        from time import sleep
        
        max_retries = 3
        retry_delay = 1  # 秒
        
        for attempt in range(max_retries):
            try:
                # 测试连接
                session.execute(text("SELECT 1"))
                return session
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retrying in {retry_delay} seconds...")
                    sleep(retry_delay)
                    retry_delay *= 2  # 指数回退
                    continue
                raise
