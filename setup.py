import sys
import os
from cx_Freeze import setup, Executable

# 增加递归限制
sys.setrecursionlimit(5000)

# 依赖包配置
build_exe_options = {
    "packages": [
        # 基础包
        "os",
        "sys",
        "json",
        "datetime",
        
        # UI相关
        "PyQt6",
        
        # 数据处理相关
        "numpy",
        
        # 数据库相关
        "sqlalchemy",
        
        # 图像处理相关
        "PIL",
        "cv2",
        
        # AI模型相关
        "torch",
        "transformers",
        "tensorflow",
    ],
    
    # 排除不需要的包
    "excludes": [
        "tkinter",
        "unittest",
        "email",
        "http",
        "xml",
    ],
    
    # 添加额外文件和资源
    "include_files": [
        ("src/config.py", "config.py"),  # 配置文件
        ("models", "models"),       # 资源文件夹
    ],
    
    # 其他选项
    "include_msvcr": True,
    "zip_include_packages": "*",
    "zip_exclude_packages": "",
    "optimize": 2,
    "build_exe": "dist/LocalMediaSearch",  # 指定输出目录
}

# 创建requirements.txt文件内容
requirements = """
# UI
PyQt6>=6.5.0

# 数据处理
numpy>=1.24.0 
pandas>=1.3.0

# 数据库
SQLAlchemy>=2.0.15

# 图像处理
Pillow>=9.5.0
opencv-python>=4.5.0

# AI模型
torch>=2.2.0
transformers>=4.27.0
tensorflow>=2.8.0

# 开发工具
cx-Freeze>=6.10.0
"""

# 写入requirements.txt
with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write(requirements.strip())

# 如果是Windows系统，添加必要的DLL
if sys.platform == "win32":
    os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
    os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')
    build_exe_options['include_files'] += [
        (os.path.join(PYTHON_INSTALL_DIR, 'DLLs', 'tk86t.dll'), 'tk86t.dll'),
        (os.path.join(PYTHON_INSTALL_DIR, 'DLLs', 'tcl86t.dll'), 'tcl86t.dll'),
    ]

# 目标执行文件配置
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # 使用Windows GUI子系统

setup(
    name="LocalMediaSearch",
    version="1.0.0",
    description="本地媒体智能搜索工具",
    author="Carson",
    author_email="zmlmfok@qq.com",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "main.py",
            base=base,
            target_name="LocalMediaSearch.exe",
            icon="logo.ico",
            shortcut_name="本地媒体搜索",
            shortcut_dir="DesktopFolder"
        )
    ]
)