import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    ENVIRONMENT: str = "production"
    LOGGING_LEVEL: str = "INFO"
    FRAME_QUEUE_SIZE: int = 30
    PROCESS_FPS: int = 10
    
    YOLO_MODEL: str = "yolo11n.pt"
    YOLO_CONFIDENCE: float = 0.40
    YOLO_IOU: float = 0.45
    YOLO_DEVICE: str = "cpu"
    DETECTION_CLASSES: str = "person,car,motorcycle,bus,truck"

    # Storage paths
    DATA_DIR: str = "data"
    VIDEOS_DIR: str = "data/videos"
    EVIDENCE_DIR: str = "data/evidence"

    # CORS & Security
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: str = ""
    
    TRACKER_TYPE: str = "bytetrack"
    TRACKER_TRACK_BUFFER: int = 30
    TRACKER_MATCH_THRESHOLD: float = 0.80
    TRACK_HISTORY_LENGTH: int = 30

    VIRTUAL_FENCE_ENABLED: bool = True
    TRIGGER_ON_INITIAL_INSIDE: bool = False
    FENCE_POINT_STRATEGY: str = "bottom_center"
    FENCE_MONITORED_CLASSES: str = "person,car,motorcycle,bus,truck"
    INTRUSION_CONFIRMATION_FRAMES: int = 2
    FENCE_BOUNDARY_TOLERANCE: int = 5
    INTRUSION_COOLDOWN: int = 60

    
    ANPR_ENABLED: bool = True
    ANPR_PROCESS_INTERVAL: int = 2
    ANPR_MIN_CONFIDENCE: float = 0.60
    
    # Event & Alert Configuration
    ALERT_COOLDOWN_SECONDS: int = 60   # 60 s per track per fence — prevents spam on looping videos
    MAX_IN_MEMORY_EVENTS: int = 1000
    MAX_IN_MEMORY_ALERTS: int = 500

    # Behavior settings
    LOITERING_ENABLED: bool = True
    LOITERING_TIME_THRESHOLD: int = 5
    LOITERING_DISTANCE_THRESHOLD: int = 50
    LOITERING_COOLDOWN: int = 60

    NIGHT_MOVEMENT_ENABLED: bool = True
    NIGHT_MOVEMENT_MODE: str = "AUTO"
    NIGHT_START_TIME: str = "18:00"
    NIGHT_END_TIME: str = "06:00"
    NIGHT_MOVEMENT_MIN_DISTANCE: int = 20
    NIGHT_MOVEMENT_MIN_DURATION: int = 2
    NIGHT_MOVEMENT_COOLDOWN: int = 30

    FACE_RECOGNITION_ENABLED: bool = True
    
    # Correlation Engine settings
    CORRELATION_ENABLED: bool = True
    CORRELATION_TIME_WINDOW_SECONDS: int = 300
    CORRELATION_CAMERA_DISTANCE_METERS: int = 1000
    MIN_INCIDENT_CORRELATION_SCORE: int = 60

    class Config:
        env_file = ".env"

settings = Settings()
