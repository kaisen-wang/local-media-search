from PIL import Image
from typing import Union, List
from src.config import MODEL_NAME, DEVICE, CACHE_DIR
from transformers import ChineseCLIPProcessor, ChineseCLIPModel
import cv2
import torch
import numpy as np
import logging

log = logging.getLogger(__name__)

class FeatureExtractor:
    """特征提取器"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            log.info("创建 FeatureExtractor 实例")
            cls._instance = super(FeatureExtractor, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self):
        try:
            log.info("正在初始化文本特征提取模型 ChineseCLIP...")
            log.info(f"模型: {MODEL_NAME}")
            log.info(f"Device: {DEVICE}")
            
            self.processor = ChineseCLIPProcessor.from_pretrained(
                MODEL_NAME,
                cache_dir=CACHE_DIR,
                local_files_only=True,
                image_mean=[0.48145466, 0.4578275, 0.40821073],
                image_std=[0.26862954, 0.26130258, 0.27577711]
            )
            
            self.model = ChineseCLIPModel.from_pretrained(
                MODEL_NAME,
                cache_dir=CACHE_DIR,
                local_files_only=True,
                torch_dtype=torch.float32
            ).to(DEVICE)
            
            self.model.eval()
            log.info("初始化完成")
            
        except Exception as e:
            log.exception("模型初始化失败")
            raise e

    def extract_image_features(self, image_path: str) -> np.ndarray:
        """使用ChineseCLIP从图片文件提取特征"""
        if not image_path:
            log.warning("图像路径为空")
            return None
        try:
            # 加载图片
            image = Image.open(image_path).convert('RGB')
            
            if not image:
                log.warning("无法加载图像 image_path:", image_path)
                return None

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
                image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            
            return image_features.cpu().numpy()[0]
            
        except Exception as e:
            log.exception("图像提取特征错误")
            raise e

    def extract_text_features(self, text: Union[str, List[str]]) -> np.ndarray:
        """从文本中提取特征向量"""
        try:
            log.info(f"Processing text: {text}")
            
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
                text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            
            return text_features.numpy()[0]
            
        except Exception as e:
            log.exception("文本提取特征错误")
            raise e

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
            log.exception("视频帧提取特征错误")
            raise e

    def calculate_similarity(features1: np.ndarray, features2: np.ndarray) -> float:
        """计算两个特征向量之间的相似度"""
        try:
            if features1 is None or features2 is None:
                return 0.0
            
            # 将numpy数组转换为torch张量，并移动到GPU
            features1_tensor = torch.tensor(features1, dtype=torch.float32).to(DEVICE)
            features2_tensor = torch.tensor(features2, dtype=torch.float32).to(DEVICE)
            
            # 确保向量已经归一化
            features1_norm = features1_tensor / features1_tensor.norm(dim=-1, keepdim=True)
            features2_norm = features2_tensor / features2_tensor.norm(dim=-1, keepdim=True)
            
            # 计算余弦相似度
            similarity = torch.dot(features1_norm, features2_norm)
            similarity = torch.clamp(similarity, -1.0, 1.0)  # 限制在 [-1, 1] 范围内
            similarity = (similarity + 1) / 2  # 转换到 [0, 1] 范围
            
            return float(similarity.cpu())
            
        except Exception as e:
            log.exception("计算两个特征向量之间的相似度错误")
            return 0.0
