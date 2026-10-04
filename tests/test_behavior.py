import pytest
import time
from ai_engine.behavior.loitering_detector import LoiteringDetector
from ai_engine.behavior.night_movement_detector import NightMovementDetector
from ai_engine.behavior.engine import BehaviorEngine
from ai_engine.behavior.models import TrackState
from ai_engine.tracking.models import TrackResult
from ai_engine.detection.models import BoundingBox
from backend.app.core.config import settings

def make_track(track_id, class_name, x1, y1, x2, y2, frames=10):
    return TrackResult(
        track_id=track_id,
        class_id=0,
        class_name=class_name,
        confidence=0.9,
        bbox=BoundingBox(
            x1=x1, y1=y1, x2=x2, y2=y2,
            center_x=(x1+x2)//2, 
            center_y=(y1+y2)//2, 
            width=x2-x1, 
            height=y2-y1
        ),
        trajectory=[((x1+x2)/2.0, y2)],
        frames_seen=frames
    )

def test_loitering_detector():
    settings.LOITERING_ENABLED = True
    settings.LOITERING_TIME_THRESHOLD = 5
    settings.LOITERING_DISTANCE_THRESHOLD = 20
    
    detector = LoiteringDetector()
    detector.time_threshold = 5
    detector.distance_threshold = 20
    
    track = make_track(1, "person", 10, 10, 50, 100)
    state = TrackState(1, "person", 1000.0, (30.0, 100.0))
    
    # At 2s, no loitering
    evt = detector.evaluate("cam1", 1002.0, track, state)
    assert evt is None
    
    # Update state to 5s without moving
    state.update(1005.0, (30.0, 100.0))
    evt = detector.evaluate("cam1", 1005.0, track, state)
    assert evt is not None
    assert evt.event_type == "LOITERING_DETECTED"
    
    # Cooldown should prevent immediate re-trigger
    evt2 = detector.evaluate("cam1", 1006.0, track, state)
    assert evt2 is None

def test_night_movement_detector():
    settings.NIGHT_MOVEMENT_ENABLED = True
    settings.NIGHT_MOVEMENT_MODE = "AUTO"
    settings.NIGHT_START_TIME = "18:00"
    settings.NIGHT_END_TIME = "06:00"
    
    detector = NightMovementDetector()
    detector.min_distance = 10
    detector.min_duration = 2
    
    track = make_track(1, "car", 10, 10, 50, 100)
    state = TrackState(1, "car", 1000.0, (30.0, 100.0))
    
    # Mocking _is_night_time to return True for AUTO testing
    detector._is_night_time = lambda t: True
    
    # 3s duration, 5 distance -> no alert
    state.update(1003.0, (35.0, 100.0))
    assert detector.evaluate("cam1", 1003.0, track, state) is None
    
    # 3s duration, 15 distance -> alert
    state.update(1003.0, (50.0, 100.0))
    evt = detector.evaluate("cam1", 1003.0, track, state)
    assert evt is not None
    assert evt.event_type == "NIGHT_MOVEMENT_DETECTED"
    
    # Test OFF mode
    settings.NIGHT_MOVEMENT_MODE = "OFF"
    del state.cooldown_until["night_movement"]
    assert detector.evaluate("cam1", 1004.0, track, state) is None
    
    # Test ON mode (even if _is_night_time is False)
    settings.NIGHT_MOVEMENT_MODE = "ON"
    detector._is_night_time = lambda t: False
    evt_on = detector.evaluate("cam1", 1004.0, track, state)
    assert evt_on is not None
    assert evt_on.event_type == "NIGHT_MOVEMENT_DETECTED"
