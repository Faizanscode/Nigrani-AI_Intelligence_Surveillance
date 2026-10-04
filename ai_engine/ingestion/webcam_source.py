import cv2
import numpy as np
from typing import Optional
from ai_engine.ingestion.source import BaseVideoSource
from backend.app.core.logger import get_logger

logger = get_logger("WebcamVideoSource")

class WebcamVideoSource(BaseVideoSource):
    """Video source for local webcams."""

    def __init__(self, source_id: str, url: str):
        super().__init__(source_id, url)
        self.cap = None
        try:
            self.camera_index = int(url)
        except ValueError:
            logger.warning(f"[{self.source_id}] Invalid webcam index '{url}'. Defaulting to 0.")
            self.camera_index = 0

    def connect(self) -> bool:
        logger.info(f"[{self.source_id}] Connecting to webcam index: {self.camera_index}")
        import sys
        
        # Release any prior capture handle
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        # Backends to try in order on Windows: MSMF -> DSHOW -> ANY
        if sys.platform.startswith('win'):
            backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]

        opened = False
        for backend in backends:
            try:
                cap = cv2.VideoCapture(self.camera_index, backend)
                if cap.isOpened():
                    # Read a test frame to verify capture works
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        self.cap = cap
                        opened = True
                        logger.info(f"[{self.source_id}] Connected to webcam index {self.camera_index} using backend {backend}")
                        break
                    else:
                        cap.release()
                else:
                    cap.release()
            except Exception as e:
                logger.warning(f"[{self.source_id}] Error opening webcam with backend {backend}: {e}")

        if not opened or self.cap is None:
            logger.error(f"[{self.source_id}] Failed to open webcam: {self.camera_index}")
            self.is_connected = False
            return False
            
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30.0 # Default fallback
            
        self.is_connected = True
        logger.info(f"[{self.source_id}] Connected. {self.width}x{self.height} @ {self.fps}FPS")
        return True

    def read_frame(self) -> tuple[bool, Optional[np.ndarray]]:
        if not self.is_open():
            return False, None
            
        ret, frame = self.cap.read()
        if not ret:
            logger.error(f"[{self.source_id}] Error reading frame from webcam.")
            self.is_connected = False
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
