import torch
from PIL import Image
from transformers import ChineseCLIPProcessor, ChineseCLIPModel
import cv2
import numpy as np
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing import image
from typing import Union, List, Tuple
import traceback
from src.config import MODEL_NAME, DEVICE, CACHE_DIR

class FeatureExtractor:
    def __init__(self):
        try:
            print("=== Starting Feature Extractor Initialization ===")
            
            # 初始化文本特征提取模型（ChineseCLIP）
            print(f"Initializing ChineseCLIP for text and image features...")
            print(f"Model: {MODEL_NAME}")
            print(f"Device: {DEVICE}")
            
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
            ).to(DEVICE)
            
            self.model.eval()
            print("=== Initialization Complete ===")
            
        except Exception as e:
            print("\n=== Initialization Error ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            traceback.print_exc()
            print("===========================")
            raise

    def extract_image_features(self, image_path: str) -> np.ndarray:
        """使用ChineseCLIP从图片文件提取特征"""
        try:
            # 加载图片
            image = Image.open(image_path).convert('RGB')
            
            # 使用processor处理图片
            inputs = self.processor(
                images=image,
                return_tensors="pt",
                padding=True
            ).to(DEVICE)
            
            # 提取特征
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # 归一化
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy()[0]
            
        except Exception as e:
            print(f"\n=== Image Processing Error ===")
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
            
            # 使用processor处理文本
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

    def extract_frame_features(self, frame: np.ndarray) -> np.ndarray:
        """从视频帧提取特征"""
        try:
            # 将OpenCV的BGR格式转换为RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 转换为PIL Image
            pil_image = Image.fromarray(frame_rgb)
            
            # 使用processor处理图片
            inputs = self.processor(
                images=pil_image,
                return_tensors="pt",
                padding=True
            ).to(DEVICE)
            
            # 提取特征
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # 归一化
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy()[0]
            
        except Exception as e:
            print(f"\n=== Frame Processing Error ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            traceback.print_exc()
            print("============================")
            return None

    def calculate_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """计算两个特征向量之间的相似度"""
        try:
            if features1 is None or features2 is None:
                return 0.0
            
            # 确保向量已经归一化
            features1_norm = features1 / np.linalg.norm(features1)
            features2_norm = features2 / np.linalg.norm(features2)
            
            # 计算余弦相似度
            similarity = np.dot(features1_norm, features2_norm)
            similarity = max(-1.0, min(1.0, similarity))  # 限制在 [-1, 1] 范围内
            similarity = (similarity + 1) / 2  # 转换到 [0, 1] 范围
            
            return float(similarity)
            
        except Exception as e:
            print("\n=== Similarity Computation Error ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            traceback.print_exc()
            print("==================================")
            return 0.0