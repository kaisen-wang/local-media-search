# LocalMediaSearch - 本地媒体智能搜索工具

## 项目简介
LocalMediaSearch 是一个跨平台（Windows、macOS、Linux）的本地媒体搜索工具，支持通过文字（中文和英文）和图片搜索本地图片和视频文件。使用先进的机器学习模型进行图像识别和特征提取，让用户可以方便地管理和检索本地媒体文件。优先使用CPU进行计算，如果需要使用GPU，请确保CUDA可用。

## 主要功能
1. 文件索引
   - 自动扫描指定文件夹
   - 支持图片格式：JPG, PNG, GIF, WEBP，BMP，SVG，TIFF
   - 支持视频格式：MP4, AVI, MOV, MKV
   
2. 搜索功能
   - 文本搜索：通过关键词搜索图片和视频内容
   - 图片搜索：上传图片搜索相似内容
   - 组合搜索：支持文本+图片混合搜索
   
3. 智能识别
   - 图片场景识别
   - 物体检测
   - 文字识别（OCR）
   - 人脸检测

## 技术方案
- 使用 Python + Qt 开发跨平台桌面应用
- 后端采用 FastAPI 提供 RESTful API
- 使用 CLIP 模型进行图文特征提取
- 使用 Faiss 进行向量检索
- SQLite 存储文件索引和元数据

## 安装说明
1. 环境要求
   - Python 3.12+
   - CUDA 支持（可选，用于GPU加速）

2. 安装步骤
   ```bash
   # 克隆项目
   git clone https://gitee.com/kaisen-wang/local-media-search.git
   
   # 创建虚拟环境
   python -m venv venv
   
   # 进入虚拟环境
   source venv/bin/activate
   
   # 安装依赖
   pip install -r requirements.txt
   
   # 运行程序
   python main.py

   # 打包程序
   pip install pyinstaller
   pyinstaller -D -w -i resources/logo.ico -n LocalMediaSearch main.py
   or
   python build.py
   ```

## 使用指南
1. 首次运行
   - 点击"设置"配置需要索引的文件夹
   - 等待系统完成初始索引
   
2. 搜索操作
   - 文本搜索：直接在搜索框输入关键词
   - 图片搜索：点击图片图标上传参考图片
   - 查看搜索结果，支持预览和打开原文件位置

## 开发计划
- [X] v1.0: 基础搜索功能
- [X] v1.1: 添加视频帧提取和检索
- [X] v1.2: 优化搜索算法和用户界面
- [ ] v2.0: 添加更多高级特性

## CI/CD Pipeline
项目使用GitHub Actions进行持续集成和部署：
- 自动运行测试（Windows/macOS/Linux）
- 自动构建可执行文件
- 自动发布版本
- 自动部署文档

详细配置请查看 `pipeline.yml` 文件。

## 贡献指南
欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证
MIT License 

## 模型配置说明

### 模型下载与安装
1. 创建模型存储目录：
```bash
mkdir -p ./models
```

2. 下载模型文件：
   - 访问 [chinese-clip-vit-base-patch16](https://huggingface.co/OFA-Sys/chinese-clip-vit-base-patch16)
   - 下载所有模型文件到 `./models/chinese-clip-vit-base-patch16` 目录
   - 确保下载以下必要文件：
     - config.json
     - pytorch_model.bin
     - tokenizer.json
     - tokenizer_config.json
     - vocab.txt

3. 目录结构应如下：
```
./models/
└── chinese-clip-vit-base-patch16/
    ├── config.json
    ├── pytorch_model.bin
    ├── tokenizer.json
    ├── tokenizer_config.json
    └── vocab.txt
```

### 常见问题
如果遇到 "模型文件不存在" 错误，请检查：
1. 模型文件是否已正确下载
2. 文件路径是否正确
3. 文件名是否与配置匹配


# 安装说明

## Windows
1. 下载 LocalMediaSearch-Setup.exe
2. 双击运行安装程序
3. 按照向导完成安装

## macOS
1. 下载 LocalMediaSearch.dmg
2. 双击打开DMG文件
3. 将应用程序拖入Applications文件夹

## Debian/Ubuntu
1. 下载 localmediasearch_1.0.0_amd64.deb
2. 双击使用软件中心安装
   或使用命令行：
   ```bash
   sudo dpkg -i localmediasearch_1.0.0_amd64.deb
   sudo apt-get install -f  # 安装依赖
   ```
