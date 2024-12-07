import os
import shutil
import subprocess
import sys

def clean_build():
    """清理构建目录"""
    print("Cleaning build directories...")
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Cleaned {dir_name}/")

def create_directories():
    """创建必要的目录"""
    print("Creating necessary directories...")
    dirs_to_create = ['logs']
    for dir_name in dirs_to_create:
        os.makedirs(dir_name, exist_ok=True)
        print(f"Created {dir_name}/")

def copy_resources():
    """复制资源文件"""
    print("Copying resource files...")
    # 复制配置文件
    if os.path.exists('config.ini'):
        shutil.copy2('config.ini', 'dist/')
    
    # 复制其他必要文件
    resources = [
        ('README.md', 'dist/'),
        ('LICENSE', 'dist/'),
    ]
    
    for src, dst in resources:
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {src} to {dst}")

def build_executable():
    """构建可执行文件"""
    print("Building executable...")
    try:
        subprocess.run([sys.executable, 'setup.py', 'build_exe'], check=True)
        print("Build successful!")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)

def create_launcher():
    """创建启动器脚本"""
    print("Creating launcher script...")
    launcher_script = """@echo off
echo Starting Image Text Search System...
start LocalMediaSearch.exe
"""
    
    with open('dist/start.bat', 'w') as f:
        f.write(launcher_script)

def main():
    """主打包流程"""
    print("=== Starting build process ===")
    
    # 1. 清理旧的构建文件
    clean_build()
    
    # 2. 创建必要的目录
    create_directories()
    
    # 3. 构建可执行文件
    build_executable()
    
    # 4. 复制资源文件
    copy_resources()
    
    # 5. 创建启动器
    create_launcher()
    
    print("\n=== Build completed successfully! ===")
    print("The executable can be found in the 'dist' directory.")
    print("Run 'start.bat' to launch the application.")

if __name__ == "__main__":
    main() 