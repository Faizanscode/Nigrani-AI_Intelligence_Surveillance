import pytest
import numpy as np
from ai_engine.detection.models import DetectionResult, BoundingBox
from ai_engine.tracking.bytetrack import ByteTrackTracker

def test_tracker_initialization():
    tracker = ByteTrackTracker("cam_1")
    assert tracker.camera_id == "cam_1"
    assert tracker.tracker is not None

def test_tracker_synthetic_association():
    tracker = ByteTrackTracker("cam_2")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Frame 1
    d1 = DetectionResult(
        class_id=0, class_name="person", confidence=0.9, 
        bbox=BoundingBox(x1=100, y1=100, x2=200, y2=300, center_x=150, center_y=200, width=100, height=200)
    )
    t1 = tracker.update([d1], frame)
    assert len(t1) == 1
    id1 = t1[0].track_id
    assert t1[0].class_name == "person"
    assert len(t1[0].trajectory) == 1
    
    # Frame 2 (slightly moved)
    d2 = DetectionResult(
        class_id=0, class_name="person", confidence=0.85, 
        bbox=BoundingBox(x1=110, y1=105, x2=210, y2=305, center_x=160, center_y=205, width=100, height=200)
    )
    t2 = tracker.update([d2], frame)
    assert len(t2) == 1
    assert t2[0].track_id == id1  # Should associate to the same track ID
    assert len(t2[0].trajectory) == 2
    
    # Frame 3 (New object appearing)
    d3 = DetectionResult(
        class_id=2, class_name="car", confidence=0.95, 
        bbox=BoundingBox(x1=400, y1=400, x2=500, y2=500, center_x=450, center_y=450, width=100, height=100)
    )
    t3 = tracker.update([d2, d3], frame)
    # At frame 3, the new car track is unconfirmed.
    # It must be seen in the next frame to become activated.
    
    # Frame 4
    t4 = tracker.update([d2, d3], frame)
    assert len(t4) == 2
    ids = {t.track_id for t in t4}
    assert id1 in ids
    assert len(ids) == 2

def test_tracker_isolation():
    tracker1 = ByteTrackTracker("cam_A")
    tracker2 = ByteTrackTracker("cam_B")
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    d = DetectionResult(
        class_id=0, class_name="person", confidence=0.9, 
        bbox=BoundingBox(x1=100, y1=100, x2=200, y2=300, center_x=150, center_y=200, width=100, height=200)
    )
    
    t1 = tracker1.update([d], frame)
    t2 = tracker2.update([d], frame)
    
    assert len(t1) == 1
    assert len(t2) == 1
    
    # Ultralytics BYTETracker uses a global ID counter (BaseTrack._count).
    # Hence, independent instances will assign different unique IDs.
    assert t1[0].track_id != t2[0].track_id

def test_empty_detections():
    tracker = ByteTrackTracker("cam_3")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    t = tracker.update([], frame)
    assert len(t) == 0
