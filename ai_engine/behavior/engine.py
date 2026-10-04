import time
from typing import List, Dict
from ai_engine.tracking.models import TrackResult
from ai_engine.behavior.models import BehaviorEvent, TrackState
from ai_engine.behavior.loitering_detector import LoiteringDetector
from ai_engine.behavior.night_movement_detector import NightMovementDetector

class BehaviorEngine:
    def __init__(self):
        self.loitering_detector = LoiteringDetector()
        self.night_movement_detector = NightMovementDetector()
        
        # State tracking: key is "{camera_id}_{track_id}"
        self.track_states: Dict[str, TrackState] = {}
        self.cleanup_threshold = 10.0 # Remove state if unseen for 10s

    def evaluate(self, camera_id: str, tracks: List[TrackResult], current_time: float) -> List[BehaviorEvent]:
        events = []
        active_state_keys = set()
        
        for track in tracks:
            state_key = f"{camera_id}_{track.track_id}"
            active_state_keys.add(state_key)
            
            # Use bottom center for position to match typical ground plane
            # bbox is x1, y1, x2, y2
            # BoundingBox model is x1, y1, x2, y2
            bb = track.bbox
            pos = ((bb.x1 + bb.x2) / 2.0, bb.y2)
            
            if state_key not in self.track_states:
                self.track_states[state_key] = TrackState(track.track_id, track.class_name, current_time, pos)
            else:
                self.track_states[state_key].update(current_time, pos)
                
            state = self.track_states[state_key]
            
            # Run Loitering Detection
            loitering_event = self.loitering_detector.evaluate(camera_id, current_time, track, state)
            if loitering_event:
                events.append(loitering_event)
                
            # Run Night Movement Detection
            night_event = self.night_movement_detector.evaluate(camera_id, current_time, track, state)
            if night_event:
                events.append(night_event)
                
        # Cleanup stale tracks
        stale_keys = []
        for k, v in self.track_states.items():
            # If tracking state belongs to this camera, but wasn't active
            # (We only cleanup current camera's stale tracks here to avoid cross-camera race conditions if engine is shared, 
            # though usually BehaviorEngine is 1 per CameraPipeline)
            if k.startswith(f"{camera_id}_") and k not in active_state_keys:
                if current_time - v.last_seen_time > self.cleanup_threshold:
                    stale_keys.append(k)
                    
        for k in stale_keys:
            del self.track_states[k]
            
        return events
