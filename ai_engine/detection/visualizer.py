import cv2
import numpy as np
from typing import List
from ai_engine.detection.models import DetectionResult

class DetectionVisualizer:
    """
    Utility to draw bounding boxes and labels on frames.
    """
    
    @staticmethod
    def draw_detections(frame: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        """
        Draws bounding boxes and confidence labels on a copy of the frame.
        
        Args:
            frame: Original BGR image frame.
            detections: List of DetectionResult objects.
            
        Returns:
            A new annotated BGR image frame.
        """
        annotated = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2
            label = f"{det.class_name.upper()} {det.confidence:.2f}"
            
            # Determine color based on class
            if det.class_name == "person":
                color = (0, 255, 0) # Green for person
            else:
                color = (0, 165, 255) # Orange for vehicles
                
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - 20), (x1 + w, y1), color, -1)
            
            # Draw label text
            cv2.putText(annotated, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
        return annotated
