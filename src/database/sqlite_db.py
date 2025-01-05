import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config import DB_PATH
from .models import Base

class SQLiteDB:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(SQLiteDB, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self) -> None:
        """初始化数据库"""
        try:
            self.db_path = DB_PATH
            self.engine = create_engine(f'sqlite:///{DB_PATH}', echo=True)
            self.Session = sessionmaker(bind=self.engine)

            # 如果数据库文件存在但无法写入，尝试删除它
            if os.path.exists(self.db_path):
                try:
                    # 测试写入权限
                    with open(self.db_path, 'a'):
                        pass
                except PermissionError:
                    print(f"No write permission for {self.db_path}, attempting to remove...")
                    os.remove(self.db_path)
                    print(f"Removed old database at {self.db_path}")
            
            # 创建新的数据库和表
            Base.metadata.create_all(self.engine)
            print(f"Created new database at {self.db_path}")
            
            # 设置数据库文件权限为 600 (只有用户可以读写)
            os.chmod(self.db_path, 0o600)
            
            # 测试数据库连接
            session = self.Session()
            try:
                session.execute(text("SELECT 1"))
                session.commit()
                print("Database connection test successful")
            finally:
                session.close()
            
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            raise

    def get_session(self):
        """获取新的数据库会话"""
        return self.Session()


