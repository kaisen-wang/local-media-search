import torch
from PIL import Image
from transformers import ChineseCLIPProcessor, ChineseCLIPModel
from typing import Union, List
import numpy as np
import traceback
from src.config import MODEL_NAME, DEVICE, CACHE_DIR
import cv2
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing import image
import tensorflow as tf

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
            
            # 加载预训练模型，去掉最后的分类层
            self.model = ResNet50(weights='imagenet', include_top=False, pooling='avg')
            # 预热模型
            self._warmup_model()
            
        except Exception as e:
            print("\n=== Initialization Error ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            traceback.print_exc()
            print("===========================")
            raise

    def _warmup_model(self):
        """预热模型，避免第一次提取特征时的延迟"""
        dummy_input = np.zeros((1, 224, 224, 3))
        self.model.predict(dummy_input)

    def extract_image_features(self, image_path):
        """从图片文件提取特征"""
        try:
            # 加载并预处理图片
            img = image.load_img(image_path, target_size=(224, 224))
            x = image.img_to_array(img)
            x = np.expand_dims(x, axis=0)
            x = preprocess_input(x)
            
            # 直接使用模型预测获取特征
            features = self.model.predict(x, verbose=0)
            
            # 标准化特征向量
            features_normalized = features[0] / np.linalg.norm(features[0])
            return features_normalized
            
        except Exception as e:
            print(f"Error extracting features from image {image_path}: {str(e)}")
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

    def extract_frame_features(self, frame):
        """从视频帧提取特征"""
        try:
            # 调整帧大小
            frame = cv2.resize(frame, (224, 224))
            
            # OpenCV使用BGR格式，需要转换为RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 预处理帧
            x = image.img_to_array(frame)
            x = np.expand_dims(x, axis=0)
            x = preprocess_input(x)
            
            # 直接使用模型预测获取特征
            features = self.model.predict(x, verbose=0)
            
            # 标准化特征向量
            features_normalized = features[0] / np.linalg.norm(features[0])
            return features_normalized
            
        except Exception as e:
            print(f"Error extracting features from video frame: {str(e)}")
            return None

    def calculate_similarity(self, features1, features2):
        """计算两个特征向量之间的相似度"""
        # 使用余弦相似度
        return np.dot(features1, features2)  # 由于特征已经标准化，直接点积即可