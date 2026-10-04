from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.app.services.camera_manager import camera_manager, CameraConfig

router = APIRouter(prefix="/cameras", tags=["Cameras"])

class CameraCreate(BaseModel):
    name: str
    source: str
    type: str # 'file', 'webcam', 'rtsp'
    # Map Metadata
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    border_sector: Optional[str] = None
    border_state: Optional[str] = None
    border_region: Optional[str] = None
    bop_name: Optional[str] = None

@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]], include_in_schema=False)
def list_cameras():
    cameras = camera_manager.get_all_cameras()
    result = []
    for cam in cameras:
        status = "stopped"
        health = camera_manager.get_camera_health(cam.id)
        if health and health["is_running"]:
            status = "active"
        result.append({
            "id": cam.id,
            "name": cam.name,
            "source": cam.url,
            "type": cam.type,
            "status": status
        })
    return result

@router.post("")
@router.post("/", include_in_schema=False)
def add_camera(camera: CameraCreate):
    import uuid
    new_id = str(uuid.uuid4())
    config = CameraConfig(
        id=new_id, 
        name=camera.name, 
        type=camera.type, 
        url=camera.source,
        latitude=camera.latitude,
        longitude=camera.longitude,
        border_sector=camera.border_sector,
        border_state=camera.border_state,
        border_region=camera.border_region,
        bop_name=camera.bop_name
    )
    camera_manager.add_camera(config)
    return {"message": "Camera added", "id": new_id}

@router.delete("/{camera_id}")
def delete_camera(camera_id: str):
    if not camera_manager.get_camera_config(camera_id):
        raise HTTPException(status_code=404, detail="Camera not found")
    
    success = camera_manager.remove_camera(camera_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete camera")
    return {"message": "Camera deleted successfully"}

@router.get("/map", response_model=List[Dict[str, Any]])
def get_map_cameras(
    status: Optional[str] = None,
    border_sector: Optional[str] = None,
    border_state: Optional[str] = None,
    border_region: Optional[str] = None
):
    from backend.app.services.event_engine import global_alert_manager
    cameras = camera_manager.get_all_cameras()
    result = []
    
    for cam in cameras:
        # Determine Status
        cam_status = "OFFLINE"
        health = camera_manager.get_camera_health(cam.id)
        if health and health.get("is_running"):
            # Check for active alerts
            active_alerts = global_alert_manager.list_alerts(camera_id=cam.id, status="NEW", limit=1)
            if active_alerts:
                cam_status = "ACTIVE ALERT"
            else:
                cam_status = "ONLINE"
                
        # Apply filters
        if status and status.upper() != cam_status:
            continue
        if border_sector and cam.border_sector != border_sector:
            continue
        if border_state and cam.border_state != border_state:
            continue
        if border_region and cam.border_region != border_region:
            continue
            
        result.append({
            "id": cam.id,
            "name": cam.name,
            "type": cam.type,
            "url": cam.url,
            "latitude": cam.latitude,
            "longitude": cam.longitude,
            "border_sector": cam.border_sector,
            "border_state": cam.border_state,
            "border_region": cam.border_region,
            "bop_name": cam.bop_name,
            "status": cam_status
        })
        
    return result

@router.get("/{camera_id}")
def get_camera(camera_id: str):
    config = camera_manager.get_camera_config(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail="Camera not found")
    return config

@router.post("/{camera_id}/start")
def start_camera(camera_id: str):
    config = camera_manager.get_camera_config(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    success = camera_manager.start_camera(camera_id)
    if not success:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to start camera '{config.name}'. Unable to connect to source '{config.url}'. Please verify that the camera is plugged in, not used by another application, or check the file path."
        )
    return {"message": f"Camera {camera_id} started."}

@router.post("/{camera_id}/stop")
def stop_camera(camera_id: str):
    if not camera_manager.get_camera_config(camera_id):
        raise HTTPException(status_code=404, detail="Camera not found")
        
    camera_manager.stop_camera(camera_id)
    return {"message": f"Camera {camera_id} stopped."}

@router.delete("/{camera_id}")
def remove_camera(camera_id: str):
    success = camera_manager.remove_camera(camera_id)
    if not success:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"message": f"Camera {camera_id} removed."}

@router.get("/{camera_id}/status")
def get_camera_status(camera_id: str):
    if not camera_manager.get_camera_config(camera_id):
        raise HTTPException(status_code=404, detail="Camera not found")
        
    health = camera_manager.get_camera_health(camera_id)
    if not health:
        return {"status": "stopped"}
    return health

@router.get("/{camera_id}/detections")
def get_camera_detections(camera_id: str):
    if not camera_manager.get_camera_config(camera_id):
        raise HTTPException(status_code=404, detail="Camera not found")
        
    pipeline = camera_manager.pipelines.get(camera_id)
    if not pipeline or not pipeline.is_running or not pipeline.detector:
        return {"detections": [], "tracks": [], "face_recognition": []}
        
    with pipeline._frame_lock:
        latest_metadata = pipeline.latest_metadata
            
    if latest_metadata:
        dets = [d.model_dump() if hasattr(d, 'model_dump') else d for d in latest_metadata.get("detections", [])]
        tracks = [t.model_dump() if hasattr(t, 'model_dump') else t for t in latest_metadata.get("tracks", [])]
        faces = latest_metadata.get("face_recognition", [])
        return {
            "timestamp": latest_metadata.get("timestamp"),
            "detections": dets,
            "tracks": tracks,
            "face_recognition": faces
        }
    return {"detections": [], "tracks": [], "face_recognition": []}

@router.get("/{camera_id}/tracks")
async def get_camera_tracks(camera_id: str):
    """
    Get the latest track results for a camera.
    """
    pipeline = camera_manager.pipelines.get(camera_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Camera not running")
        
    if not pipeline.tracker:
        raise HTTPException(status_code=400, detail="Tracker not configured")
        
    with pipeline._frame_lock:
        latest_metadata = pipeline.latest_metadata
            
    if latest_metadata and "tracks" in latest_metadata:
        tracks = [t.model_dump() if hasattr(t, 'model_dump') else t for t in latest_metadata["tracks"]]
        return {
            "timestamp": latest_metadata.get("timestamp"),
            "tracks": tracks
        }
    return {"tracks": []}

@router.get("/{camera_id}/stream")
async def stream_camera(camera_id: str):
    """
    Stream the latest annotated frames via MJPEG.
    """
    import asyncio
    import cv2
    import numpy as np
    from fastapi.responses import StreamingResponse

    pipeline = camera_manager.pipelines.get(camera_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Camera not running")

    async def frame_generator():
        # Placeholder frame when no data yet
        blank = np.zeros((360, 640, 3), dtype=np.uint8)
        cv2.putText(blank, "Loading stream...", (180, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)

        while pipeline.is_running:
            frame = pipeline.get_stream_frame()

            if frame is None:
                frame = blank

            ret, buffer = cv2.imencode(
                '.jpg', frame,
                [cv2.IMWRITE_JPEG_QUALITY, 80]
            )
            if ret:
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n'
                    + buffer.tobytes()
                    + b'\r\n'
                )
            # Stream at ~25 FPS
            await asyncio.sleep(0.04)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*",
        }
    )

