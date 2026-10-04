import pytest
import time
from ai_engine.anpr.plate_validator import PlateValidator
from ai_engine.anpr.temporal_aggregator import TemporalAggregator
from backend.app.core.config import settings

def test_plate_validator():
    validator = PlateValidator()
    assert validator.normalize("cg 04 ab 1234") == "CG04AB1234"
    assert validator.validate("CG04AB1234") == "VALID"
    assert validator.validate("MH12DE1234") == "VALID"
    assert validator.validate("A") == "INVALID"
    assert validator.validate("TESTPLATE1") == "UNKNOWN" 

def test_temporal_aggregator():
    agg = TemporalAggregator(min_observations=3, cooldown_seconds=1.0)
    current_time = time.time()
    
    # Track 1 appears
    res = agg.add_observation(1, "CG04AB1234", 0.9, current_time)
    assert res is None # only 1 observation
    
    res = agg.add_observation(1, "CG04AB1234", 0.8, current_time + 0.1)
    assert res is None # 2
    
    res = agg.add_observation(1, "CG04AB1234", 0.85, current_time + 0.2)
    assert res is not None # 3!
    assert res["plate_text"] == "CG04AB1234"
    assert res["observations"] == 3
    
    # Cooldown prevents immediate re-trigger
    res2 = agg.add_observation(1, "CG04AB1234", 0.9, current_time + 0.3)
    assert res2 is None
    
    # After cooldown it triggers again
    res3 = agg.add_observation(1, "CG04AB1234", 0.9, current_time + 1.5)
    assert res3 is not None
    assert res3["observations"] == 5

    # Test expiry
    agg._cleanup(current_time + 100)
    assert 1 not in agg.track_history
