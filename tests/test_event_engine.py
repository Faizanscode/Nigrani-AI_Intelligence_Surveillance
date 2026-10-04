import pytest
import asyncio
from backend.app.core.config import settings
from backend.app.core.event_bus import EventBus
from backend.app.services.alert_manager import AlertManager
from backend.app.services.event_engine import EventEngine
from backend.app.repositories.memory import InMemoryEventRepository, InMemoryAlertRepository
from ai_engine.analytics.fence.models import IntrusionEvent

@pytest.fixture
def test_bus():
    return EventBus()

@pytest.fixture
def repositories():
    event_repo = InMemoryEventRepository()
    alert_repo = InMemoryAlertRepository()
    return event_repo, alert_repo

@pytest.fixture
def alert_manager(repositories):
    _, alert_repo = repositories
    return AlertManager(alert_repo)

@pytest.fixture
def event_engine(repositories, alert_manager):
    event_repo, _ = repositories
    # We patch settings manually for tests
    engine = EventEngine(event_repo, alert_manager)
    engine.settings.ALERT_COOLDOWN_SECONDS = 0.5
    return engine

def _create_test_event(track_id=1) -> IntrusionEvent:
    return IntrusionEvent(
        event_id=f"evt_{track_id}",
        event_type="VIRTUAL_FENCE_INTRUSION",
        camera_id="cam_001",
        fence_id="fence_001",
        track_id=track_id,
        object_class="person",
        confidence=0.95,
        timestamp=1000.0,
        position={"x": 50, "y": 50},
        bounding_box={"x1": 40, "y1": 30, "x2": 60, "y2": 70},
        direction="ENTRY",
        severity="HIGH",
        status="NEW"
    )

def test_event_engine_processes_event(event_engine, repositories):
    event_repo, alert_repo = repositories
    event = _create_test_event()
    
    # Process event
    result = event_engine._process_event(event)
    
    assert result is not None
    assert event_repo.get_total_count() == 1
    assert alert_repo.get_total_count() == 1
    
    alert = alert_repo.list()[0]
    assert alert.event_id == event.event_id
    assert alert.severity == "HIGH"
    assert alert.status == "NEW"

def test_event_engine_deduplication(event_engine, repositories):
    event_repo, alert_repo = repositories
    event1 = _create_test_event(track_id=1)
    event2 = _create_test_event(track_id=1) # same track, camera, fence
    
    # Process first
    res1 = event_engine._process_event(event1)
    assert res1 is not None
    
    # Process second immediately (should be deduped)
    res2 = event_engine._process_event(event2)
    assert res2 is None
    
    assert event_repo.get_total_count() == 1
    assert alert_repo.get_total_count() == 1

def test_alert_lifecycle(alert_manager, repositories):
    event_repo, alert_repo = repositories
    event = _create_test_event()
    
    # Create Alert
    alert = alert_manager.create_alert(event)
    assert alert.status == "NEW"
    
    # Acknowledge
    ack_alert = alert_manager.acknowledge_alert(alert.alert_id, user_id="user_123")
    assert ack_alert.status == "ACKNOWLEDGED"
    assert ack_alert.acknowledged_by == "user_123"
    
    # Resolve
    res_alert = alert_manager.resolve_alert(alert.alert_id)
    assert res_alert.status == "RESOLVED"
    
    # Try to acknowledge resolved alert
    with pytest.raises(ValueError):
        alert_manager.acknowledge_alert(alert.alert_id)

def test_alert_dismiss(alert_manager, repositories):
    event_repo, alert_repo = repositories
    event = _create_test_event()
    
    alert = alert_manager.create_alert(event)
    
    # Dismiss
    dis_alert = alert_manager.dismiss_alert(alert.alert_id)
    assert dis_alert.status == "DISMISSED"

def test_repository_capacity():
    repo = InMemoryEventRepository(max_capacity=5)
    
    # Add 10 events
    for i in range(10):
        evt = _create_test_event(track_id=i)
        evt.event_id = f"e{i}"
        repo.add(evt)
        
    assert repo.get_total_count() == 5
    # The last 5 should be present (e5 to e9)
    assert repo.get("e9") is not None
    assert repo.get("e0") is None

def test_event_bus_integration(test_bus):
    received = []
    
    async def my_callback(msg):
        received.append(msg)
        
    async def run_test():
        test_bus.subscribe("test.topic", my_callback)
        test_bus.publish("test.topic", "hello")
        await asyncio.sleep(0.01)
        
    asyncio.run(run_test())
    
    assert len(received) == 1
    assert received[0] == "hello"
