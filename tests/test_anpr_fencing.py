import pytest
import numpy as np
from ai_engine.anpr.engine import ANPREngine
from ai_engine.anpr.plate_validator import PlateValidator

def test_plate_validator_indian_patterns():
    v = PlateValidator()
    # Test valid Indian numbers
    assert v.validate(v.normalize("MP04TB1506")) == "VALID"
    assert v.validate(v.normalize("MP04CC1776")) == "VALID"
    assert v.validate(v.normalize("MH12DE1234")) == "VALID"
    assert v.validate(v.normalize("DL01CA1234")) == "VALID"
    
    # Test OCR confusion auto-correction (O -> 0, I -> 1 in digit slots)
    assert v.normalize("MPO4TB15O6") == "MP04TB1506"
    assert v.validate(v.normalize("MPO4TB15O6")) == "VALID"

def test_anpr_engine_filters_fence_intruders():
    engine = ANPREngine("test_cam")
    
    # Dummy frame (black image)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Two vehicle tracks: Track 101 (intruder) and Track 102 (outside fence)
    class DummyBBox:
        x1, y1, x2, y2 = 100, 100, 300, 300
        
    class DummyTrack:
        def __init__(self, tid, cls_name):
            self.track_id = tid
            self.class_name = cls_name
            self.bbox = DummyBBox()
            
    tracks = [
        DummyTrack(101, "car"),
        DummyTrack(102, "car")
    ]
    
    metadata = {"timestamp": 1000.0}
    
    # active_intruders only contains 101
    active_intruders = {101}
    
    # Track 102 must be skipped because it's not in active_intruders
    results = engine.process(frame, tracks, metadata, active_intruders=active_intruders)
    for r in results:
        assert r.vehicle_track_id == 101
        assert r.is_fence_intruder is True
