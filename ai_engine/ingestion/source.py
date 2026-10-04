from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np

class BaseVideoSource(ABC):
    """
    Abstract base class for all video sources (File, Webcam, RTSP).
    Ensures a consistent interface for the downstream pipeline.
    """
    
    def __init__(self, source_id: str, url: str):
        self.source_id = source_id
        self.url = url
        self.width = 0
        self.height = 0
        self.fps = 0
        self.is_connected = False
        
    @abstractmethod
    def connect(self) -> bool:
        """Initialize connection to the video source."""
        pass
        
    @abstractmethod
    def read_frame(self) -> tuple[bool, Optional[np.ndarray]]:
        """
        Read the next frame.
        Returns:
            tuple: (success (bool), frame (numpy array or None))
        """
        pass
        
    @abstractmethod
    def is_open(self) -> bool:
        """Check if the source is currently open and healthy."""
        pass
        
    @abstractmethod
    def release(self) -> None:
        """Release resources associated with the source."""
        pass
        
    def get_metadata(self) -> Dict[str, Any]:
        """Return metadata about the source."""
        return {
            "source_id": self.source_id,
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "is_connected": self.is_connected,
        }
