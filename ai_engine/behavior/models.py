from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

class BehaviorEvent(BaseModel):
    event_id: str
    event_type: str
    camera_id: str
    track_id: int
    object_type: str
    timestamp: float
    duration_seconds: float
    movement_distance: float
    severity: str = "MEDIUM"
    description: str = ""
    snapshot_url: Optional[str] = None
    
class TrackState:
    def __init__(self, track_id: int, object_type: str, first_seen_time: float, first_seen_position: tuple):
        self.track_id = track_id
        self.object_type = object_type
        
        self.first_seen_time = first_seen_time
        self.last_seen_time = first_seen_time
        
        self.first_seen_position = first_seen_position
        self.last_seen_position = first_seen_position
        self.max_distance_from_start = 0.0
        
        # State tracking flags
        self.loitering_event_emitted = False
        self.night_movement_event_emitted = False
        self.cooldown_until: Dict[str, float] = {}

    def update(self, current_time: float, position: tuple):
        import math
        self.last_seen_time = current_time
        self.last_seen_position = position
        
        # Calculate Euclidean distance from start
        dx = position[0] - self.first_seen_position[0]
        dy = position[1] - self.first_seen_position[1]
        dist = math.hypot(dx, dy)
        if dist > self.max_distance_from_start:
            self.max_distance_from_start = dist
            
    def duration(self) -> float:
        return self.last_seen_time - self.first_seen_time
