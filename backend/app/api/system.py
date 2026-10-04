from fastapi import APIRouter
from typing import Dict, Any
import psutil
import os
import time

from backend.app.services.camera_manager import camera_manager
from backend.app.core.config import settings
from backend.app.core.logger import get_logger

router = APIRouter(prefix="/system", tags=["system"])
logger = get_logger("System")

@router.get("/performance")
def get_performance_metrics() -> Dict[str, Any]:
    process = psutil.Process(os.getpid())
    
    # System & Process Metrics
    metrics = {
        "cpu_percent": psutil.cpu_percent(),
        "process_cpu_percent": process.cpu_percent(),
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "system_memory_percent": psutil.virtual_memory().percent,
        "cameras": []
    }
    
    # Pipeline Metrics
    total_processed = 0
    total_received = 0
    total_errors = 0
    
    for cam_id, pipeline in camera_manager.pipelines.items():
        if pipeline.is_running:
            uptime = time.time() - pipeline.start_time if pipeline.start_time else 0
            fps = pipeline.frames_processed / uptime if uptime > 0 else 0
            
            cam_metrics = {
                "camera_id": cam_id,
                "uptime_seconds": uptime,
                "frames_received": pipeline.frames_received,
                "frames_processed": pipeline.frames_processed,
                "errors": pipeline.errors,
                "processing_fps": fps,
                "input_queue_size": pipeline.frame_queue.qsize(),
                "output_queue_size": pipeline.output_queue.qsize()
            }
            metrics["cameras"].append(cam_metrics)
            
            total_processed += pipeline.frames_processed
            total_received += pipeline.frames_received
            total_errors += pipeline.errors

    metrics["aggregate"] = {
        "total_active_pipelines": len(metrics["cameras"]),
        "total_frames_received": total_received,
        "total_frames_processed": total_processed,
        "total_errors": total_errors,
        "yolo_device": settings.YOLO_DEVICE
    }
    
    return metrics
