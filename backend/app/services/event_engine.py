import logging
import time
import os
import cv2
from typing import Dict, Any, Optional
import threading

from backend.app.core.config import settings
from backend.app.core.event_bus import event_bus
from backend.app.services.alert_manager import AlertManager
from backend.app.services.camera_manager import camera_manager
from backend.app.repositories.interfaces import IEventRepository
from ai_engine.analytics.fence.models import IntrusionEvent
from backend.app.services.correlation_engine import MultiCameraCorrelationEngine

logger = logging.getLogger("EventEngine")
class EventEngine:
    def __init__(self, event_repo: IEventRepository, alert_manager: AlertManager, correlation_engine: MultiCameraCorrelationEngine):
        self.repo = event_repo
        self.alert_manager = alert_manager
        self.correlation_engine = correlation_engine
        self.settings = settings
        
        # Deduplication cache
        # Key: f"{camera_id}_{fence_id}_{track_id}_{event_type}"
        # Value: float timestamp
        self._last_event_times: Dict[str, float] = {}
        self._lock = threading.Lock()
        
        # Register to the event bus
        event_bus.subscribe("events.intrusion", self.process_event_bus)
        event_bus.subscribe("events.behavior", self.process_event_bus)
        event_bus.subscribe("events.face_recognition", self.process_event_bus_dict)
        
    async def process_event_bus(self, event: Any):
        """Process an incoming event asynchronously from the Event Bus."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._process_event, event)
        except Exception as e:
            logger.error(f"Failed to process intrusion event: {e}")

    async def process_event_bus_dict(self, event_dict: dict):
        """Process an incoming dict event (like ANPR or Face Recognition) asynchronously."""
        import asyncio
        try:
            from types import SimpleNamespace
            event = SimpleNamespace(**event_dict)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._process_event, event)
        except Exception as e:
            logger.error(f"Failed to process dict event: {e}")

    def _process_event(self, event: Any) -> Optional[Any]:
        """
        Validate, deduplicate, store the event, and generate an alert.
        """
        if not hasattr(event, "event_id") or not hasattr(event, "event_type"):
            logger.warning("Received malformed event without event_id or event_type.")
            return None

        camera_id = getattr(event, "camera_id", "unknown")
        fence_id = getattr(event, "fence_id", "unknown")
        track_id = getattr(event, "track_id", "unknown")
        event_type = event.event_type

        # 1. Deduplication and Cooldown check
        if event_type == "FACE_RECOGNITION":
            face_name = getattr(event, "name", "unknown")
            dedup_key = f"{camera_id}_FACE_{face_name}"
        elif event_type == "VIRTUAL_FENCE_INTRUSION":
            # Prevent spam from same object type in same fence if tracking is lost
            obj_type = getattr(event, "object_class", getattr(event, "object_type", "unknown"))
            dedup_key = f"{camera_id}_FENCE_{fence_id}_{obj_type}"
        elif event_type == "LOITERING_DETECTED":
            dedup_key = f"{camera_id}_LOITERING_{track_id}"
        else:
            dedup_key = f"{camera_id}_{fence_id}_{track_id}_{event_type}"
            
        now = time.time()
        
        with self._lock:
            last_time = self._last_event_times.get(dedup_key, 0)
            if now - last_time < self.settings.ALERT_COOLDOWN_SECONDS:
                # Still in cooldown, reject duplicate event
                return None
                
            # Update last event time
            self._last_event_times[dedup_key] = now
            
            # Periodically clean up the cache (naive approach for prototype)
            if len(self._last_event_times) > 10000:
                # Remove items older than cooldown
                self._last_event_times = {
                    k: v for k, v in self._last_event_times.items() 
                    if now - v < self.settings.ALERT_COOLDOWN_SECONDS
                }

        # 2. Capture evidence snapshot for high-severity events
        snapshot_url = None
        if event_type in ["VIRTUAL_FENCE_INTRUSION", "LOITERING_DETECTED", "NIGHT_MOVEMENT_DETECTED", "FACE_RECOGNITION"]:
            frame = camera_manager.capture_snapshot(camera_id)
            if frame is not None:
                try:
                    filename = f"{event.event_id}.jpg"
                    filepath = os.path.join("data/evidence", filename)
                    cv2.imwrite(filepath, frame)
                    snapshot_url = f"/api/v1/evidence/{filename}"
                    
                    # Attach to event if possible
                    if hasattr(event, 'snapshot_url'):
                        event.snapshot_url = snapshot_url
                    elif isinstance(event, dict):
                        event['snapshot_url'] = snapshot_url
                    elif hasattr(event, '__dict__'):
                        setattr(event, 'snapshot_url', snapshot_url)
                except Exception as e:
                    logger.error(f"Failed to save snapshot for event {event.event_id}: {e}")

        # 3. Store event in repository
        import types
        if isinstance(event, types.SimpleNamespace):
            self.repo.add(vars(event))
        else:
            self.repo.add(event)
        logger.info(f"Processed valid event {event.event_id} ({event_type}) with evidence {snapshot_url}")

        # 4. Create Alert
        if event_type in ["VIRTUAL_FENCE_INTRUSION", "LOITERING_DETECTED", "NIGHT_MOVEMENT_DETECTED", "FACE_RECOGNITION"]:
            alert = self.alert_manager.create_alert(event, snapshot_url=snapshot_url)
            # Publish Alert internally for websockets, etc.
            if alert:
                event_bus.publish("alerts.new", alert)
                
        # 5. Process for cross-camera correlation
        try:
            self.correlation_engine.process_event(event)
        except Exception as e:
            logger.error(f"Correlation engine error: {e}")
        
        return event

    def clear_camera_state(self, camera_id: str):
        """Clear all dedup state for a camera. Call when a pipeline stops."""
        with self._lock:
            keys = [k for k in self._last_event_times if k.startswith(f"{camera_id}_")]
            for k in keys:
                del self._last_event_times[k]
        logger.info(f"Cleared dedup state for camera {camera_id} ({len(keys) if 'keys' in dir() else 0} entries)")

# We need global instances for the FastAPI DI to use easily
from backend.app.repositories.memory import InMemoryEventRepository, InMemoryAlertRepository, InMemoryIncidentRepository
from backend.app.services.correlation_engine import MultiCameraCorrelationEngine

# Initialize global repositories based on config limits
global_event_repo = InMemoryEventRepository(max_capacity=settings.MAX_IN_MEMORY_EVENTS)
global_alert_repo = InMemoryAlertRepository(max_capacity=settings.MAX_IN_MEMORY_ALERTS)
global_incident_repo = InMemoryIncidentRepository()

global_alert_manager = AlertManager(global_alert_repo)
global_correlation_engine = MultiCameraCorrelationEngine(global_incident_repo)
global_event_engine = EventEngine(global_event_repo, global_alert_manager, global_correlation_engine)

def get_event_repo():
    return global_event_repo

def get_alert_repo():
    return global_alert_repo

def get_alert_manager():
    return global_alert_manager

def get_event_engine():
    return global_event_engine

def get_incident_repo():
    return global_incident_repo
