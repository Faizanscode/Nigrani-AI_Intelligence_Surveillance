import math
import time
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logger import get_logger
from backend.app.core.event_bus import event_bus
from backend.app.services.camera_manager import camera_manager
from backend.app.models.incidents import Incident, IncidentEvent

logger = get_logger("CorrelationEngine")

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Returns distance in meters
    R = 6371000 # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class MultiCameraCorrelationEngine:
    def __init__(self, incident_repo):
        self.repo = incident_repo
        self.settings = settings
        
    def _extract_fields(self, event: Any) -> Dict[str, Any]:
        """Normalize event fields for correlation."""
        if hasattr(event, "event_id"):
            eid = event.event_id
            cid = event.camera_id
            etype = event.event_type
            otype = getattr(event, "object_class", getattr(event, "object_type", None))
            ts = getattr(event, "timestamp", time.time())
            snap = getattr(event, "snapshot_url", None)
        else:
            eid = event.get("event_id")
            cid = event.get("camera_id")
            etype = event.get("event_type")
            otype = event.get("object_class", event.get("object_type"))
            ts = event.get("timestamp", time.time())
            snap = event.get("snapshot_url")
            
        return {
            "event_id": eid,
            "camera_id": cid,
            "event_type": etype,
            "object_type": otype,
            "timestamp": ts,
            "snapshot_url": snap
        }
        
    def process_event(self, event: Any) -> Optional[Incident]:
        if not self.settings.CORRELATION_ENABLED:
            return None
            
        fields = self._extract_fields(event)
        if not fields["event_id"] or not fields["camera_id"]:
            return None
            
        # Get active incidents
        active_incidents = self.repo.list(status="ACTIVE")
        
        best_incident = None
        best_score = 0
        best_reasons = []
        
        current_cam = camera_manager.get_camera_config(fields["camera_id"])
        
        for inc in active_incidents:
            # Prevent single camera spamming inside an incident
            if fields["event_id"] in inc.event_ids:
                continue
                
            score = 0
            reasons = []
            
            # Temporal Proximity
            time_diff = abs(fields["timestamp"] - inc.last_seen_at)
            if time_diff <= self.settings.CORRELATION_TIME_WINDOW_SECONDS:
                score += 30
                reasons.append(f"Occurred within {int(time_diff)}s of previous event")
            else:
                continue # Outside time window, cannot correlate
                
            # Camera Geographical Proximity
            primary_cam = camera_manager.get_camera_config(inc.primary_camera_id)
            if current_cam and primary_cam and current_cam.latitude and primary_cam.latitude:
                dist = haversine_distance(
                    current_cam.latitude, current_cam.longitude,
                    primary_cam.latitude, primary_cam.longitude
                )
                if dist <= self.settings.CORRELATION_CAMERA_DISTANCE_METERS:
                    score += 25
                    reasons.append(f"Cameras are geographically close ({int(dist)}m)")
            
            # Camera relationship/Same camera
            if inc.primary_camera_id != fields["camera_id"]:
                score += 10
                reasons.append("Multi-camera cross-correlation")
                
            # Object Type
            if fields["object_type"] and fields["object_type"] in inc.object_types:
                score += 20
                reasons.append(f"Matched object type: {fields['object_type']}")
                
            # Event Type relationship
            serious_events = ["VIRTUAL_FENCE_INTRUSION", "FACE_RECOGNITION", "ANPR", "NIGHT_MOVEMENT_DETECTED"]
            if fields["event_type"] in serious_events:
                score += 15
                reasons.append(f"High-severity event escalated: {fields['event_type']}")
                
            if score > best_score:
                best_score = score
                best_incident = inc
                best_reasons = reasons
                
        # Do we update or create?
        if best_incident and best_score >= self.settings.MIN_INCIDENT_CORRELATION_SCORE:
            logger.info(f"Correlating event {fields['event_id']} to INCIDENT {best_incident.id} (Score: {best_score})")
            
            # Update incident
            best_incident.last_seen_at = fields["timestamp"]
            best_incident.updated_at = time.time()
            if fields["camera_id"] not in best_incident.related_camera_ids and fields["camera_id"] != best_incident.primary_camera_id:
                best_incident.related_camera_ids.append(fields["camera_id"])
            if fields["object_type"] and fields["object_type"] not in best_incident.object_types:
                best_incident.object_types.append(fields["object_type"])
                
            best_incident.event_ids.append(fields["event_id"])
            
            if fields["snapshot_url"] and fields["snapshot_url"] not in best_incident.evidence_urls:
                best_incident.evidence_urls.append(fields["snapshot_url"])
                
            new_reasons = list(set(best_incident.correlation_reasons + best_reasons))
            best_incident.correlation_reasons = new_reasons
            best_incident.correlation_score = max(best_incident.correlation_score, best_score)
            
            evt = IncidentEvent(**fields)
            best_incident.timeline.append(evt)
            
            self.repo.update(best_incident)
            
            event_bus.publish("alerts.incident_update", best_incident.model_dump())
            return best_incident
            
        else:
            # Need to form a new incident?
            # We only create a new incident if this is a high-priority event
            # or if we want every event to be a potential incident seed.
            # Let's seed an incident if it's high severity.
            if fields["event_type"] in ["VIRTUAL_FENCE_INTRUSION", "FACE_RECOGNITION", "NIGHT_MOVEMENT_DETECTED", "ANPR"]:
                inc = Incident(
                    first_seen_at=fields["timestamp"],
                    last_seen_at=fields["timestamp"],
                    primary_camera_id=fields["camera_id"],
                    event_ids=[fields["event_id"]],
                    correlation_score=50, # Initial seed score
                    correlation_reasons=["Initial seed event"],
                    timeline=[IncidentEvent(**fields)]
                )
                if fields["object_type"]:
                    inc.object_types.append(fields["object_type"])
                if fields["snapshot_url"]:
                    inc.evidence_urls.append(fields["snapshot_url"])
                    
                self.repo.add(inc)
                logger.info(f"Created new INCIDENT {inc.id} seeded by {fields['event_id']}")
                event_bus.publish("alerts.incident_new", inc.model_dump())
                return inc
                
        return None
