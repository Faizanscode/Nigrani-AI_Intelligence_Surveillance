from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from backend.app.models.alerts import Alert
from backend.app.services.event_engine import get_alert_repo, get_alert_manager

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

@router.get("", response_model=List[Alert])
@router.get("/", response_model=List[Alert], include_in_schema=False)
async def list_alerts(
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=1000),
    camera_id: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None
):
    repo = get_alert_repo()
    filters = {}
    if camera_id: filters["camera_id"] = camera_id
    if status: filters["status"] = status
    if severity: filters["severity"] = severity
    
    alerts = repo.list(skip=skip, limit=limit, **filters)
    return alerts

@router.get("/{alert_id}", response_model=Alert)
async def get_alert(alert_id: str):
    repo = get_alert_repo()
    alert = repo.get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.patch("/{alert_id}/acknowledge", response_model=Alert)
async def acknowledge_alert(alert_id: str, user_id: Optional[str] = None):
    manager = get_alert_manager()
    try:
        alert = manager.acknowledge_alert(alert_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.patch("/{alert_id}/resolve", response_model=Alert)
async def resolve_alert(alert_id: str):
    manager = get_alert_manager()
    alert = manager.resolve_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.patch("/{alert_id}/dismiss", response_model=Alert)
async def dismiss_alert(alert_id: str):
    manager = get_alert_manager()
    alert = manager.dismiss_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert
