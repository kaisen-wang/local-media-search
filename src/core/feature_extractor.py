import torch
from PIL import Image
from transformers import ChineseCLIPProcessor, ChineseCLIPModel
from typing import Union, List
import numpy as np
import traceback
from src.config import MODEL_NAME, DEVICE, CACHE_DIR

class FeatureExtractor:
    def __init__(self):
        try:
            print("=== Starting Feature Extractor Initialization ===")
            print(f"Model: {MODEL_NAME}")
            print(f"Device: {DEVICE}")
            
            # 加载处理器和模型
            print("Loading processor and model...")
            self.processor = ChineseCLIPProcessor.from_pretrained(
                MODEL_NAME,
                cache_dir=CACHE_DIR,
                local_files_only=True,
                trust_remote_code=True
            )
            
            self.model = ChineseCLIPModel.from_pretrained(
                MODEL_NAME,
                cache_dir=CACHE_DIR,
                trust_remote_code=True,
                local_files_only=True,
                torch_dtype=torch.float32
            )
            # 判断 DEVICE=cpu 将模型加载到 CPU； DEVICE=cuda 将模型加载到 GPU
            self.model = self.model.to(DEVICE)
            self.model.eval()
            print("Model and processor ready")
            
            print("=== Initialization Complete ===")
            
        except Exception as e:
            print("\n=== Initialization Error ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            traceback.print_exc()
            print("===========================")
            raise

    def extract_image_features(self, image_path: str) -> np.ndarray:
        """从图片中提取特征向量"""
        try:
            print(f"\nProcessing image: {image_path}")
            
            # 读取图片
            image = Image.open(image_path).convert('RGB')
            
            # 使用处理器处理图片
            inputs = self.processor(
                images=image,
                return_tensors="pt",
                padding=True
            )
            
            with torch.no_grad():
                # 提取图像特征
                image_features = self.model.get_image_features(**inputs)
                # 归一化
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.numpy()[0]
            
        except Exception as e:
            print("\n=== Image Processing Error ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            traceback.print_exc()
            print("============================")
            return None

    def extract_text_features(self, text: Union[str, List[str]]) -> np.ndarray:
        """从文本中提取特征向量"""
        try:
            print(f"\nProcessing text: {text}")
            
            if isinstance(text, str):
                text = [text]
            
            # 使用处理器处理文本
            inputs = self.processor(
                text=text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=77
            )
            
            with torch.no_grad():
                # 提取文本特征
                text_features = self.model.get_text_features(**inputs)
                # 归一化
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            print("Text features extracted successfully")
            return text_features.numpy()[0]
            
        except Exception as e:
            print("\n=== Text Processing Error ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"Input text: {text}")
            traceback.print_exc()
            print("===========================")
            return None

    def compute_similarity(self, feature1: np.ndarray, feature2: np.ndarray) -> float:
        """计算两个特征向量之间的相似度"""
        try:
            if feature1 is None or feature2 is None:
                print("One or both features are None")
                return 0.0
            
            # 确保向量已经归一化
            feature1_norm = feature1 / np.linalg.norm(feature1)
            feature2_norm = feature2 / np.linalg.norm(feature2)
            
            # 计算余弦相似度
            similarity = np.dot(feature1_norm, feature2_norm)
            similarity = max(-1.0, min(1.0, similarity))
            similarity = (similarity + 1) / 2
            
            return float(similarity)
            
        except Exception as e:
            print("\n=== Similarity Computation Error ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            traceback.print_exc()
            print("==================================")
            return 0.0