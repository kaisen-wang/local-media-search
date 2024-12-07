from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLineEdit, QLabel, QFileDialog, QScrollArea, QMessageBox, QProgressDialog,
                           QGridLayout)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QImage
from src.core.indexer import Indexer
from src.core.search_engine import SearchEngine
import os
import subprocess
from src.database.models import Session, MediaFile
import concurrent.futures
from src.config import CURRENT_OS, WINDOW_TITLE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT

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
                        print(f"Error indexing file {file_path}: {str(e)}")

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
            print(f"Error loading image {self.file_path}: {str(e)}")

    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 在默认图片查看器中打开图片
            os.system(f'xdg-open "{self.file_path}"')  # Linux
            # 对于 Windows，使用：os.startfile(self.file_path)
            # 对于 MacOS，使用：os.system(f'open "{self.file_path}"')

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
            
            session = Session()
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Initializing MainWindow...")  # 调试信息
        
        try:
            self.setWindowTitle(WINDOW_TITLE)
            self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
            
            # 初始化核心组件
            self.indexer = Indexer()
            self.search_engine = SearchEngine()
            
            # 添加已索引文件夹列表
            self.indexed_folders = set()
            
            # 设置UI
            self.setup_ui()
            
            # 从数据库加载已索引的文件夹
            self.load_indexed_folders()
            
            # 初始化进度对话框
            self.progress_dialog = None
            
            print("MainWindow initialization complete")  # 调试信息
            
        except Exception as e:
            print(f"Error in MainWindow initialization: {str(e)}")  # 调试信息
            QMessageBox.critical(
                self,
                "初始化错误",
                f"窗口初始化失败：{str(e)}"
            )
            raise

    def setup_ui(self):
        print("Setting up UI...")  # 调试信息
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 搜索区域
        search_layout = QHBoxLayout()
        
        # 创建搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索关键词...")
        self.search_input.returnPressed.connect(self.perform_text_search)
        search_layout.addWidget(self.search_input)
        
        # 创建图片搜索按钮
        self.image_search_btn = QPushButton("图片搜索")
        self.image_search_btn.clicked.connect(self.open_image_search)
        search_layout.addWidget(self.image_search_btn)
        
        main_layout.addLayout(search_layout)
        
        # 添加文件夹按钮
        self.add_folder_btn = QPushButton("添加索引文件夹")
        self.add_folder_btn.clicked.connect(self.add_index_folder)
        main_layout.addWidget(self.add_folder_btn)
        
        # 创建按钮布局
        buttons_layout = QHBoxLayout()
        
        # 保留原有的添加文件夹按钮
        buttons_layout.addWidget(self.add_folder_btn)
        
        # 添加刷新按钮
        self.refresh_btn = QPushButton("刷新索引")
        self.refresh_btn.clicked.connect(self.refresh_indexes)
        self.refresh_btn.setEnabled(False)  # 初始状态禁用
        buttons_layout.addWidget(self.refresh_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # 创建滚动区域用于显示结果
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # 创建结果显示区域
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        
        scroll_area.setWidget(self.results_widget)
        main_layout.addWidget(scroll_area)
        
        # 添加状态栏
        self.statusBar().showMessage("就绪")
        
        print("UI setup complete")  # 调试信息

    def load_indexed_folders(self):
        """从数据库加载已索引的文件夹"""
        session = Session()
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
        self.search_engine.build_index()
        
        # 显示结果统计
        message = (
            f"刷新完成\n"
            f"新增文件：{stats['added']}\n"
            f"更新文件：{stats['updated']}\n"
            f"删除文件：{stats['removed']}"
        )
        QMessageBox.information(self, "完成", message)

    def add_index_folder(self):
        """添加索引文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择要索引的文件夹",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            # 添加到已索引文件夹集合
            self.indexed_folders.add(folder)
            # 启用刷新按钮
            self.refresh_btn.setEnabled(True)
            
            reply = QMessageBox.question(
                self,
                '确认',
                f'是否索引文件夹 {folder}？这可能需要一些时间。',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 创建进度对话框
                self.progress_dialog = QProgressDialog(
                    "正在扫描文件...", 
                    "取消", 
                    0, 
                    100, 
                    self
                )
                self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                self.progress_dialog.setAutoClose(True)
                self.progress_dialog.setAutoReset(True)
                
                # 创建并启动工作线程
                self.worker = IndexingWorker(self.indexer, folder)
                self.worker.progress.connect(self.update_progress)
                self.worker.finished.connect(self.indexing_finished)
                self.worker.error.connect(self.indexing_error)
                
                # 显示进度对话框
                self.progress_dialog.show()
                
                # 启动工作线程
                self.worker.start()

    def update_progress(self, current, total):
        """更新进度对话框"""
        if self.progress_dialog:
            progress = int((current / total) * 100)
            self.progress_dialog.setLabelText(
                f"正在索引文件... ({current}/{total})"
            )
            self.progress_dialog.setValue(progress)

    def indexing_finished(self, indexed_files):
        """索引完成处理"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        # 重建搜索索引
        if indexed_files:
            self.search_engine.build_index()
            QMessageBox.information(
                self,
                "完成",
                f"索引完成，共处理 {len(indexed_files)} 个文件"
            )
        else:
            QMessageBox.information(
                self,
                "完成",
                "没有新的文件需要索引"
            )

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
            self.statusBar().showMessage("正在搜索...")
            results = self.search_engine.text_search(query)
            self.display_results(results)
            self.statusBar().showMessage(f"找到 {len(results)} 个结果", 5000)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "搜索错误",
                f"搜索过程中发生错误：{str(e)}"
            )
            self.statusBar().showMessage("搜索失败", 5000)

    def open_image_search(self):
        """打开图片搜索对话框"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择搜索图片",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        
        if file_name:
            try:
                self.statusBar().showMessage("正在搜索...")
                results = self.search_engine.image_search(file_name)
                self.display_results(results)
                self.statusBar().showMessage(f"找到 {len(results)} 个结果", 5000)
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "搜索错误",
                    f"图片搜索过程中发生错误：{str(e)}"
                )
                self.statusBar().showMessage("搜索失败", 5000)

    def display_results(self, results):
        """显示搜索结果"""
        # 清除现有结果
        for i in reversed(range(self.results_layout.count())): 
            widget = self.results_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if not results:
            no_results_label = QLabel("没有找到匹配的结果")
            no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_layout.addWidget(no_results_label)
            return

        # 创建列表布局
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setSpacing(10)

        session = Session()
        try:
            for file_id, similarity, result_type, frame in results:
                media_file = session.query(MediaFile).get(file_id)
                if media_file and os.path.exists(media_file.file_path):
                    # 创建单行结果容器
                    row_widget = QWidget()
                    row_layout = QHBoxLayout(row_widget)
                    
                    # 缩略图
                    if result_type == 'image':
                        thumbnail_path = media_file.file_path
                    else:  # video
                        thumbnail_path = frame.frame_path
                        
                    thumbnail = QLabel()
                    pixmap = QPixmap(thumbnail_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(100, 100,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        thumbnail.setPixmap(scaled_pixmap)
                    thumbnail.setFixedSize(100, 100)
                    row_layout.addWidget(thumbnail)

                    # 文件信息
                    info_widget = QWidget()
                    info_layout = QVBoxLayout(info_widget)
                    
                    # 文件名和类型
                    filename = os.path.basename(media_file.file_path)
                    type_text = "视频" if result_type == 'video' else "图片"
                    name_label = QLabel(f"{filename} ({type_text})")
                    name_label.setStyleSheet("font-weight: bold;")
                    info_layout.addWidget(name_label)
                    
                    # 对于视频，显示时间戳
                    if result_type == 'video':
                        timestamp = frame.timestamp
                        time_label = QLabel(f"时间: {timestamp:.2f}秒")
                        info_layout.addWidget(time_label)
                    
                    # 文件路径
                    path_label = QLabel(media_file.file_path)
                    path_label.setStyleSheet("color: gray;")
                    path_label.setToolTip(media_file.file_path)
                    path_label.setMaximumWidth(400)
                    info_layout.addWidget(path_label)
                    
                    row_layout.addWidget(info_widget)

                    # 操作按钮
                    if result_type == 'video':
                        # 添加跳转到指定时间的按钮
                        play_btn = QPushButton("播放视频片段")
                        play_btn.clicked.connect(
                            lambda checked, path=media_file.file_path, time=frame.timestamp:
                            self.play_video_at_timestamp(path, time)
                        )
                        row_layout.addWidget(play_btn)
                    
                    open_folder_btn = QPushButton("打开所在文件夹")
                    open_folder_btn.clicked.connect(
                        lambda checked, path=media_file.file_path: self._open_folder(path)
                    )
                    row_layout.addWidget(open_folder_btn)

                    list_layout.addWidget(row_widget)

            # 添加列表到主布局
            self.results_layout.addWidget(list_widget)
            # 添加弹性空间
            self.results_layout.addStretch()

        except Exception as e:
            error_label = QLabel(f"显示结果时发生错误: {str(e)}")
            self.results_layout.addWidget(error_label)
            
        finally:
            session.close()
    
    def _open_folder(self, path):
        print(f"Opening folder for: {path}")
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
        print(f"Playing video: {video_path}, timestamp: {timestamp}")
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
            print(f"Error executing command: {e}")
        except FileNotFoundError as e:
            print(f"Command not found: {e}")

        # 这里使用 ffplay 播放器（需要安装 ffmpeg）
        # os.system(f'ffplay "{video_path}" -ss {timestamp}')
        # 注意：具体的播放命令可能需要根据操作系统和安装的播放器进行调整