from PyQt6.QtCore import QThread, pyqtSignal
from src.core.search_engine import SearchEngine
from src.core.file_scanner import FileScanner
from src.database.models import FilePathDao, MediaFileDao, VideoFrameDao
import concurrent.futures
import logging

log = logging.getLogger(__name__)

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
            # 添加索引路径
            FilePathDao.add_file_path(self.folder)

            # 首先扫描所有文件
            media_files = FileScanner.scan_directory(self.folder)
            total_files = len(media_files)
            indexed_files = []

            # 发送进度信号
            self.progress.emit(0, total_files)

            # 使用线程池并行处理文件
            with concurrent.futures.ThreadPoolExecutor(thread_name_prefix='IndexingWorker') as executor:
                futures = {executor.submit(self.indexer.index_single_file, file_path): file_path for file_path in media_files}
                for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    file_path = futures[future]
                    try:
                        if future.result():
                            indexed_files.append(file_path)
                    except Exception as e:
                        log.error(f"Error indexing file {file_path}:", e)

                    # 发送进度信号
                    self.progress.emit(i, total_files)

            self.finished.emit(indexed_files)

        except Exception as e:
            self.error.emit(str(e))

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
            
            for folder in self.folders:
                # 获取文件夹中的所有文件
                current_files = set(FileScanner.scan_directory(folder))
                    
                # 获取数据库中该文件夹的所有文件
                db_files = set(MediaFileDao.get_media_files_by_folder(folder))
                    
                # 计算需要添加、删除的文件
                files_to_add = current_files - db_files
                files_to_remove = db_files - current_files
                
                # if not files_to_add and not files_to_remove:
                #     continue
                log.info(f"正在刷新文件夹 {folder}，新增文件数：{len(files_to_add)}, 删除文件数：{len(files_to_remove)}")
                log.info(f'新增文件: {'\n'.join(files_to_add)}')
                log.info(f'删除文件: {'\n'.join(files_to_remove)}')

                # 删除不存在的文件记录
                for file_path in files_to_remove:
                    mf_list = MediaFileDao.get_media_files_by_file_path(file_path)
                    if not mf_list:
                        continue
                    for mf in mf_list:
                        if mf.file_type == 'video':
                            vf_list = VideoFrameDao.get_video_frames_by_media_file_id(mf.id)
                            for vf in vf_list:
                                VideoFrameDao.delete_video_frame(vf)
                            
                        MediaFileDao.delete_media_file(mf)
                            
                    stats['removed'] += 1

                # 添加新文件
                total_files = len(files_to_add)
                for i, file_path in enumerate(files_to_add, 1):
                    if self.indexer.index_single_file(file_path):
                        stats['added'] += 1
                    self.progress.emit(folder, i, total_files)

            self.finished.emit(stats)
        except Exception as e:
            self.error.emit(str(e))

class SearchWorker(QThread):
    """后台搜索线程"""
    finished = pyqtSignal(list, bool)  # 完成信号，返回搜索结果
    error = pyqtSignal(str)  # 错误信号

    def __init__(self, query, type):
        super().__init__()
        self.query = query
        self.type = type

    def run(self):
        try:
            if self.type == 'image':
                results = SearchEngine.image_search(self.query)
            elif self.type == 'text':
                results = SearchEngine.text_search(self.query.strip())
            else:
                results = None
            
            is_empty = False
            
            if not results:
                results = []
                is_empty = True
            
            self.finished.emit(results, is_empty)
        except Exception as e:
            log.error("搜索文件异常", e)
            self.error.emit(str(e))
