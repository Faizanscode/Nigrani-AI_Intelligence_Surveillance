from pydantic import BaseModel, Field, validator
from typing import List, Tuple, Optional


class VirtualFence(BaseModel):
    """Absolute-pixel fence used by the detection engine at runtime."""
    fence_id: str
    camera_id: str
    name: str
    description: Optional[str] = ""
    polygon: List[Tuple[int, int]]
    enabled: bool = True
    target_classes: List[str] = ["person", "car", "motorcycle", "bus", "truck"]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @validator('polygon')
    def validate_polygon(cls, v):
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 points")
        return v


class NormalizedFence(BaseModel):
    """
    Fence with normalized coordinates (0.0–1.0).
    This is what gets persisted to disk and sent to/from the frontend.
    """
    camera_id: str
    name: str = "Custom Fence"
    description: Optional[str] = ""
    # Each point is [x, y] with values between 0.0 and 1.0
    points: List[List[float]]
    enabled: bool = True
    target_classes: List[str] = ["person", "car", "motorcycle", "bus", "truck"]

    @validator('points')
    def validate_points(cls, v):
        if len(v) < 3:
            raise ValueError("Fence must have at least 3 points")
        for pt in v:
            if len(pt) != 2:
                raise ValueError("Each point must have exactly 2 coordinates [x, y]")
            if not (0.0 <= pt[0] <= 1.0 and 0.0 <= pt[1] <= 1.0):
                raise ValueError(f"Coordinates must be between 0.0 and 1.0, got {pt}")
        return v

    def to_absolute(self, width: int, height: int) -> List[Tuple[int, int]]:
        """Convert normalized points to absolute pixel coordinates."""
        return [(int(pt[0] * width), int(pt[1] * height)) for pt in self.points]


class IntrusionEvent(BaseModel):
    event_id: str
    event_type: str = "VIRTUAL_FENCE_INTRUSION"
    camera_id: str
    fence_id: str
    track_id: int
    object_class: str
    confidence: float
    timestamp: float
    position: dict  # {"x": int, "y": int}
    bounding_box: dict  # {"x1": int, "y1": int, "x2": int, "y2": int}
    direction: str = "ENTRY"
    severity: str = "HIGH"
    status: str = "NEW"
    snapshot_url: Optional[str] = None
