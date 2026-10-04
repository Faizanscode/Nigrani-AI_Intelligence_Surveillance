from abc import ABC, abstractmethod
from typing import List
import numpy as np

from ai_engine.detection.models import DetectionResult
from ai_engine.tracking.models import TrackResult

class BaseTracker(ABC):
    """
    Abstract interface for object trackers.
    Consumes application-level DetectionResults and outputs TrackResults.
    """
    
    @abstractmethod
    def update(self, detections: List[DetectionResult], frame: np.ndarray) -> List[TrackResult]:
        """
        Update tracker with new detections from the current frame.
        
        Args:
            detections: List of DetectionResult objects from the current frame.
            frame: A NumPy array representing the image (BGR). Might be used by some trackers (like BoT-SORT).
            
        Returns:
            A list of TrackResult objects containing persistent IDs and history.
        """
        pass
