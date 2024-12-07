#!/bin/bash

# 安装必要的打包工具
sudo apt-get update
sudo apt-get install -y python3-stdeb dh-python debhelper

# 创建必要的目录
mkdir -p /usr/lib/LocalMediaSearch
mkdir -p /usr/share/applications

# 构建项目
python3 setup.py build

# 复制桌面文件
cp debian/LocalMediaSearch.desktop /usr/share/applications/

# 构建deb包
dpkg-buildpackage -b -us -uc

# 清理构建文件
python3 setup.py clean 