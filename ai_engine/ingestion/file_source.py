import os
from pathlib import Path
import cv2
import numpy as np
from typing import Optional
from ai_engine.ingestion.source import BaseVideoSource
from backend.app.core.config import settings
from backend.app.core.logger import get_logger

logger = get_logger("FileVideoSource")

class FileVideoSource(BaseVideoSource):
    """Video source for pre-recorded local files (MP4, AVI, etc.)."""

    def __init__(self, source_id: str, url: str):
        resolved_url = self._resolve_video_path(source_id, url)
        super().__init__(source_id, resolved_url)
        self.cap = None

    @classmethod
    def _resolve_video_path(cls, source_id: str, raw_path: str) -> str:
        """
        Resolves Windows paths or relative container paths to the active video directory.
        Checks:
        1. Direct existence of path.
        2. Extracted filename against data/videos, /app/data/videos, settings.VIDEOS_DIR.
        """
        if not raw_path:
            return raw_path

        cleaned = raw_path.strip().strip('"\'')
        if os.path.exists(cleaned):
            return cleaned

        # Extract filename (handles both Windows C:\path\file.mp4 and Linux /path/file.mp4)
        normalized = cleaned.replace("\\", "/")
        filename = os.path.basename(normalized)

        candidates = [
            os.path.join(settings.VIDEOS_DIR, filename),
            os.path.join("data", "videos", filename),
            os.path.join("/app", "data", "videos", filename),
            os.path.join("data", filename),
            os.path.join("/app", "data", filename),
            filename
        ]

        for cand in candidates:
            if os.path.exists(cand):
                logger.info(f"[{source_id}] Resolved video path '{raw_path}' -> '{cand}'")
                return cand

        # If not resolved yet, log helpful warning and fallback to cleaned
        logger.warning(
            f"[{source_id}] Video file not found directly at '{cleaned}'. "
            f"If running in Docker, place video files in 'data/videos/' (or mounted at '/app/data/videos/')."
        )
        return cleaned

    def connect(self) -> bool:
        logger.info(f"[{self.source_id}] Connecting to file: {self.url}")
        self.cap = cv2.VideoCapture(self.url)
        if not self.cap.isOpened():
            logger.error(f"[{self.source_id}] Failed to open file: {self.url}")
            self.is_connected = False
            return False
            
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30.0 # Default fallback
        
        self.loop_count = 0       # increments each time the file restarts
        self.is_connected = True
        logger.info(f"[{self.source_id}] Connected. {self.width}x{self.height} @ {self.fps}FPS")
        return True


    def read_frame(self) -> tuple[bool, Optional[np.ndarray]]:
        if not self.is_open():
            return False, None
            
        ret, frame = self.cap.read()
        if not ret:
            # Loop the video for testing purposes
            logger.info(f"[{self.source_id}] End of file reached. Restarting video.")
            self.cap.release()
            self.cap = cv2.VideoCapture(self.url)
            self.loop_count += 1          # signal a new loop to the pipeline
            ret, frame = self.cap.read()
            if not ret:
                logger.error(f"[{self.source_id}] Error reading frame after restart.")
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
