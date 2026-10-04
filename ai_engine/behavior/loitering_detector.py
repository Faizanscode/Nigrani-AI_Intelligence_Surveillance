import time
import uuid
from typing import Dict, List, Optional
from ai_engine.tracking.models import TrackResult
from ai_engine.behavior.models import BehaviorEvent, TrackState
from backend.app.core.config import settings

class LoiteringDetector:
    def __init__(self):
        self.enabled = settings.LOITERING_ENABLED
        self.time_threshold = settings.LOITERING_TIME_THRESHOLD
        self.distance_threshold = settings.LOITERING_DISTANCE_THRESHOLD
        self.cooldown = settings.LOITERING_COOLDOWN

    def evaluate(self, camera_id: str, current_time: float, track: TrackResult, state: TrackState) -> Optional[BehaviorEvent]:
        if not self.enabled:
            return None
            
        # Only evaluate persons for loitering
        if track.class_name.lower() != "person":
            return None

        # Check if we are in cooldown for this track
        if "loitering" in state.cooldown_until:
            if current_time < state.cooldown_until["loitering"]:
                return None
            else:
                # Cooldown expired, we can potentially alert again. We should reset the "start time"
                # so we don't immediately alert again based on old time.
                state.first_seen_time = current_time
                state.first_seen_position = track.trajectory[-1]
                state.max_distance_from_start = 0.0
                del state.cooldown_until["loitering"]

        duration = state.duration()
        
        if duration >= self.time_threshold:
            if state.max_distance_from_start <= self.distance_threshold:
                # Loitering detected!
                state.loitering_event_emitted = True
                state.cooldown_until["loitering"] = current_time + self.cooldown
                
                return BehaviorEvent(
                    event_id=f"evt_loiter_{uuid.uuid4().hex[:8]}",
                    event_type="LOITERING_DETECTED",
                    camera_id=camera_id,
                    track_id=track.track_id,
                    object_type=track.class_name,
                    timestamp=current_time,
                    duration_seconds=duration,
                    movement_distance=state.max_distance_from_start,
                    severity="MEDIUM",
                    description=f"Person loitering detected for {int(duration)}s"
                )
                
        return None
