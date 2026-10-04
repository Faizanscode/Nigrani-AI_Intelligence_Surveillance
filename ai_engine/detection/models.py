from pydantic import BaseModel
from typing import List, Dict, Optional

class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    center_x: int
    center_y: int
    width: int
    height: int

class DetectionResult(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
