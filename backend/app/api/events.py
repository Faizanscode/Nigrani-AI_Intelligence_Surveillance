from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Any
from backend.app.services.event_engine import get_event_repo
from ai_engine.analytics.fence.models import IntrusionEvent

router = APIRouter(prefix="/api/v1/events", tags=["events"])

@router.get("", response_model=List[Any])
@router.get("/", response_model=List[Any], include_in_schema=False)
async def list_events(
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=1000),
    camera_id: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None
):
    repo = get_event_repo()
    filters = {}
    if camera_id: filters["camera_id"] = camera_id
    if event_type: filters["event_type"] = event_type
    if severity: filters["severity"] = severity
    
    events = repo.list(skip=skip, limit=limit, **filters)
    return events

@router.get("/{event_id}", response_model=Any)
async def get_event(event_id: str):
    repo = get_event_repo()
    event = repo.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.get("/statistics/count")
async def get_event_statistics(
    camera_id: Optional[str] = None,
    event_type: Optional[str] = None
):
    repo = get_event_repo()
    filters = {}
    if camera_id: filters["camera_id"] = camera_id
    if event_type: filters["event_type"] = event_type
    
    total = repo.get_total_count(**filters)
    return {"total": total}
