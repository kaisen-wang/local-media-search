import sys
import os
from cx_Freeze import setup, Executable
import platform

# 增加递归限制
sys.setrecursionlimit(5000)

# 获取当前系统
SYSTEM = platform.system().lower()

# 基础依赖包配置
build_exe_options = {
    "packages": [
        # 基础包
        "os", "sys", "json", "datetime",
        # UI相关
        "PyQt6",
        # 数据处理相关
        "numpy",
        # 数据库相关
        "sqlalchemy",
        # 图像处理相关
        "PIL", "cv2",
        # AI模型相关
        "torch", "transformers", "tensorflow",
    ],
    "excludes": [
        "tkinter", "unittest", "email", "http", "xml",
    ],
    "include_files": [
        ("config.ini", "config.ini"),
        ("models", "models"),
    ],
    "include_msvcr": True,
    "zip_include_packages": "*",
    "zip_exclude_packages": "",
    "optimize": 2,
}

# 平台特定配置
if SYSTEM == "windows":
    build_exe_options.update({
        "build_exe": "dist/windows/LocalMediaSearch",
        "include_files": build_exe_options["include_files"] + [
            ("resources/logo.ico", "logo.ico"),
        ]
    })
    if hasattr(sys, 'real_prefix'):  # 检查是否在虚拟环境中
        PYTHON_INSTALL_DIR = sys.real_prefix
    else:
        PYTHON_INSTALL_DIR = sys.base_prefix
    
    os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
    os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')
    
elif SYSTEM == "darwin":
    build_exe_options.update({
        "build_exe": "dist/macos/LocalMediaSearch.app/Contents/MacOS",
        "include_files": build_exe_options["include_files"] + [
            ("resources/logo.icns", "logo.icns"),
        ]
    })
elif SYSTEM == "linux":
    build_exe_options.update({
        "build_exe": "dist/linux/LocalMediaSearch",
        "include_files": build_exe_options["include_files"] + [
            ("debian/LocalMediaSearch.desktop", "LocalMediaSearch.desktop"),
        ]
    })

# 目标执行文件配置
base = None
if SYSTEM == "windows":
    base = "Win32GUI"

# 平台特定的可执行文件配置
executables = []
if SYSTEM == "windows":
    executables.append(
        Executable(
            "main.py",
            base=base,
            target_name="LocalMediaSearch.exe",
            icon="resources/logo.ico",
            shortcut_name="本地媒体搜索",
            shortcut_dir="DesktopFolder"
        )
    )
elif SYSTEM == "darwin":
    executables.append(
        Executable(
            "main.py",
            base=base,
            target_name="LocalMediaSearch",
            icon="resources/logo.icns"
        )
    )
else:  # Linux
    executables.append(
        Executable(
            "main.py",
            base=base,
            target_name="LocalMediaSearch",
            icon="resources/logo.jpeg"
        )
    )

setup(
    name="LocalMediaSearch",
    version="1.0.0",
    description="本地媒体智能搜索工具",
    author="Carson",
    author_email="zmlmfok@qq.com",
    options={"build_exe": build_exe_options},
    executables=executables
)