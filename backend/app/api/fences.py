"""
Per-camera virtual fence API.
Endpoints follow the REST convention:
  GET    /api/v1/cameras/{camera_id}/fence  → get saved fence (or null)
  PUT    /api/v1/cameras/{camera_id}/fence  → save/replace fence
  DELETE /api/v1/cameras/{camera_id}/fence  → delete saved fence (revert to default)
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, validator

from backend.app.services.camera_manager import camera_manager
from backend.app.services.fence_store import fence_store
from ai_engine.analytics.fence.models import NormalizedFence, VirtualFence
from backend.app.core.logger import get_logger

logger = get_logger("FencesAPI")

router = APIRouter(prefix="/cameras", tags=["fences"])


class FenceSaveRequest(BaseModel):
    name: str = "Custom Fence"
    description: str = ""
    points: List[List[float]]            # [[x, y], ...] normalized 0.0–1.0
    enabled: bool = True
    target_classes: List[str] = ["person", "car", "motorcycle", "bus", "truck"]

    @validator("points")
    def validate_points(cls, v):
        if len(v) < 3:
            raise ValueError("A fence must have at least 3 points.")
        for pt in v:
            if len(pt) != 2:
                raise ValueError("Each point must have exactly 2 values [x, y].")
            if not (0.0 <= pt[0] <= 1.0 and 0.0 <= pt[1] <= 1.0):
                raise ValueError(f"Coordinates must be 0.0–1.0, got {pt}.")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# GET /cameras/{camera_id}/fence
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{camera_id}/fence")
async def get_fence(camera_id: str):
    """Return the saved normalized fence for a camera, or null if none saved."""
    # Camera must exist (running or not)
    if not camera_manager.get_camera_config(camera_id):
        raise HTTPException(status_code=404, detail="Camera not found")

    fence = fence_store.get(camera_id)
    if fence is None:
        return {"camera_id": camera_id, "fence": None, "is_default": True}

    return {"camera_id": camera_id, "fence": fence.model_dump(), "is_default": False}


# ─────────────────────────────────────────────────────────────────────────────
# PUT /cameras/{camera_id}/fence
# ─────────────────────────────────────────────────────────────────────────────
@router.put("/{camera_id}/fence")
async def save_fence(camera_id: str, request: FenceSaveRequest):
    """
    Save a custom normalized fence for a camera.
    If the camera pipeline is running, hot-swaps the fence immediately.
    """
    if not camera_manager.get_camera_config(camera_id):
        raise HTTPException(status_code=404, detail="Camera not found")

    normalized = NormalizedFence(
        camera_id=camera_id,
        name=request.name,
        description=request.description,
        points=request.points,
        enabled=request.enabled,
        target_classes=request.target_classes,
    )

    # Persist to disk
    fence_store.save(camera_id, normalized)

    # Hot-swap into live pipeline if it's running
    pipeline = camera_manager.pipelines.get(camera_id)
    if pipeline and pipeline.fence_engine:
        source = pipeline.source
        width = source.width or 1280
        height = source.height or 720

        abs_poly = normalized.to_absolute(width, height)
        vf = VirtualFence(
            fence_id="custom_fence",
            camera_id=camera_id,
            name=normalized.name,
            description=normalized.description,
            polygon=abs_poly,
            enabled=normalized.enabled,
            target_classes=normalized.target_classes,
        )
        # Remove old fences and install the new one
        pipeline.fence_engine.fences.clear()
        pipeline.fence_engine.track_states.clear()
        pipeline.fence_engine.add_fence(vf)
        logger.info(f"Hot-swapped fence for running camera {camera_id}")

    return {
        "status": "saved",
        "camera_id": camera_id,
        "fence": normalized.model_dump(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /cameras/{camera_id}/fence
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/{camera_id}/fence")
async def delete_fence(camera_id: str):
    """
    Delete the custom fence for a camera and revert to the default fence.
    Hot-swaps the default fence into the running pipeline if active.
    """
    if not camera_manager.get_camera_config(camera_id):
        raise HTTPException(status_code=404, detail="Camera not found")

    deleted = fence_store.delete(camera_id)

    # Hot-swap default fence into live pipeline
    pipeline = camera_manager.pipelines.get(camera_id)
    if pipeline and pipeline.fence_engine:
        pipeline.fence_engine.fences.clear()
        pipeline.fence_engine.track_states.clear()
        _install_default_fence(pipeline, camera_id)
        logger.info(f"Reverted to default fence for camera {camera_id}")

    return {
        "status": "deleted" if deleted else "no_custom_fence",
        "camera_id": camera_id,
        "message": "Reverted to default fence",
    }


def _install_default_fence(pipeline, camera_id: str):
    """Install the hardcoded default fence (center zone) into a pipeline."""
    width = getattr(pipeline.source, "width", None) or 1280
    height = getattr(pipeline.source, "height", None) or 720
    # Default: 80% of the frame centered
    margin_x = int(width * 0.10)
    margin_y = int(height * 0.10)
    default_poly = [
        (margin_x, margin_y),
        (width - margin_x, margin_y),
        (width - margin_x, height - margin_y),
        (margin_x, height - margin_y),
    ]
    vf = VirtualFence(
        fence_id="default_fence",
        camera_id=camera_id,
        name="Default Detection Zone",
        polygon=default_poly,
        target_classes=["person", "car", "motorcycle", "bus", "truck"],
    )
    pipeline.fence_engine.add_fence(vf)
