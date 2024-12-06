import os
from pathlib import Path

def check_model_files():
    """检查模型文件是否存在并完整"""
    model_dir = os.getenv('MODEL_NAME')
    required_files = ['config.json', 'pytorch_model.bin', 'tokenizer.json', 'tokenizer_config.json', 'vocab.txt']
    
    if not os.path.exists(model_dir):
        raise FileNotFoundError(f"""
模型文件夹不存在！请按照以下步骤操作：

1. 创建目录：mkdir -p {model_dir}
2. 下载模型文件：
  https://huggingface.co/OFA-Sys/chinese-clip-vit-base-patch16
  （国内）https://hf-mirror.com/OFA-Sys/chinese-clip-vit-base-patch16
3. 将下载的文件放入 {model_dir} 目录

需要下载的文件：{', '.join(required_files)}
        """)
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(model_dir, file)):
            missing_files.append(file)
    
    if missing_files:
        raise FileNotFoundError(f"""
模型文件不完整！以下文件缺失：
{', '.join(missing_files)}

请从 https://huggingface.co/OFA-Sys/chinese-clip-vit-base-patch16 下载缺失的文件
并放入 {model_dir} 目录
        """) 