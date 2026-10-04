from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import time
import uuid

class IncidentEvent(BaseModel):
    event_id: str
    camera_id: str
    event_type: str
    object_type: Optional[str] = None
    timestamp: float
    snapshot_url: Optional[str] = None

class Incident(BaseModel):
    id: str = Field(default_factory=lambda: f"INC-{str(uuid.uuid4())[:8].upper()}")
    status: str = "ACTIVE" # ACTIVE, ACKNOWLEDGED, RESOLVED
    severity: str = "HIGH"
    correlation_score: int = 0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    first_seen_at: float
    last_seen_at: float
    primary_camera_id: str
    related_camera_ids: List[str] = []
    object_types: List[str] = []
    event_ids: List[str] = []
    evidence_urls: List[str] = []
    correlation_reasons: List[str] = []
    timeline: List[IncidentEvent] = []
