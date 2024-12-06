import os
# from pathlib import Path
from dotenv import load_dotenv
import torch
import platform

# 加载.env文件
load_dotenv()

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
CACHE_DIR = get_path(os.getenv('CACHE_DIR', '~/.cache/LocalMediaSearch'))

# 模型配置
DEVICE = get_device()
# MODEL_NAME = get_path(os.getenv('MODEL_NAME', 'OFA-Sys/chinese-clip-vit-base-patch16'))
MODEL_NAME = get_path(os.getenv('MODEL_NAME', './data/models/chinese-clip-vit-base-patch16'))

# 数据库配置
DB_NAME = os.getenv('DB_NAME', 'media_search.db')
DB_DIR = get_path(os.getenv('DB_DIR', '~/.config/LocalMediaSearch'))
DB_PATH = os.path.join(DB_DIR, DB_NAME)

# 图片配置
IMAGE_EXTENSIONS = os.getenv('IMAGE_EXTENSIONS', '.jpg,.jpeg,.png,.gif,.bmp').split(',')
VIDEO_EXTENSIONS = os.getenv('VIDEO_EXTENSIONS', '.mp4,.avi,.mov,.mkv').split(',')
MAX_IMAGE_SIZE = int(os.getenv('MAX_IMAGE_SIZE', '224'))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '32'))

# 界面配置
WINDOW_TITLE = os.getenv('WINDOW_TITLE', 'LocalMediaSearch')
WINDOW_MIN_WIDTH = int(os.getenv('WINDOW_MIN_WIDTH', '800'))
WINDOW_MIN_HEIGHT = int(os.getenv('WINDOW_MIN_HEIGHT', '600'))
RESULTS_PER_ROW = int(os.getenv('RESULTS_PER_ROW', '4'))
THUMBNAIL_SIZE = int(os.getenv('THUMBNAIL_SIZE', '200'))

# 创建必要的目录
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

print(f"Configuration loaded:")
print(f"- OS: {CURRENT_OS}")
print(f"- Device: {DEVICE}")
print(f"- Model: {MODEL_NAME}")
print(f"- Database path: {DB_PATH}")
print(f"- Cache directory: {CACHE_DIR}") 
