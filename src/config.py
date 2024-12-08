import os
import torch
import platform
import configparser

# 读取 config.ini 文件
config = configparser.ConfigParser()
config.read('config.ini')

def get_path(path_str: str) -> str:
    """展开路径中的波浪号和环境变量"""
    return os.path.expandvars(os.path.expanduser(path_str))

# 检测CUDA可用性
def get_device():
    if torch.cuda.is_available() and torch.version.cuda is not None:
        return 'cuda'
    else:
        print("CUDA not available or torch not compiled with CUDA, using CPU instead")
        return 'cpu'

# 获取是什么操作系统 (Windows, Linux, macOS)
def get_os():
    if platform.system() == 'Windows':
        return 'windows'
    elif platform.system() == 'Linux':
        return 'linux'
    elif platform.system() == 'Darwin':
        return 'macos'
    else:
        raise ValueError("Unsupported OS")

# 获取当前操作系统
CURRENT_OS = get_os()

# 缓存配置
CACHE_DIR = get_path(config.get('Cache', 'cache_dir', fallback='./data/cache'))

# 模型配置
DEVICE = get_device()
MODEL_NAME = get_path(config.get('Model', 'model_name', fallback='./models/chinese-clip-vit-base-patch16'))

# 数据库配置
DB_NAME = config.get('Database', 'db_name', fallback='media_search.db')
DB_DIR = get_path(config.get('Database', 'db_dir', fallback='./data/db'))
DB_PATH = os.path.join(DB_DIR, DB_NAME)

# 媒体文件配置
IMAGE_EXTENSIONS = config.get('Media', 'image_extensions', fallback='.jpg,.jpeg,.png,.gif,.bmp').split(',')
VIDEO_EXTENSIONS = config.get('Media', 'video_extensions', fallback='.mp4,.avi,.mov,.mkv,.wmv,.flv,.avi,.rmvb,.webm').split(',')
MAX_IMAGE_SIZE = config.getint('Media', 'max_image_size', fallback=224)
BATCH_SIZE = config.getint('Media', 'batch_size', fallback=32)

# 界面配置
WINDOW_TITLE = config.get('Window', 'title', fallback='LocalMediaSearch')
WINDOW_MIN_WIDTH = config.getint('Window', 'min_width', fallback=800)
WINDOW_MIN_HEIGHT = config.getint('Window', 'min_height', fallback=600)
RESULTS_PER_ROW = config.getint('Window', 'results_per_row', fallback=4)
THUMBNAIL_SIZE = config.getint('Window', 'thumbnail_size', fallback=200)

# 创建必要的目录
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

print(f"Configuration loaded:")
print(f"- OS: {CURRENT_OS}")
print(f"- Device: {DEVICE}")
print(f"- Model: {MODEL_NAME}")
print(f"- Database path: {DB_PATH}")
print(f"- Cache directory: {CACHE_DIR}") 
