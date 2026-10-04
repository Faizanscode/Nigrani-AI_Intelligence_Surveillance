from pydantic import BaseModel
from typing import List, Optional

class ANPRRecord(BaseModel):
    id: str
    camera_id: str
    timestamp: float
    vehicle_track_id: int
    vehicle_class: str
    plate_bbox: List[int]
    raw_text: str
    plate_text: str
    ocr_confidence: float
    validation_status: str
    detection_confidence: float
    is_fence_intruder: bool = True
    fence_id: Optional[str] = None

