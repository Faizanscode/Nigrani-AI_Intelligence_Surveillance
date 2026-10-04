import time
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from ai_engine.tracking.models import TrackResult
from ai_engine.behavior.models import BehaviorEvent, TrackState
from backend.app.core.config import settings

class NightMovementDetector:
    def __init__(self):
        self.enabled = settings.NIGHT_MOVEMENT_ENABLED
        self.start_time = settings.NIGHT_START_TIME  # "18:00"
        self.end_time = settings.NIGHT_END_TIME      # "06:00"
        self.min_distance = settings.NIGHT_MOVEMENT_MIN_DISTANCE
        self.min_duration = settings.NIGHT_MOVEMENT_MIN_DURATION
        self.cooldown = settings.NIGHT_MOVEMENT_COOLDOWN
        
    def _is_night_time(self, current_time: float) -> bool:
        dt = datetime.fromtimestamp(current_time)
        current_minutes = dt.hour * 60 + dt.minute
        
        try:
            sh, sm = map(int, self.start_time.split(':'))
            eh, em = map(int, self.end_time.split(':'))
        except ValueError:
            return False
            
        start_minutes = sh * 60 + sm
        end_minutes = eh * 60 + em
        
        if start_minutes < end_minutes:
            return start_minutes <= current_minutes <= end_minutes
        else:
            # Over midnight (e.g. 18:00 to 06:00)
            return current_minutes >= start_minutes or current_minutes <= end_minutes

    def evaluate(self, camera_id: str, current_time: float, track: TrackResult, state: TrackState) -> Optional[BehaviorEvent]:
        if not self.enabled:
            return None
            
        mode = getattr(settings, "NIGHT_MOVEMENT_MODE", "AUTO")
        if mode == "OFF":
            return None
            
        is_night = self._is_night_time(current_time)
        if mode == "AUTO" and not is_night:
            return None

        # Check if we are in cooldown for this track
        if "night_movement" in state.cooldown_until:
            if current_time < state.cooldown_until["night_movement"]:
                return None
            else:
                del state.cooldown_until["night_movement"]

        duration = state.duration()
        
        # We need significant movement to trigger
        if duration >= self.min_duration and state.max_distance_from_start >= self.min_distance:
            state.night_movement_event_emitted = True
            state.cooldown_until["night_movement"] = current_time + self.cooldown
            
            return BehaviorEvent(
                event_id=f"evt_night_{uuid.uuid4().hex[:8]}",
                event_type="NIGHT_MOVEMENT_DETECTED",
                camera_id=camera_id,
                track_id=track.track_id,
                object_type=track.class_name,
                timestamp=current_time,
                duration_seconds=duration,
                movement_distance=state.max_distance_from_start,
                severity="MEDIUM",
                description=f"Night movement detected: {track.class_name}"
            )
            
        return None
