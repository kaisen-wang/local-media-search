import sys
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from src.gui.main_window import MainWindow
from src.database.init import init_db
from src.config import setup_logging, LOGGER_LEVEL

def initialize_app():
    """初始化应用程序"""
    try:
        # 确保数据库初始化
        init_db()
        return True
    except Exception as e:
        QMessageBox.critical(
            None,
            "初始化错误",
            f"程序初始化失败：{str(e)}\n请确保您有写入权限并重试。"
        )
        return False

def main():
    # 初始化日志
    setup_logging(LOGGER_LEVEL)
    logger = logging.getLogger(__name__)
    
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("LocalMediaSearch")
    app.setApplicationDisplayName("本地媒体智能搜索工具")
    # 添加图标
    app.setWindowIcon(QIcon("resources/logo.ico"))
    
    # 初始化应用
    if not initialize_app():
        return 1
        
    try:
        # 创建并显示主窗口
        window = MainWindow()
        window.show()
        
        # 记录主窗口显示
        logger.info("主窗口已显示")
        
        # 启动事件循环
        logger.info("启动应用程序事件循环")
        return app.exec()
    except Exception as e:
        logger.error(f"应用程序运行出错: ", e, exc_info=True)
        QMessageBox.critical(
            None,
            "错误",
            f"程序运行出错：{str(e)}"
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())
