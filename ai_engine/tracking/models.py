from pydantic import BaseModel
from typing import List, Tuple, Optional
from ai_engine.detection.models import BoundingBox

class TrackResult(BaseModel):
    track_id: int
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
    trajectory: List[Tuple[int, int]]  # List of (center_x, center_y) tuples
    frames_seen: int
