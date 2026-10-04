import cv2
import numpy as np
import time
from typing import Optional
from ai_engine.ingestion.source import BaseVideoSource
from backend.app.core.logger import get_logger

logger = get_logger("RTSPVideoSource")

class RTSPVideoSource(BaseVideoSource):
    """Video source for RTSP streams with auto-reconnect."""

    def __init__(self, source_id: str, url: str):
        super().__init__(source_id, url)
        self.cap = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0 # seconds

    def connect(self) -> bool:
        logger.info(f"[{self.source_id}] Connecting to RTSP stream... (URL masked for security)")
        self.cap = cv2.VideoCapture(self.url)
        
        # Optimize for RTSP if needed (e.g. cv2.CAP_FFMPEG, setting buffer size)
        # Note: Set env var OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;udp" etc outside this if needed
        
        if not self.cap.isOpened():
            logger.error(f"[{self.source_id}] Failed to open RTSP stream.")
            self.is_connected = False
            return False
            
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 25.0 # Typical fallback for IP cameras
            
        self.is_connected = True
        self.reconnect_attempts = 0
        logger.info(f"[{self.source_id}] Connected. {self.width}x{self.height} @ {self.fps}FPS")
        return True

    def _reconnect(self):
        logger.warning(f"[{self.source_id}] Attempting to reconnect...")
        self.release()
        
        while self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"[{self.source_id}] Reconnect attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            time.sleep(self.reconnect_delay)
            
            if self.connect():
                logger.info(f"[{self.source_id}] Reconnection successful.")
                return True
                
        logger.error(f"[{self.source_id}] Max reconnect attempts reached. Source failed.")
        return False

    def read_frame(self) -> tuple[bool, Optional[np.ndarray]]:
        if not self.is_open():
            if not self._reconnect():
                return False, None
            
        ret, frame = self.cap.read()
        if not ret:
            logger.warning(f"[{self.source_id}] Frame read failed. Connection might be lost.")
            self.is_connected = False
            # We don't block by reconnecting here inside read_frame, 
            # we just return False and let the pipeline decide what to do, 
            # or the next call to read_frame will trigger _reconnect.
            return False, None
            
        return True, frame

    def is_open(self) -> bool:
        return self.cap is not None and self.cap.isOpened() and self.is_connected

    def release(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_connected = False
        logger.info(f"[{self.source_id}] Resources released.")
