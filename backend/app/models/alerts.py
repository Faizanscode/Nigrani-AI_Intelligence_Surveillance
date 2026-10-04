from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
import uuid

class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: f"alert_{uuid.uuid4().hex[:12]}")
    event_id: str
    event_type: str
    camera_id: str
    severity: str
    status: str = "NEW"  # NEW, ACKNOWLEDGED, RESOLVED, DISMISSED
    message: str
    
    # Snapshot or evidence
    snapshot_url: Optional[str] = None
    
    # Metadata for specific event details (e.g. track_id, bounding_box)
    metadata: dict = Field(default_factory=dict)
    
    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    dismissed_at: Optional[str] = None
    
    acknowledged_by: Optional[str] = None
