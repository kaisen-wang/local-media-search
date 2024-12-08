#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import shutil

SYSTEM = platform.system().lower()

def install_requirements():
    """安装依赖包"""
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def build_windows():
    """Windows打包"""
    print("正在构建Windows安装包...")
    # 使用cx_Freeze构建
    subprocess.run([sys.executable, "setup.py", "build", "--include-module=http.client"])
    
    # 使用NSIS创建安装程序
    if os.path.exists("installer.nsi"):
        subprocess.run(["makensis", "installer.nsi"])
    
    print("Windows安装包构建完成！")

def build_macos():
    """macOS打包"""
    print("正在构建macOS安装包...")
    # 使用cx_Freeze构建
    subprocess.run([sys.executable, "setup.py", "build"])
    
    # 创建DMG
    app_path = "dist/macos/LocalMediaSearch.app"
    dmg_path = "dist/LocalMediaSearch.dmg"
    
    if os.path.exists(app_path):
        subprocess.run([
            "hdiutil", "create", "-volname", "LocalMediaSearch",
            "-srcfolder", app_path, "-ov", "-format", "UDZO", dmg_path
        ])
    
    print("macOS安装包构建完成！")

def build_linux():
    """Linux打包"""
    print("正在构建Linux安装包...")
    
    # 创建必要的目录
    os.makedirs("debian/LocalMediaSearch/usr/lib/LocalMediaSearch", exist_ok=True)
    os.makedirs("debian/LocalMediaSearch/usr/share/applications", exist_ok=True)
    
    # 使用cx_Freeze构建
    subprocess.run([sys.executable, "setup.py", "build"])
    
    # 复制文件到debian目录
    shutil.copytree(
        "dist/linux/LocalMediaSearch",
        "debian/LocalMediaSearch/usr/lib/LocalMediaSearch",
        dirs_exist_ok=True
    )
    
    # 复制desktop文件
    shutil.copy2(
        "debian/LocalMediaSearch.desktop",
        "debian/LocalMediaSearch/usr/share/applications/"
    )
    
    # 构建deb包
    subprocess.run(["dpkg-buildpackage", "-b", "-us", "-uc"])
    
    print("Linux安装包构建完成！")

def main():
    """主函数"""
    # 安装依赖
    install_requirements()
    
    # 根据系统选择打包方式
    if SYSTEM == "windows":
        build_windows()
    elif SYSTEM == "darwin":
        build_macos()
    elif SYSTEM == "linux":
        build_linux()
    else:
        print(f"不支持的操作系统: {SYSTEM}")
        sys.exit(1)

if __name__ == "__main__":
    main() 