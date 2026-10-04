from fastapi import APIRouter, Query
from typing import List, Optional
from backend.app.models.anpr import ANPRRecord

router = APIRouter(prefix="/anpr", tags=["ANPR"])

# In-memory storage for prototype
anpr_db = []

@router.get("", response_model=List[ANPRRecord])
def get_anpr_records(
    camera_id: Optional[str] = None,
    intruder_only: bool = Query(True, description="Filter only vehicles that intruded the virtual fence"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get recent ANPR records, optionally filtered by camera and fence intrusion status.
    """
    sorted_records = sorted(anpr_db, key=lambda x: x['timestamp'], reverse=True)

    if camera_id:
        sorted_records = [r for r in sorted_records if r.get('camera_id') == camera_id]

    if intruder_only:
        # Show plates that are from fence intruders (default true)
        # If record doesn't have the key, fallback to True for backwards compatibility
        sorted_records = [r for r in sorted_records if r.get('is_fence_intruder', True)]

    return sorted_records[:limit]

@router.delete("")
def clear_anpr_records():
    global anpr_db
    anpr_db.clear()
    return {"status": "cleared"}

def add_anpr_record(record: dict):
    # Only keep records if they have a plate text
    if not record.get("plate_text"):
        return
    anpr_db.append(record)
    if len(anpr_db) > 1000:
        anpr_db.pop(0)

from backend.app.core.event_bus import event_bus
async def on_anpr_event(msg):
    data = msg.model_dump() if hasattr(msg, "model_dump") else msg
    add_anpr_record(data)

event_bus.subscribe("events.anpr", on_anpr_event)

