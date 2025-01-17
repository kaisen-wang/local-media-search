from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLineEdit, QLabel, QFileDialog, QScrollArea, QMessageBox, QProgressDialog,
                           QDialog, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QGuiApplication
from src.core.indexer import Indexer
from src.core.feature_extractor import FeatureExtractor
from src.config import CURRENT_OS, WINDOW_TITLE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, IMAGE_EXTENSIONS
from src.database.models import FilePathDao, MediaFileDao
from src.thread.workers import IndexingWorker, RefreshWorker, SearchWorker
from src.gui.label import ImageLabel
import os
import logging

log = logging.getLogger(__name__)

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
            FeatureExtractor()
            
            # 添加已索引文件夹列表
            self.indexed_folders = set()
            
            # 设置UI
            self.setup_ui()
            
            # 从数据库加载已索引的文件夹
            self.load_indexed_folders()
            
            # 自动重建索引
            self.rebuild_search_index()
            
            # 初始化进度对话框
            self.progress_dialog = None
        except Exception as e:
            log.error("Error in MainWindow initialization: ", e)
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
        
        # 添加显示菜单
        shows_menu = menubar.addMenu("显示")
        
        # 添加显示索引文件夹动作
        show_folders_action = shows_menu.addAction("索引文件夹")
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
        self.load_indexed_folders()

        file_path_count = FilePathDao.file_path_count()
        self._show_status_bar_message(f"当前已索引的文件夹数量：{file_path_count}", 5000)

        # 创建并显示文件夹对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("已索引文件夹")
        dialog.setMinimumSize(500, 300)
        
        layout = QVBoxLayout()
        
        # 添加文件夹列表
        list_widget = QListWidget()
        list_widget.setContentsMargins(10, 10, 10, 10)  # 增加内边距
        list_widget.setStyleSheet("QListWidget::item { height: 50px; }")  # 设置行高度
        for folder in sorted(self.indexed_folders):
            item = QListWidgetItem()
            list_widget.addItem(item)
        
            # 创建布局并添加按钮
            item_widget = QWidget()
            item_layout = QHBoxLayout()

            # 设置 QLabel
            folder_label = QLabel(folder)
            folder_label.setWordWrap(True)  # 允许文字换行
            item_layout.addWidget(folder_label)

            # 设置 QPushButton
            refresh_btn = QPushButton("刷新")
            refresh_btn.setFixedWidth(50)
            refresh_btn.clicked.connect(lambda checked, f=folder: self.refresh_folder(f))
            item_layout.addWidget(refresh_btn)

            item_layout.setContentsMargins(10, 10, 10, 10)  # 增加内边距
            item_widget.setLayout(item_layout)
            
            list_widget.setItemWidget(item, item_widget)
    
        layout.addWidget(list_widget)

        # 添加关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()

    def refresh_folder(self, folder):
        """指定文件夹刷新"""
        log.info(f"刷新文件夹: {folder}")
        reply = QMessageBox.question(
            self,
            '提示',
            f'是否要刷新索引文件夹？\n这将重新扫描文件夹中的变化。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.indexed_folders = [folder]
            self.refresh_indexe_folders()


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
        # 获取所有已索引文件的目录
        folders = FilePathDao.get_indexed_folders()

        for file_path in folders:
            self.indexed_folders.add(file_path)
        
        # 如果有已索引的文件夹，启用刷新按钮
        self.refresh_btn.setEnabled(len(self.indexed_folders) > 0)

    def refresh_indexes(self):
        """刷新所有已索引文件夹"""
        reply = QMessageBox.question(
            self,
            '提示',
            f'是否要刷新所有已索引文件夹？\n这将重新扫描所有文件夹中的变化。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.load_indexed_folders()
            self.refresh_indexe_folders()

    def refresh_indexe_folders(self):
        """刷新所有已索引文件夹"""
        # 创建进度对话框
        if not self.indexed_folders or len(self.indexed_folders) == 0:
            QMessageBox.information(self, "提示", "没有已索引的文件夹")
            return
        
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
        self.progress_dialog.setCancelButtonText("取消")
        
        # 创建工作线程处理所有文件夹
        self.refresh_worker = RefreshWorker(self.indexer, list(self.indexed_folders))
        self.refresh_worker.progress.connect(self.update_refresh_progress)
        self.refresh_worker.finished.connect(self.refresh_finished)
        self.refresh_worker.error.connect(self.indexing_error)
        
        self.progress_dialog.canceled.connect(self.refresh_stop)
        self.progress_dialog.show()
        self.refresh_worker.start()

    def update_refresh_progress(self, current_folder, current, total):
        """更新刷新进度"""
        if self.progress_dialog:
            folder_name = os.path.basename(current_folder)
            log.info(f"正在刷新文件夹: {current_folder}")
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
            log.info("=== 启动时重建搜索索引 ===")
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
            
            # 关闭加载对话框
            self.loading_dialog.close()
            
            # 更新状态栏
            self._show_status_bar_message(f"搜索索引加载完成", 1000)
        except Exception as e:
            log.error(f"Error rebuilding search index:", e)
            QMessageBox.warning(self, "错误", "搜索索引重建失败，请重新运行程序")
            
    def indexing_finished(self, stats: dict):
        """索引完成处理"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
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
            self.progress_dialog.setCancelButtonText("取消")
            
            # 创建索引线程
            self.index_worker = IndexingWorker(self.indexer, folder)
            self.index_worker.progress.connect(self.update_index_progress)
            self.index_worker.finished.connect(self.indexing_finished)
            self.index_worker.error.connect(self.indexing_error)
            
            self.progress_dialog.canceled.connect(self.indexing_stop)
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

    def indexing_stop(self):
        """停止索引"""
        if hasattr(self, 'index_worker') and self.index_worker:
            self.index_worker.stop()
            self._show_status_bar_message("索引已停止", 3000)

    def refresh_stop(self):
        """停止刷新索引"""
        if hasattr(self, 'refresh_worker') and self.refresh_worker:
            self.refresh_worker.stop()
            self._show_status_bar_message("刷新索引已停止", 3000)

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
            self.search_worker = SearchWorker(query, 'text')
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
        image_types = ""
        for img in IMAGE_EXTENSIONS:
            image_types = image_types + "*" + img + " "

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择搜索图片",
            "",
            f"Images ({image_types})"
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
            self.search_worker = SearchWorker(file_name, 'image')
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

    def _search_finished(self, results, is_empty):
        """搜索完成处理"""
        if self.progress_dialog:
            self.progress_dialog.close()
        if is_empty:
            self._show_status_bar_message("请选择 ‘添加索引文件夹’ 添加文件到索引中")
            return
        self.display_results(results)

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
        if not results or len(results) == 0:
            self._show_status_bar_message("没有找到匹配的结果")
            return
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
        # 回到顶部
        self.scroll_area.verticalScrollBar().setValue(0)
        self._show_status_bar_message(f"找到 {len(results)} 个结果")

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
        
        for _index, item in enumerate(results_to_display):
            score = item['score']
            metadata = item['metadata']
            media_file = MediaFileDao.get_media_files_by_id(metadata['id'])
            if media_file and os.path.exists(media_file.file_path):
                # 创建结果卡片
                result_card = self.create_result_card(media_file, score, metadata)
                self.results_layout.addWidget(result_card)
        
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
            thumbnail_path = metadata['frame_path']
        
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
        
        if result_type == 'video' or result_type == 'video_frame':
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
        log.info(f"Opening folder for: {path}")
        if CURRENT_OS == 'linux':
            os.system(f'xdg-open "{os.path.dirname(path)}"')
        elif CURRENT_OS == 'windows':
            os.startfile(os.path.dirname(path))
        elif CURRENT_OS == 'macos':
            os.system(f'open -R "{path}"')
        else:
            raise ValueError("Unsupported OS")
    
    def play_video_at_timestamp(self, video_path: str, timestamp: float):
        """使用系统默认视频播放器播放视频，并尝试跳转到指定时间"""
        log.info(f"Playing video: {video_path}, timestamp: {timestamp}")

        if CURRENT_OS == 'linux':
            os.system(f'xdg-open "{video_path}"')
        elif CURRENT_OS == 'windows':
            os.system(f'start cmd /c "{video_path}" -t {timestamp}')
        elif CURRENT_OS == 'macos':
            os.system(f'open -R "{video_path}"')
        else:
            raise ValueError("Unsupported OS")
