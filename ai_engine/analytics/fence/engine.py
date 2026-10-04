import cv2
import numpy as np
import uuid
import time
from typing import List, Dict, Tuple, Optional

from backend.app.core.config import settings
from backend.app.core.logger import get_logger
from ai_engine.tracking.models import TrackResult
from ai_engine.analytics.fence.models import VirtualFence, IntrusionEvent

logger = get_logger("FenceEngine")

class FenceEngine:
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        # fence_id -> VirtualFence
        self.fences: Dict[str, VirtualFence] = {}
        # (fence_id, track_id) -> dict of state info
        self.track_states: Dict[Tuple[str, int], Dict[str, Any]] = {}
        
    def add_fence(self, fence: VirtualFence):
        if fence.camera_id != self.camera_id:
            logger.warning(f"Attempted to add fence {fence.fence_id} belonging to {fence.camera_id} to engine for {self.camera_id}")
            return
        self.fences[fence.fence_id] = fence
        
    def remove_fence(self, fence_id: str):
        if fence_id in self.fences:
            del self.fences[fence_id]
            # Clean up states related to this fence
            keys_to_delete = [k for k in self.track_states if k[0] == fence_id]
            for k in keys_to_delete:
                del self.track_states[k]
                
    def get_fences(self) -> List[VirtualFence]:
        return list(self.fences.values())
        
    def _get_evaluation_point(self, track: TrackResult) -> Tuple[int, int]:
        """Returns the point to evaluate for the given track."""
        if settings.FENCE_POINT_STRATEGY == "bottom_center":
            return (track.bbox.center_x, track.bbox.y2)
        else:
            # Fallback to center
            return (track.bbox.center_x, track.bbox.center_y)

    def evaluate(self, tracks: List[TrackResult], timestamp: Optional[float] = None) -> List[IntrusionEvent]:
        """
        Evaluate tracks against all configured fences and generate intrusion events.
        """
        if not settings.VIRTUAL_FENCE_ENABLED or not self.fences or not tracks:
            return []
            
        if timestamp is None:
            timestamp = time.time()
            
        events: List[IntrusionEvent] = []
        active_track_ids = {t.track_id for t in tracks}
        
        # Determine monitored classes from settings
        monitored_classes = [c.strip().lower() for c in settings.FENCE_MONITORED_CLASSES.split(",")]
        
        for fence in self.fences.values():
            if not fence.enabled:
                continue
                
            poly = np.array(fence.polygon, np.int32)
            
            for track in tracks:
                # Use track classes from global settings if fence doesn't specify
                target_classes = fence.target_classes if fence.target_classes else monitored_classes
                if track.class_name.lower() not in [c.lower() for c in target_classes]:
                    continue
                    
                pt = self._get_evaluation_point(track)
                # measureDist=True returns distance to the closest boundary edge (negative outside, positive inside)
                dist = cv2.pointPolygonTest(poly, pt, measureDist=True)
                
                state_key = (fence.fence_id, track.track_id)
                if state_key not in self.track_states:
                    self.track_states[state_key] = {
                        "status": "OUTSIDE",
                        "inside_frames": 0,
                        "last_alert_time": 0.0
                    }
                
                state_info = self.track_states[state_key]
                current_status = state_info["status"]
                
                # Hysteresis Logic
                # Only change fundamental geometry state if strongly inside or outside
                if dist > settings.FENCE_BOUNDARY_TOLERANCE:
                    geom_state = "INSIDE"
                elif dist < -settings.FENCE_BOUNDARY_TOLERANCE:
                    geom_state = "OUTSIDE"
                else:
                    geom_state = "BOUNDARY"
                    
                new_status = current_status
                
                if geom_state == "INSIDE" or (geom_state == "BOUNDARY" and current_status == "INSIDE"):
                    state_info["inside_frames"] += 1
                elif geom_state == "OUTSIDE":
                    state_info["inside_frames"] = 0
                    new_status = "OUTSIDE"
                
                # Temporal confirmation check
                if state_info["inside_frames"] >= settings.INTRUSION_CONFIRMATION_FRAMES and current_status == "OUTSIDE":
                    # Check Cooldown
                    time_since_last_alert = timestamp - state_info["last_alert_time"]
                    if state_info["last_alert_time"] == 0.0 or time_since_last_alert >= settings.INTRUSION_COOLDOWN:
                        # Intrusion!
                        events.append(self._create_event(fence, track, timestamp, pt))
                        state_info["last_alert_time"] = timestamp
                    
                    new_status = "INSIDE"
                    
                # Handle TRIGGER_ON_INITIAL_INSIDE (legacy)
                elif current_status == "UNKNOWN" and geom_state == "INSIDE":
                    if settings.TRIGGER_ON_INITIAL_INSIDE:
                        events.append(self._create_event(fence, track, timestamp, pt))
                        state_info["last_alert_time"] = timestamp
                    new_status = "INSIDE"
                    
                state_info["status"] = new_status
                
        # Clean up stale tracks to avoid memory leak
        stale_keys = [k for k in self.track_states if k[1] not in active_track_ids]
        for k in stale_keys:
            del self.track_states[k]
            
        return events
        
    def _create_event(self, fence: VirtualFence, track: TrackResult, timestamp: float, pt: Tuple[int, int]) -> IntrusionEvent:
        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        
        return IntrusionEvent(
            event_id=event_id,
            camera_id=self.camera_id,
            fence_id=fence.fence_id,
            track_id=track.track_id,
            object_class=track.class_name,
            confidence=track.confidence,
            timestamp=timestamp,
            position={"x": pt[0], "y": pt[1]},
            bounding_box={
                "x1": track.bbox.x1,
                "y1": track.bbox.y1,
                "x2": track.bbox.x2,
                "y2": track.bbox.y2
            },
            direction="ENTRY",
            severity="HIGH",
            status="NEW"
        )

