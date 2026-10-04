import pytest
import time
from ai_engine.analytics.fence.models import VirtualFence
from ai_engine.analytics.fence.engine import FenceEngine
from ai_engine.tracking.models import TrackResult
from ai_engine.detection.models import BoundingBox
from backend.app.core.config import settings

def test_fence_validation():
    with pytest.raises(ValueError):
        VirtualFence(fence_id="f1", camera_id="c1", name="n1", polygon=[(0, 0), (1, 1)])
        
    f = VirtualFence(fence_id="f1", camera_id="c1", name="n1", polygon=[(0, 0), (10, 0), (10, 10), (0, 10)])
    assert len(f.polygon) == 4

def _create_track(track_id: int, x: int, y: int) -> TrackResult:
    # Since we use bottom_center for fence point by default:
    # bbox.center_x = x, bbox.y2 = y
    bbox = BoundingBox(
        x1=x-5, y1=y-10, x2=x+5, y2=y, 
        center_x=x, center_y=y-5, width=10, height=10,
        confidence=0.9, class_name="car"
    )
    return TrackResult(
        track_id=track_id, 
        bbox=bbox, 
        confidence=0.9, 
        class_name="car", 
        class_id=0,
        frames_seen=1,
        trajectory=[(x, y)]
    )

def test_fence_engine_temporal_confirmation():
    # Save original settings
    original_frames = settings.INTRUSION_CONFIRMATION_FRAMES
    settings.INTRUSION_CONFIRMATION_FRAMES = 2
    
    engine = FenceEngine(camera_id="cam_001")
    poly = [(100, 100), (200, 100), (200, 200), (100, 200)]
    fence = VirtualFence(fence_id="f1", camera_id="cam_001", name="zone", polygon=poly)
    engine.add_fence(fence)
    
    # 1. OUTSIDE
    t1 = _create_track(1, 50, 50)
    events = engine.evaluate([t1], timestamp=1.0)
    assert len(events) == 0
    assert engine.track_states[("f1", 1)]["status"] == "OUTSIDE"
    assert engine.track_states[("f1", 1)]["inside_frames"] == 0
    
    # 2. INSIDE (Frame 1) - Should not trigger yet due to confirmation
    t1_inside = _create_track(1, 150, 150)
    events = engine.evaluate([t1_inside], timestamp=2.0)
    assert len(events) == 0
    assert engine.track_states[("f1", 1)]["status"] == "OUTSIDE"
    assert engine.track_states[("f1", 1)]["inside_frames"] == 1
    
    # 3. INSIDE (Frame 2) - Confirmation met, should trigger
    events = engine.evaluate([t1_inside], timestamp=3.0)
    assert len(events) == 1
    assert events[0].event_type == "VIRTUAL_FENCE_INTRUSION"
    assert engine.track_states[("f1", 1)]["status"] == "INSIDE"
    
    # Restore settings
    settings.INTRUSION_CONFIRMATION_FRAMES = original_frames

def test_duplicate_suppression_and_cooldown():
    # Save original settings
    original_cooldown = settings.INTRUSION_COOLDOWN
    original_frames = settings.INTRUSION_CONFIRMATION_FRAMES
    settings.INTRUSION_COOLDOWN = 60
    settings.INTRUSION_CONFIRMATION_FRAMES = 1
    
    engine = FenceEngine(camera_id="cam_001")
    poly = [(100, 100), (200, 100), (200, 200), (100, 200)]
    fence = VirtualFence(fence_id="f1", camera_id="cam_001", name="zone", polygon=poly)
    engine.add_fence(fence)
    
    # Enters
    t1 = _create_track(1, 150, 150)
    events = engine.evaluate([t1], timestamp=1.0)
    assert len(events) == 1
    
    # Stays inside -> no duplicate
    events = engine.evaluate([t1], timestamp=2.0)
    assert len(events) == 0
    
    # Leaves
    t1_outside = _create_track(1, 50, 50)
    events = engine.evaluate([t1_outside], timestamp=3.0)
    assert len(events) == 0
    
    # Enters again BEFORE cooldown expires -> no duplicate event
    events = engine.evaluate([t1], timestamp=4.0)
    assert len(events) == 0
    
    # Leaves again
    events = engine.evaluate([t1_outside], timestamp=60.0)
    assert len(events) == 0
    
    # Enters again AFTER cooldown expires -> new event
    events = engine.evaluate([t1], timestamp=65.0)
    assert len(events) == 1
    
    # Restore settings
    settings.INTRUSION_COOLDOWN = original_cooldown
    settings.INTRUSION_CONFIRMATION_FRAMES = original_frames

def test_boundary_hysteresis():
    original_tolerance = settings.FENCE_BOUNDARY_TOLERANCE
    original_frames = settings.INTRUSION_CONFIRMATION_FRAMES
    settings.FENCE_BOUNDARY_TOLERANCE = 5
    settings.INTRUSION_CONFIRMATION_FRAMES = 1
    
    engine = FenceEngine(camera_id="cam_001")
    # Top edge is y=100
    poly = [(100, 100), (200, 100), (200, 200), (100, 200)]
    f1 = VirtualFence(fence_id="f1", camera_id="cam_001", name="z1", polygon=poly)
    engine.add_fence(f1)
    
    # OUTSIDE
    engine.evaluate([_create_track(1, 150, 50)])
    assert engine.track_states[("f1", 1)]["status"] == "OUTSIDE"
    
    # On Boundary (dist = 0). Should retain OUTSIDE state because dist <= 5
    engine.evaluate([_create_track(1, 150, 100)])
    assert engine.track_states[("f1", 1)]["status"] == "OUTSIDE"
    
    # Deep INSIDE (dist = 50). Triggers INSIDE state
    events = engine.evaluate([_create_track(1, 150, 150)], timestamp=3.0)
    assert len(events) == 1
    assert engine.track_states[("f1", 1)]["status"] == "INSIDE"
    
    # On Boundary (exiting) (dist = 0). Should retain INSIDE state because dist >= -5
    engine.evaluate([_create_track(1, 150, 100)], timestamp=4.0)
    assert engine.track_states[("f1", 1)]["status"] == "INSIDE"
    
    # Deep OUTSIDE (dist = -50). Triggers OUTSIDE state
    engine.evaluate([_create_track(1, 150, 50)], timestamp=5.0)
    assert engine.track_states[("f1", 1)]["status"] == "OUTSIDE"
    
    settings.FENCE_BOUNDARY_TOLERANCE = original_tolerance
    settings.INTRUSION_CONFIRMATION_FRAMES = original_frames

def test_multiple_cameras_and_fences():
    original_frames = settings.INTRUSION_CONFIRMATION_FRAMES
    settings.INTRUSION_CONFIRMATION_FRAMES = 1
    
    engine1 = FenceEngine(camera_id="cam_1")
    engine2 = FenceEngine(camera_id="cam_2")
    
    f1 = VirtualFence(fence_id="f1", camera_id="cam_1", name="z1", polygon=[(100, 100), (200, 100), (200, 200), (100, 200)])
    f2 = VirtualFence(fence_id="f2", camera_id="cam_2", name="z2", polygon=[(100, 100), (200, 100), (200, 200), (100, 200)])
    
    engine1.add_fence(f1)
    engine2.add_fence(f2)
    
    # Both tracks start outside
    engine1.evaluate([_create_track(1, 50, 50)])
    engine2.evaluate([_create_track(1, 50, 50)])
    
    # cam_1 track enters, cam_2 track stays out
    e1 = engine1.evaluate([_create_track(1, 150, 150)])
    e2 = engine2.evaluate([_create_track(1, 50, 50)])
    
    assert len(e1) == 1
    assert len(e2) == 0
    assert engine1.track_states[("f1", 1)]["status"] == "INSIDE"
    assert engine2.track_states[("f2", 1)]["status"] == "OUTSIDE"
    
    settings.INTRUSION_CONFIRMATION_FRAMES = original_frames
