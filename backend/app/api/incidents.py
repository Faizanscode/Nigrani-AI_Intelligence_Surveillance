from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from backend.app.services.event_engine import get_incident_repo
from backend.app.core.event_bus import event_bus

router = APIRouter()

class UpdateIncidentStatus(BaseModel):
    status: str

@router.get("/", response_model=List[dict])
def list_incidents(
    skip: int = 0, 
    limit: int = 50, 
    status: Optional[str] = None,
    repo = Depends(get_incident_repo)
):
    filters = {}
    if status:
        filters["status"] = status
    
    incidents = repo.list(skip=skip, limit=limit, **filters)
    return [inc.model_dump() for inc in incidents]

@router.get("/{incident_id}", response_model=dict)
def get_incident(incident_id: str, repo = Depends(get_incident_repo)):
    inc = repo.get(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc.model_dump()

@router.patch("/{incident_id}/status", response_model=dict)
def update_incident_status(
    incident_id: str, 
    update_data: UpdateIncidentStatus, 
    repo = Depends(get_incident_repo)
):
    inc = repo.get(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    inc.status = update_data.status
    repo.update(inc)
    event_bus.publish("alerts.incident_update", inc.model_dump())
    return inc.model_dump()
