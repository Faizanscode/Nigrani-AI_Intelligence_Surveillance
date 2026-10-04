from fastapi import APIRouter
from backend.app.services.camera_manager import camera_manager

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    """System health check endpoint."""
    pipelines_running = sum(
        1 for cam in camera_manager.get_all_cameras()
        if camera_manager.get_camera_health(cam.id) and camera_manager.get_camera_health(cam.id)["is_running"]
    )
    
    return {
        "status": "healthy",
        "cameras_configured": len(camera_manager.get_all_cameras()),
        "pipelines_running": pipelines_running
    }
