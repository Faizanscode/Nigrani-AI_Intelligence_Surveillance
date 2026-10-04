from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from backend.app.core.config import settings
import uuid
import time

class PlateDetection(BaseModel):
    bbox: List[int]  # [x1, y1, x2, y2] relative to the original frame
    confidence: float

class OCRResult(BaseModel):
    raw_text: str
    normalized_text: str
    confidence: float
    characters: Optional[List[Dict[str, Any]]] = None

class ANPRResult(BaseModel):
    id: str
    camera_id: str
    timestamp: float
    vehicle_track_id: int
    vehicle_class: str
    plate_bbox: List[int]
    raw_text: str
    plate_text: str
    ocr_confidence: float
    validation_status: str  # VALID, INVALID, UNKNOWN
    detection_confidence: float
    is_fence_intruder: bool = True
    fence_id: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def create(cls, camera_id: str, track_id: int, vehicle_class: str, 
               bbox: List[int], ocr: OCRResult, validation: str, det_conf: float,
               is_fence_intruder: bool = True, fence_id: Optional[str] = None):
        return cls(
            id=str(uuid.uuid4()),
            camera_id=camera_id,
            timestamp=time.time(),
            vehicle_track_id=track_id,
            vehicle_class=vehicle_class,
            plate_bbox=bbox,
            raw_text=ocr.raw_text,
            plate_text=ocr.normalized_text,
            ocr_confidence=ocr.confidence,
            validation_status=validation,
            detection_confidence=det_conf,
            is_fence_intruder=is_fence_intruder,
            fence_id=fence_id
        )
