from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLineEdit, QLabel, QFileDialog, QScrollArea, QMessageBox, QProgressDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QGuiApplication
from src.core.indexer import Indexer
from src.core.search_engine import SearchEngine
import os
import json
import logging
import subprocess
from src.database.models import MediaFile, VideoFrame
from src.database.sqlite_db import SQLiteDB
import concurrent.futures
from src.config import CURRENT_OS, WINDOW_TITLE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
import traceback

logging = logging.getLogger(__name__)

class IndexingWorker(QThread):
    """后台索引线程"""
    progress = pyqtSignal(int, int)  # 当前进度，总数
    finished = pyqtSignal(list)  # 完成信号，返回索引的文件列表
    error = pyqtSignal(str)  # 错误信号

    def __init__(self, indexer, folder):
        super().__init__()
        self.indexer = indexer
        self.folder = folder

    def run(self):
        try:
            # 首先扫描所有文件
            media_files = self.indexer.file_scanner.scan_directory(self.folder)
            total_files = len(media_files)
            indexed_files = []

            # 使用线程池并行处理文件
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(self.indexer.index_single_file, file_path): file_path for file_path in media_files}
                for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    file_path = futures[future]
                    try:
                        if future.result():
                            indexed_files.append(file_path)
                    except Exception as e:
                        logging.error(f"Error indexing file {file_path}: {str(e)}")

                    # 发送进度信号
                    self.progress.emit(i, total_files)

            self.finished.emit(indexed_files)

        except Exception as e:
            self.error.emit(str(e))

class ImageLabel(QLabel):
    """可点击的图片标签"""
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self.setMaximumSize(200, 200)
        self.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
            QLabel:hover {
                border: 1px solid #999;
                background-color: #f0f0f0;
            }
        """)
        self.load_image()

    def load_image(self):
        """加载并显示图片"""
        try:
            pixmap = QPixmap(self.file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    190, 190,  # 略小于标签大小，留出边距
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.setPixmap(scaled_pixmap)
                # 设置工具提示显示文件路径
                self.setToolTip(self.file_path)
            else:
                self.setText("无法加载图片")
        except Exception as e:
            self.setText("加载错误")
            logging.error(f"Error loading image {self.file_path}: {str(e)}")

    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 在默认图片查看器中打开图片
            if CURRENT_OS == 'linux':
                os.system(f'xdg-open "{self.file_path}"')  # Linux
            elif CURRENT_OS == 'windows':
                os.startfile(self.file_path) # Windows
            elif CURRENT_OS == 'macos':
                os.system(f'open "{self.file_path}"')   # MacOS
            else:
                raise ValueError("Unsupported OS")

class RefreshWorker(QThread):
    """后台刷新线程"""
    progress = pyqtSignal(str, int, int)  # 当前文件夹，当前进度，总数
    finished = pyqtSignal(dict)  # 完成信号，返回统计信息
    error = pyqtSignal(str)  # 错误信号

    def __init__(self, indexer, folders):
        super().__init__()
        self.indexer = indexer
        self.folders = folders

    def run(self):
        try:
            stats = {
                'added': 0,    # 新增文件数
                'updated': 0,  # 更新文件数
                'removed': 0   # 删除文件数
            }
            
            session = SQLiteDB().get_session()
            try:
                for folder in self.folders:
                    # 获取文件夹中的所有文件
                    current_files = set(self.indexer.file_scanner.scan_directory(folder))
                    
                    # 获取数据库中该文件夹的所有文件
                    db_files = set(
                        path[0] for path in 
                        session.query(MediaFile.file_path)
                        .filter(MediaFile.file_path.like(f"{folder}%"))
                        .all()
                    )
                    
                    # 计算需要添加、删除的文件
                    files_to_add = current_files - db_files
                    files_to_remove = db_files - current_files
                    
                    # 删除不存在的文件记录
                    for file_path in files_to_remove:
                        session.query(MediaFile).filter_by(file_path=file_path).delete()
                        stats['removed'] += 1
                    
                    # 添加新文件
                    total_files = len(files_to_add)
                    for i, file_path in enumerate(files_to_add, 1):
                        if self.indexer.index_single_file(file_path):
                            stats['added'] += 1
                        self.progress.emit(folder, i, total_files)
                    
                    session.commit()
                    
                self.finished.emit(stats)
                
            finally:
                session.close()
                
        except Exception as e:
            self.error.emit(str(e))

class SearchWorker(QThread):
    """后台搜索线程"""
    finished = pyqtSignal(list)  # 完成信号，返回搜索结果
    error = pyqtSignal(str)  # 错误信号

    def __init__(self, search_engine, query, type):
        super().__init__()
        self.search_engine = search_engine
        self.query = query
        self.type = type

    def run(self):
        try:
            if type == 'image':
                results = self.search_engine.image_search(self.query)
            else:
                results = self.search_engine.text_search(self.query)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        
        try:
            # self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
            self.resize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
            self.setWindowTitle(WINDOW_TITLE)
            self.setCenter()
            
            # 初始化核心组件
            self.indexer = Indexer()
            self.search_engine = SearchEngine()
            
            # 添加已索引文件夹列表
            self.indexed_folders = set()
            
            # 设置UI
            self.setup_ui()
            
            # 从数据库加载已索引的文件夹
            # self.load_indexed_folders()
            
            # 自动重建索引
            self.rebuild_search_index()
            
            # 初始化进度对话框
            self.progress_dialog = None
        except Exception as e:
            logging.error("Error in MainWindow initialization: ", e)
            QMessageBox.critical(
                self,
                "初始化错误",
                f"窗口初始化失败：{str(e)}"
            )
            raise
    
    def setCenter(self):
        screen = QGuiApplication.primaryScreen().size()
        size = self.geometry()
        self.move(int((screen.width() - size.width()) / 2), int((screen.height() - size.height()) / 2))

    def _show_status_bar_message(self, message: str, msecs: int = -1):  
        # 使用showMessage替换showStatusBar
        self.statusBar().clearMessage()

        self.statusBar().showMessage(message, msecs)

    def setup_ui(self):
        """UI设置"""
        # 创建菜单栏
        menubar = self.menuBar()
        
        # 添加设置菜单
        settings_menu = menubar.addMenu("设置")
        
        # 添加显示索引文件夹动作
        show_folders_action = settings_menu.addAction("显示索引文件夹")
        show_folders_action.triggered.connect(self.show_indexed_folders)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 搜索区域
        search_layout = QHBoxLayout()
        
        # 创建搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索关键词...")
        self.search_input.setMinimumWidth(300)
        self.search_input.returnPressed.connect(self.perform_text_search)
        search_layout.addWidget(self.search_input)
        
        # 创建图片搜索按钮
        self.image_search_btn = QPushButton("图片搜索")
        self.image_search_btn.setIcon(QIcon.fromTheme("image-x-generic"))
        self.image_search_btn.clicked.connect(self.open_image_search)
        search_layout.addWidget(self.image_search_btn)
        
        main_layout.addLayout(search_layout)
        
        # 工具栏区域
        toolbar_layout = QHBoxLayout()
        
        # 添加文件夹按钮
        self.add_folder_btn = QPushButton("添加索引文件夹")
        self.add_folder_btn.setIcon(QIcon.fromTheme("folder-new"))
        self.add_folder_btn.clicked.connect(self.add_index_folder)
        toolbar_layout.addWidget(self.add_folder_btn)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新索引")
        self.refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_btn.clicked.connect(self.refresh_indexes)
        self.refresh_btn.setEnabled(False) # 初始状态禁用
        toolbar_layout.addWidget(self.refresh_btn)
        
        # 添加弹性空间
        toolbar_layout.addStretch()
        
        main_layout.addLayout(toolbar_layout)
        
        # 创建结果显示区域
        self.create_results_area()
        
        # 状态栏
        self._show_status_bar_message("就绪")

    def show_indexed_folders(self):
        """显示当前索引的文件夹"""
        if not self.indexed_folders:
            QMessageBox.information(self, "提示", "没有已索引的文件夹")
            return
            
        folders = "\n".join(self.indexed_folders)
        QMessageBox.information(
            self,
            "已索引文件夹",
            f"当前已索引的文件夹：\n\n{folders}"
        )

    def create_results_area(self):
        """创建优化的结果显示区域"""
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 创建结果容器
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(10)
        self.results_layout.setContentsMargins(10, 10, 10, 10)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 设置最小宽度以确保内容填充
        self.results_widget.setMinimumWidth(self.scroll_area.viewport().width())
        
        self.scroll_area.setWidget(self.results_widget)
        self.centralWidget().layout().addWidget(self.scroll_area)
        
        # 连接大小变化信号
        self.scroll_area.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        """处理事件过滤"""
        if obj == self.scroll_area.viewport() and event.type() == event.Type.Resize:
            self.results_widget.setMinimumWidth(self.scroll_area.viewport().width())
        return super().eventFilter(obj, event)

    def load_indexed_folders(self):
        """从数据库加载已索引的文件夹"""
        session = SQLiteDB().get_session()
        try:
            # 获取所有已索引文件的目录
            folders = session.query(MediaFile.file_path).distinct().all()
            for (file_path,) in folders:
                folder = os.path.dirname(file_path)
                self.indexed_folders.add(folder)
            
            # 如果有已索引的文件夹，启用刷新按钮
            self.refresh_btn.setEnabled(len(self.indexed_folders) > 0)
        finally:
            session.close()

    def refresh_indexes(self):
        """刷新所有已索引文件夹"""
        if not self.indexed_folders:
            QMessageBox.information(self, "提示", "没有已索引的文件夹")
            return
            
        reply = QMessageBox.question(
            self,
            '确认',
            f'是否要刷新所有已索引文件夹？\n这将重新扫描所有文件夹中的变化。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 创建进度对话框
            self.progress_dialog = QProgressDialog(
                "正在刷新索引...", 
                "取消", 
                0, 
                len(self.indexed_folders), 
                self
            )
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setAutoClose(True)
            self.progress_dialog.setAutoReset(True)
            
            # 创建工作线程处理所有文件夹
            self.refresh_worker = RefreshWorker(self.indexer, list(self.indexed_folders))
            self.refresh_worker.progress.connect(self.update_refresh_progress)
            self.refresh_worker.finished.connect(self.refresh_finished)
            self.refresh_worker.error.connect(self.indexing_error)
            
            self.progress_dialog.show()
            self.refresh_worker.start()

    def update_refresh_progress(self, current_folder, current, total):
        """更新刷新进度"""
        if self.progress_dialog:
            folder_name = os.path.basename(current_folder)
            self.progress_dialog.setLabelText(
                f"正在刷新文件夹: {folder_name}\n"
                f"进度: {current}/{total}"
            )
            self.progress_dialog.setValue(current)

    def refresh_finished(self, stats):
        """刷新完成处理"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        # 重建搜索索引
        # self.search_engine.build_index()
        
        # 显示结果统计
        message = (
            f"刷新完成\n"
            f"新增文件：{stats['added']}\n"
            f"更新文件：{stats['updated']}\n"
            f"删除文件：{stats['removed']}"
        )
        QMessageBox.information(self, "完成", message)
        
    def rebuild_search_index(self):
        """重建搜索索引"""
        try:
            logging.error("=== Rebuilding search index on startup ===")
            # 显示加载对话框
            self.loading_dialog = QProgressDialog(
                "正在加载搜索索引...", 
                None,  # 不显示取消按钮
                0, 
                0,  # 不确定进度
                self
            )
            self.loading_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.loading_dialog.setAutoClose(True)
            self.loading_dialog.setCancelButton(None)  # 禁用取消按钮
            self.loading_dialog.show()
            
            # 验证数据库
            self.search_engine.verify_database()
            
            # 重建搜索索引
            # self.search_engine.build_index()
            
            # 关闭加载对话框
            self.loading_dialog.close()
            
            # 更新状态栏
            self._show_status_bar_message(f"搜索索引加载完成")
            
        except Exception as e:
            logging.error(f"Error rebuilding search index: {str(e)}")
            traceback.print_exc()
            QMessageBox.warning(self, "错误", "搜索索引重建失败，请重新运行程序")
            
    def indexing_finished(self, stats: dict):
        """索引完成处理"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        # 验证数据库
        self.search_engine.verify_database()
        
        # 重建搜索索引
        # self.search_engine.build_index()
        
        # 显示统计信息
        message = (
            f"索引完成！\n"
            f"处理文件：{stats['processed']}\n"
            f"成功索引：{stats['success']}\n"
            f"失败文件：{stats['failed']}\n"
            f"删除文件：{stats['removed']}"
        )
        QMessageBox.information(self, "完成", message)

    def add_index_folder(self):
        """添加索引文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            # 启用刷新按钮
            self.refresh_btn.setEnabled(True)
            # 显示进度对话框
            self.progress_dialog = QProgressDialog(
                "正在索引文件...", 
                "取消", 
                0, 
                100, 
                self
            )
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setAutoClose(True)
            self.progress_dialog.setAutoReset(True)
            
            # 创建索引线程
            self.index_worker = IndexingWorker(self.indexer, folder)
            self.index_worker.progress.connect(self.update_index_progress)
            self.index_worker.finished.connect(self.indexing_finished)
            self.index_worker.error.connect(self.indexing_error)
            
            self.progress_dialog.show()
            self.index_worker.start()

    def update_index_progress(self, current, total):
        """更新进度对话框"""
        if self.progress_dialog:
            progress = int((current / total) * 100)
            self.progress_dialog.setLabelText(
                f"正在索引文件... ({current}/{total})"
            )
            self.progress_dialog.setValue(progress)

    def indexing_finished(self):
        """索引完成处理"""
        if self.progress_dialog:
            self.progress_dialog.close()
        
        # 验证数据库
        self.search_engine.verify_database()
        
        # 重建搜索索引
        # self.search_engine.build_index()
        
        QMessageBox.information(self, "完成", "索引建立完成！")

    def indexing_error(self, error_msg):
        """索引错误处理"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        QMessageBox.critical(
            self,
            "错误",
            f"索引过程中发生错误：{error_msg}"
        )

    def perform_text_search(self):
        """执行文本搜索"""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
            
        try:
            # 显示加载对话框
            self.progress_dialog = QProgressDialog(
                "正在搜索...", 
                None,  # 不显示取消按钮
                0, 
                0,  # 设置为0表示不确定进度
                self
            )
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setAutoClose(True)
            self.progress_dialog.setCancelButton(None)  # 禁用取消按钮
            self.progress_dialog.setMinimumDuration(0)  # 立即显示
            
            # 创建搜索线程
            self.search_worker = SearchWorker(self.search_engine, query, 'text')
            self.search_worker.finished.connect(self._search_finished)
            self.search_worker.error.connect(self._search_error)
            
            self._show_status_bar_message("正在搜索...")
            self.progress_dialog.show()
            self.search_worker.start()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "搜索错误",
                f"搜索过程中发生错误：{str(e)}"
            )
            self._show_status_bar_message("搜索失败", 5000)

    def open_image_search(self):
        """打开图片搜索对话框"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择搜索图片",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        
        if not file_name:
            QMessageBox.warning(self, "提示", "请选择要搜索的图片")
            return
        

        try:
            # 显示加载对话框
            self.progress_dialog = QProgressDialog(
                "正在搜索...", 
                None,  # 不显示取消按钮
                0, 
                0,  # 设置为0表示不确定进度
                self
            )
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setAutoClose(True)
            self.progress_dialog.setCancelButton(None)  # 禁用取消按钮
            self.progress_dialog.setMinimumDuration(0)  # 立即显示
            
            # 创建搜索线程
            self.search_worker = SearchWorker(self.search_engine, file_name, 'image')
            self.search_worker.finished.connect(self._search_finished)
            self.search_worker.error.connect(self._search_error)
            
            self._show_status_bar_message("正在搜索...")
            self.progress_dialog.show()
            self.search_worker.start()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "搜索错误",
                f"图片搜索过程中发生错误：{str(e)}"
            )
            self._show_status_bar_message("搜索失败", 5000)

    def _search_finished(self, results):
        """搜索完成处理"""
        if self.progress_dialog:
            self.progress_dialog.close()
        self.display_results(results)
        self._show_status_bar_message(f"找到 {len(results)} 个结果")

    def _search_error(self, error_msg):
        """搜索错误处理"""
        if self.progress_dialog:
            self.progress_dialog.close()
        QMessageBox.critical(
            self,
            "搜索错误",
            f"搜索过程中发生错误：{error_msg}"
        )
        self._show_status_bar_message("搜索失败", 5000)

    def display_results(self, results):
        """优化的结果显示方法"""
        # 存储所有结果
        self.all_results = results
        self.current_page = 0
        self.items_per_page = 20
        
        # 清除现有结果
        for i in reversed(range(self.results_layout.count())): 
            widget = self.results_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if not self.all_results:
            no_results_label = QLabel("没有找到匹配的结果")
            no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_results_label.setStyleSheet("color: gray; padding: 20px;")
            self.results_layout.addWidget(no_results_label)
            return

        # 显示前20条数据
        self.load_more_results()
        
        # 连接滚动事件
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.check_scroll_bottom)

    def check_scroll_bottom(self):
        """检查是否滚动到底部"""
        scrollbar = self.scroll_area.verticalScrollBar()
        if scrollbar.value() == scrollbar.maximum():
            self.load_more_results()

    def load_more_results(self):
        """加载更多结果"""
        length = len(self.all_results)
        start_index = self.current_page * self.items_per_page
        if start_index >= length:
            return
        end_index = min((start_index + self.items_per_page), length)
        results_to_display = self.all_results[start_index:end_index]
        
        session = SQLiteDB().get_session()
        try:
            for _index, item in enumerate(results_to_display):
                score = item['score']
                metadata = item['metadata']
                print(f'metadata type is {type(metadata)}, metadata={metadata}')
                media_file = session.query(MediaFile).get(metadata['id'])
                if media_file and os.path.exists(media_file.file_path):
                    # 创建结果卡片
                    result_card = self.create_result_card(media_file, score, metadata)
                    self.results_layout.addWidget(result_card)
        finally:
            session.close()
        
        self.current_page += 1

    def create_result_card(self, media_file, similarity, metadata):
        """创建单个结果卡片"""
        result_type = metadata['file_type']
        card = QWidget()
        # 设置宽度
        card.setFixedWidth(WINDOW_MIN_WIDTH - 60)
        card.setStyleSheet("""
            QWidget {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QWidget:hover {
                border-color: #999;
            }
        """)
        
        layout = QHBoxLayout(card)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 设置布局居中对齐
        
        # 缩略图
        if result_type == 'image':
            thumbnail_path = media_file.file_path
        else:
            thumbnail_path = metadata['file_path']
            
        thumbnail = ImageLabel(thumbnail_path) # QLabel()
        thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 设置标签居中对齐
        # pixmap = QPixmap(thumbnail_path)
        # if not pixmap.isNull():
        #     scaled_pixmap = pixmap.scaled(
        #         150, 150,
        #         Qt.AspectRatioMode.KeepAspectRatio,
        #         Qt.TransformationMode.SmoothTransformation
        #     )
        #     thumbnail.setPixmap(scaled_pixmap)
        thumbnail.setFixedSize(150, 150)
        layout.addWidget(thumbnail)
        
        # 信息区域
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # 文件名和类型
        filename = os.path.basename(media_file.file_path)
        type_text = "图片" if result_type == 'image' else "视频"
        name_label = QLabel(f"{filename} ({type_text})")
        name_label.setStyleSheet("font-weight: bold;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addWidget(name_label)
        
        # 相似度
        similarity_label = QLabel(f"相似度: {similarity:.2%}")
        # similarity_label.setStyleSheet("color: #666;")
        info_layout.addWidget(similarity_label)
        
        # 视频时间戳
        if result_type == 'video' or result_type == 'video_frame':
            timestamp = metadata['timestamp']
            time_label = QLabel(f"时间: {timestamp:.2f}秒")
            # time_label.setStyleSheet("color: #666;")
            info_layout.addWidget(time_label)
        
        # 文件路径
        path_label = QLabel(media_file.file_path)
        # path_label.setStyleSheet("color: gray;")
        path_label.setToolTip(media_file.file_path) # 设置工具提示
        path_label.setWordWrap(False) # 禁止换行
        path_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # path_label.setElideMode(Qt.TextElideMode.ElideRight)  # 隐藏末尾部分
        info_layout.addWidget(path_label)
        
        layout.addWidget(info_widget, stretch=1)
        
        # 操作按钮
        buttons_widget = QWidget()
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setSpacing(5)
        
        if result_type == 'video':
            play_btn = QPushButton("播放片段")
            play_btn.setIcon(QIcon.fromTheme("media-playback-start"))
            play_btn.clicked.connect(
                lambda: self.play_video_at_timestamp(media_file.file_path, metadata['timestamp'])
            )
            buttons_layout.addWidget(play_btn)
        
        open_folder_btn = QPushButton("打开文件夹")
        open_folder_btn.setIcon(QIcon.fromTheme("folder"))
        open_folder_btn.clicked.connect(
            lambda: self._open_folder(media_file.file_path)
        )
        buttons_layout.addWidget(open_folder_btn)
        
        layout.addWidget(buttons_widget)
        
        return card
    
    def _open_folder(self, path):
        logging.info(f"Opening folder for: {path}")
        if CURRENT_OS == 'linux':
            os.system(f'xdg-open "{os.path.dirname(path)}"')
        elif CURRENT_OS == 'windows':
            os.startfile(os.path.dirname(path))
        elif CURRENT_OS == 'macos':
            os.system(f'open -R "{path}"')
        else:
            raise ValueError("Unsupported OS")
    
    def play_video_at_timestamp(self, video_path: str, timestamp: float):
        """使用默认播放器播放视频，并尝试跳转到指定时间"""
        logging.info(f"Playing video: {video_path}, timestamp: {timestamp}")
        command = []

        if CURRENT_OS == 'windows':
            # 使用默认播放器
            command = ['start', '', video_path]
        elif CURRENT_OS == 'macos':  # macOS
            # 使用默认播放器
            command = ['open', video_path]
        elif CURRENT_OS == 'linux':
            # 使用默认播放器
            command = ['xdg-open', video_path]
        else:
            raise ValueError("Unsupported OS")

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error executing command: {e}")
        except FileNotFoundError as e:
            logging.error("Command not found: ", e)

        # 这里使用 ffplay 播放器（需要安装 ffmpeg）
        # os.system(f'ffplay "{video_path}" -ss {timestamp}')
        # 注意：具体的播放命令可能需要根据操作系统和安装的播放器进行调整
