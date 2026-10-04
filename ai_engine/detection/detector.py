from abc import ABC, abstractmethod
from typing import List
import numpy as np

from ai_engine.detection.models import DetectionResult

class BaseDetector(ABC):
    """
    Abstract interface for object detectors.
    Allows swapping YOLO with other models without breaking the pipeline.
    """
    
    @abstractmethod
    def load_model(self) -> bool:
        """Load the detection model into memory."""
        pass
        
    @abstractmethod
    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        Run inference on a single frame.
        
        Args:
            frame: A NumPy array representing the image (BGR).
            
        Returns:
            A list of DetectionResult objects.
        """
        pass
