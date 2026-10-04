from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.core.config import settings
from ai_engine.behavior.night_movement_detector import NightMovementDetector
import time

router = APIRouter(tags=["settings"])

class NightMovementMode(BaseModel):
    mode: str

@router.get("/settings/night-movement")
def get_night_movement():
    detector = NightMovementDetector()
    is_night = detector._is_night_time(time.time())
    mode = getattr(settings, "NIGHT_MOVEMENT_MODE", "AUTO")
    
    if mode == "ON":
        active = True
    elif mode == "OFF":
        active = False
    else:
        active = is_night
        
    return {
        "mode": mode,
        "active": active,
        "is_night": is_night
    }

@router.post("/settings/night-movement")
def update_night_movement(data: NightMovementMode):
    if data.mode not in ["AUTO", "ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be AUTO, ON, or OFF")
        
    settings.NIGHT_MOVEMENT_MODE = data.mode
    
    detector = NightMovementDetector()
    is_night = detector._is_night_time(time.time())
    
    if data.mode == "ON":
        active = True
    elif data.mode == "OFF":
        active = False
    else:
        active = is_night
        
    return {
        "mode": data.mode,
        "active": active,
        "is_night": is_night
    }
