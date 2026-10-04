import logging
from typing import Optional, List
from datetime import datetime
from backend.app.models.alerts import Alert
from backend.app.repositories.interfaces import IAlertRepository

logger = logging.getLogger("AlertManager")

class AlertManager:
    def __init__(self, alert_repo: IAlertRepository):
        self.repo = alert_repo

    def create_alert(self, event, snapshot_url: Optional[str] = None) -> Optional[Alert]:
        """Generate an alert from a valid event."""
        
        # Build human readable message
        if event.event_type == "VIRTUAL_FENCE_INTRUSION":
            camera_id = event.camera_id
            object_class = getattr(event, "object_class", "Object")
            # You might map fence_id to a name, but for now we'll just use the ID or generic
            msg = f"{object_class.capitalize()} crossed restricted zone on camera {camera_id}."
        elif event.event_type == "LOITERING_DETECTED":
            camera_id = event.camera_id
            object_class = getattr(event, "object_type", "Object")
            duration = getattr(event, "duration_seconds", 0)
            msg = f"Loitering Detected: {object_class.capitalize()} on camera {camera_id} for {int(duration)}s."
        elif event.event_type == "NIGHT_MOVEMENT_DETECTED":
            camera_id = event.camera_id
            object_class = getattr(event, "object_type", "Object")
            msg = f"Night Movement Detected: {object_class.capitalize()} on camera {camera_id}."
        elif event.event_type == "FACE_RECOGNITION":
            camera_id = event.camera_id
            name = getattr(event, "name", "Unknown")
            status = getattr(event, "status", "UNKNOWN")
            if status == "RECOGNIZED":
                msg = f"Face Recognized: {name} detected on camera {camera_id}."
            else:
                msg = f"Unknown face detected on camera {camera_id}."
        else:
            msg = f"Security event '{event.event_type}' detected."

        metadata = {}
        if hasattr(event, "track_id"):
            metadata["track_id"] = event.track_id
        if hasattr(event, "fence_id"):
            metadata["fence_id"] = event.fence_id
        if hasattr(event, "bounding_box"):
            metadata["bounding_box"] = event.bounding_box

        # Determine Severity
        severity = getattr(event, "severity", "HIGH")
        if event.event_type == "FACE_RECOGNITION":
            status = getattr(event, "status", "UNKNOWN")
            severity = "LOW" if status == "RECOGNIZED" else "MEDIUM"

        alert = Alert(
            event_id=event.event_id,
            event_type=event.event_type,
            camera_id=event.camera_id,
            severity=severity,
            status="NEW",
            message=msg,
            metadata=metadata,
            snapshot_url=snapshot_url
        )

        self.repo.add(alert)
        logger.info(f"Created new alert: {alert.alert_id} for event {event.event_id}")
        
        from backend.app.core.event_bus import event_bus
        event_bus.publish("alerts.new", alert)
        return alert

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        return self.repo.get(alert_id)

    def list_alerts(self, skip: int = 0, limit: int = 100, **filters) -> List[Alert]:
        return self.repo.list(skip=skip, limit=limit, **filters)

    def acknowledge_alert(self, alert_id: str, user_id: Optional[str] = None) -> Optional[Alert]:
        alert = self.repo.get(alert_id)
        if not alert:
            return None
            
        if alert.status in ["RESOLVED", "DISMISSED"]:
            raise ValueError(f"Cannot acknowledge an alert with status {alert.status}")

        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_at = datetime.utcnow().isoformat()
        if user_id:
            alert.acknowledged_by = user_id
            
        self.repo.update(alert)
        logger.info(f"Alert {alert_id} acknowledged.")
        from backend.app.core.event_bus import event_bus
        event_bus.publish("alerts.updated", alert)
        return alert

    def resolve_alert(self, alert_id: str) -> Optional[Alert]:
        alert = self.repo.get(alert_id)
        if not alert:
            return None

        alert.status = "RESOLVED"
        alert.resolved_at = datetime.utcnow().isoformat()
        
        self.repo.update(alert)
        logger.info(f"Alert {alert_id} resolved.")
        from backend.app.core.event_bus import event_bus
        event_bus.publish("alerts.updated", alert)
        return alert

    def dismiss_alert(self, alert_id: str) -> Optional[Alert]:
        alert = self.repo.get(alert_id)
        if not alert:
            return None

        alert.status = "DISMISSED"
        alert.dismissed_at = datetime.utcnow().isoformat()
        
        self.repo.update(alert)
        logger.info(f"Alert {alert_id} dismissed.")
        from backend.app.core.event_bus import event_bus
        event_bus.publish("alerts.updated", alert)
        return alert
