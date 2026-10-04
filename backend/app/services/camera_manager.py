import threading
from typing import Dict, List, Optional, Set
from pydantic import BaseModel

from ai_engine.pipeline import CameraPipeline
from ai_engine.ingestion.file_source import FileVideoSource
from ai_engine.ingestion.webcam_source import WebcamVideoSource
from ai_engine.ingestion.rtsp_source import RTSPVideoSource
from ai_engine.detection.yolo_detector import YOLODetector
from ai_engine.tracking.bytetrack import ByteTrackTracker
from ai_engine.analytics.fence.engine import FenceEngine
from ai_engine.anpr.engine import ANPREngine
from ai_engine.behavior.engine import BehaviorEngine
from ai_engine.face_recognition.engine import FaceRecognitionEngine
from backend.app.core.logger import get_logger
from backend.app.core.config import settings
from backend.app.core.event_bus import event_bus

logger = get_logger("CameraManager")

class CameraConfig(BaseModel):
    id: str
    name: str
    type: str  # 'file', 'webcam', 'rtsp'
    url: str
    # Map Metadata
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    border_sector: Optional[str] = None
    border_state: Optional[str] = None
    border_region: Optional[str] = None
    bop_name: Optional[str] = None

class CameraManager:
    """
    Singleton manager to handle multiple camera pipelines.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CameraManager, cls).__new__(cls)
            cls._instance.pipelines = {}  # type: Dict[str, CameraPipeline]
            cls._instance.configs = {}    # type: Dict[str, CameraConfig]
            cls._instance._starting_cameras = set()  # type: Set[str]
            cls._instance._lock = threading.Lock()
            
            # Load cameras from persistent store
            try:
                from backend.app.services.camera_store import camera_store
                for cam_dict in camera_store.all_cameras():
                    cls._instance.configs[cam_dict["id"]] = CameraConfig(**cam_dict)
            except Exception as e:
                logger.error(f"Failed to load cameras from store: {e}")
                
        return cls._instance
        
    def add_camera(self, config: CameraConfig) -> bool:
        with self._lock:
            if config.id in self.configs:
                logger.warning(f"Camera {config.id} already exists.")
                return False
                
            self.configs[config.id] = config
            try:
                from backend.app.services.camera_store import camera_store
                camera_store.save(config.id, config.model_dump())
            except Exception as e:
                logger.error(f"Failed to save camera {config.id} to store: {e}")
                
            logger.info(f"Added camera configuration: {config.name} ({config.id})")
            return True
        
    def get_camera_config(self, camera_id: str) -> Optional[CameraConfig]:
        with self._lock:
            return self.configs.get(camera_id)
        
    def get_all_cameras(self) -> List[CameraConfig]:
        with self._lock:
            return list(self.configs.values())

    def start_camera(self, camera_id: str) -> bool:
        with self._lock:
            if camera_id not in self.configs:
                logger.error(f"Cannot start unknown camera: {camera_id}")
                return False
                
            if camera_id in self.pipelines and self.pipelines[camera_id].is_running:
                logger.info(f"Camera {camera_id} is already running.")
                return True

            if camera_id in self._starting_cameras:
                logger.info(f"Camera {camera_id} is already starting in another thread.")
                return True

            self._starting_cameras.add(camera_id)
            config = self.configs[camera_id]

        try:
            return self._do_start_camera(camera_id, config)
        finally:
            with self._lock:
                self._starting_cameras.discard(camera_id)

    def _do_start_camera(self, camera_id: str, config: CameraConfig) -> bool:
        source = None
        
        if config.type == 'file':
            source = FileVideoSource(config.id, config.url)
        elif config.type == 'webcam':
            source = WebcamVideoSource(config.id, config.url)
        elif config.type == 'rtsp':
            source = RTSPVideoSource(config.id, config.url)
        else:
            logger.error(f"Unknown camera type: {config.type}")
            return False
            
        pipeline = CameraPipeline(
            source=source, 
            process_fps=settings.PROCESS_FPS, 
            queue_size=settings.FRAME_QUEUE_SIZE
        )
        
        # Create and add YOLO detector
        detector = YOLODetector()
        pipeline.add_detector(detector)
        
        # Create and add object tracker
        if settings.TRACKER_TYPE == "bytetrack":
            tracker = ByteTrackTracker(camera_id)
            pipeline.add_tracker(tracker)
            
        # Create and add fence engine
        if settings.VIRTUAL_FENCE_ENABLED:
            fence_engine = FenceEngine(camera_id)
            from ai_engine.analytics.fence.models import VirtualFence, NormalizedFence
            from backend.app.services.fence_store import fence_store

            saved = fence_store.get(camera_id)
            if saved:
                # We need actual video dimensions — connect source briefly to read them
                # or use a placeholder; dimensions are patched after connect() in pipeline.start()
                # Use a sentinel width/height; we update after source connects
                _pending_normalized_fence = saved
                logger.info(f"Found custom fence for camera {camera_id}. Will apply after connect.")
            else:
                _pending_normalized_fence = None

            # Install a temporary default fence (will be overwritten post-connect if custom exists)
            default_fence = VirtualFence(
                fence_id="default_fence",
                camera_id=camera_id,
                name="Default Detection Zone",
                polygon=[(100, 100), (1100, 100), (1100, 700), (100, 700)],
                target_classes=["person", "car", "motorcycle", "bus", "truck"],
            )
            fence_engine.add_fence(default_fence)
            pipeline.add_fence_engine(fence_engine)
            pipeline._pending_normalized_fence = _pending_normalized_fence  # carry through

            
        # Create and add ANPR engine
        if settings.ANPR_ENABLED:
            anpr_engine = ANPREngine(camera_id)
            pipeline.add_anpr_engine(anpr_engine)
        # Create and add Behavior engine
        if settings.LOITERING_ENABLED or settings.NIGHT_MOVEMENT_ENABLED:
            behavior_engine = BehaviorEngine()
            pipeline.add_behavior_engine(behavior_engine)
            
        # Create and add Face Recognition engine
        if settings.FACE_RECOGNITION_ENABLED:
            face_engine = FaceRecognitionEngine(camera_id)
            pipeline.add_face_engine(face_engine)
        
        if pipeline.start():
            with self._lock:
                self.pipelines[camera_id] = pipeline
            event_bus.publish("camera.status", {"camera_id": camera_id, "status": "ONLINE"})
            return True
        return False
        
    def stop_camera(self, camera_id: str) -> bool:
        with self._lock:
            pipeline = self.pipelines.pop(camera_id, None)

        if pipeline:
            pipeline.stop()
            logger.info(f"Stopped camera: {camera_id}")
            event_bus.publish("camera.status", {"camera_id": camera_id, "status": "OFFLINE"})
            # Clear dedup cache so old events don't re-fire on next start
            try:
                from backend.app.services.event_engine import global_event_engine
                global_event_engine.clear_camera_state(camera_id)
            except Exception:
                pass
            return True
        return False
        
    def remove_camera(self, camera_id: str) -> bool:
        self.stop_camera(camera_id)
        if camera_id in self.configs:
            del self.configs[camera_id]
            try:
                from backend.app.services.camera_store import camera_store
                camera_store.delete(camera_id)
            except Exception as e:
                logger.error(f"Failed to delete camera {camera_id} from store: {e}")
            return True
        return False
        
    def get_camera_health(self, camera_id: str) -> Optional[Dict]:
        if camera_id in self.pipelines:
            return self.pipelines[camera_id].get_health()
        return None
        
    def capture_snapshot(self, camera_id: str):
        """Retrieve the latest annotated frame from the pipeline."""
        if camera_id in self.pipelines:
            pipeline = self.pipelines[camera_id]
            if pipeline.latest_annotated_frame is not None:
                return pipeline.latest_annotated_frame.copy()
            # Fallback to raw frame if annotated isn't ready
            with pipeline._frame_lock:
                if pipeline.latest_frame is not None:
                    return pipeline.latest_frame.copy()
        return None
        
    def stop_all(self):
        for cam_id in list(self.pipelines.keys()):
            self.stop_camera(cam_id)

camera_manager = CameraManager()
