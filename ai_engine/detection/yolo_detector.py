import time
import numpy as np
from typing import List, Optional
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from ai_engine.detection.detector import BaseDetector
from ai_engine.detection.models import DetectionResult, BoundingBox
from backend.app.core.config import settings
from backend.app.core.logger import get_logger

logger = get_logger("YOLODetector")

# Global model cache to avoid re-loading PyTorch model weights on every camera start
_MODEL_CACHE = {}

class YOLODetector(BaseDetector):
    """
    Object detector implementation using Ultralytics YOLO.
    """
    def __init__(self):
        self.model_path = settings.YOLO_MODEL
        self.confidence = settings.YOLO_CONFIDENCE
        self.iou = settings.YOLO_IOU
        try:
            import torch
            if settings.YOLO_DEVICE == "cuda" and not torch.cuda.is_available():
                self.device = "cpu"
                logger.warning("CUDA requested but not available. Falling back to CPU.")
            else:
                self.device = settings.YOLO_DEVICE
        except ImportError:
            self.device = settings.YOLO_DEVICE
        
        # Parse targeted classes from config
        self.target_class_names = [c.strip().lower() for c in settings.DETECTION_CLASSES.split(",")]
        
        self.model = None
        self.class_names = {}
        self.target_class_ids = []
        
        # Performance metrics
        self.inference_count = 0
        self.total_inference_time = 0.0

    def load_model(self) -> bool:
        if YOLO is None:
            logger.error("Ultralytics library is not installed.")
            return False
            
        cache_key = (self.model_path, self.device)
        try:
            if cache_key in _MODEL_CACHE:
                logger.info(f"Reusing cached YOLO model '{self.model_path}' on device '{self.device}'")
                self.model = _MODEL_CACHE[cache_key]
            else:
                logger.info(f"Loading YOLO model '{self.model_path}' on device '{self.device}'...")
                self.model = YOLO(self.model_path)
                _MODEL_CACHE[cache_key] = self.model
            
            self.class_names = self.model.names
            
            # Map string class names from config to YOLO class IDs
            self.target_class_ids = []
            for cls_id, cls_name in self.class_names.items():
                if cls_name.lower() in self.target_class_names:
                    self.target_class_ids.append(cls_id)
            
            logger.info(f"Model ready. Targeted classes: {self.target_class_names} (IDs: {self.target_class_ids})")
            return True
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return False

    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        if self.model is None:
            logger.error("Model not loaded. Call load_model() first.")
            return []
            
        start_time = time.time()
        
        try:
            # Run inference
            # We pass classes=self.target_class_ids to let YOLO filter internally if supported,
            # but we will also filter manually just in case.
            results = self.model.predict(
                source=frame,
                conf=self.confidence,
                iou=self.iou,
                device=self.device,
                classes=self.target_class_ids if self.target_class_ids else None,
                verbose=False
            )
            
            detections = []
            
            # Parse results
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    
                    if cls_id not in self.target_class_ids:
                        continue
                        
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    width = x2 - x1
                    height = y2 - y1
                    center_x = x1 + width // 2
                    center_y = y1 + height // 2
                    
                    bbox = BoundingBox(
                        x1=x1, y1=y1, x2=x2, y2=y2,
                        center_x=center_x, center_y=center_y,
                        width=width, height=height
                    )
                    
                    cls_name = self.class_names.get(cls_id, str(cls_id))
                    
                    detection = DetectionResult(
                        class_id=cls_id,
                        class_name=cls_name,
                        confidence=conf,
                        bbox=bbox
                    )
                    detections.append(detection)
                    
            inference_time = time.time() - start_time
            self.inference_count += 1
            self.total_inference_time += inference_time
            
            return detections
            
        except Exception as e:
            logger.error(f"YOLO inference failed: {e}")
            return []
            
    def get_metrics(self):
        avg_time = self.total_inference_time / self.inference_count if self.inference_count > 0 else 0
        approx_fps = 1.0 / avg_time if avg_time > 0 else 0
        return {
            "inference_count": self.inference_count,
            "avg_inference_time_ms": round(avg_time * 1000, 2),
            "approx_fps": round(approx_fps, 2)
        }
