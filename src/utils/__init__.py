import os
import time
import random
from src.config import MODEL_NAME

def check_model_files():
    """检查模型文件是否存在并完整"""
    required_files = ['config.json', 'pytorch_model.bin', 'clip_cn_vit-b-16.pt']
    
    if not os.path.exists(MODEL_NAME):
        raise FileNotFoundError(f"""
模型文件夹不存在！请按照以下步骤操作：

1. 创建目录：mkdir -p {MODEL_NAME}
2. 下载模型文件：
  https://huggingface.co/OFA-Sys/chinese-clip-vit-base-patch16
  （国内）https://hf-mirror.com/OFA-Sys/chinese-clip-vit-base-patch16
3. 将下载的文件放入 {MODEL_NAME} 目录

需要下载的文件：{', '.join(required_files)}
        """)
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(MODEL_NAME, file)):
            missing_files.append(file)
    
    if missing_files:
        raise FileNotFoundError(f"""
模型文件不完整！以下文件缺失：
{', '.join(missing_files)}

请从 https://huggingface.co/OFA-Sys/chinese-clip-vit-base-patch16 下载缺失的文件
并放入 {MODEL_NAME} 目录
        """) 

def delete_folder(folder_path: str):
    """删除文件夹"""
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                delete_folder(file_path)

def generate_id() -> int:
    """雪花算法生成ID"""
    # 获取当前时间戳（毫秒级）
    timestamp = int(time.time() * 1000)
    # 生成一个随机数
    random_number = random.randint(0, 4095)  # 12位随机数
    # 组合成唯一的ID
    unique_id = (timestamp << 12) | random_number
    return unique_id


