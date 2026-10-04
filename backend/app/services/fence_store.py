"""
FenceStore: persistent per-camera fence configuration stored in data/fences.json.
Survives backend restarts. Thread-safe for concurrent reads/writes.
"""
import json
import threading
from pathlib import Path
from typing import Optional, List

from ai_engine.analytics.fence.models import NormalizedFence
from backend.app.core.logger import get_logger

logger = get_logger("FenceStore")

_STORE_PATH = Path("data/fences.json")


class FenceStore:
    """
    Singleton JSON-backed store for per-camera normalized fence configurations.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._data = {}
                    cls._instance._io_lock = threading.Lock()
                    cls._instance._load()
        return cls._instance

    def _load(self):
        """Load existing fences from disk."""
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if _STORE_PATH.exists():
            try:
                with open(_STORE_PATH, "r") as f:
                    raw = json.load(f)
                self._data = raw
                logger.info(f"Loaded {len(raw)} fence(s) from {_STORE_PATH}")
            except Exception as e:
                logger.error(f"Failed to load fence store: {e}")
                self._data = {}
        else:
            self._data = {}

    def _save(self):
        """Persist current state to disk."""
        try:
            _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_STORE_PATH, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save fence store: {e}")

    def get(self, camera_id: str) -> Optional[NormalizedFence]:
        """Return the saved fence for a camera, or None if not set."""
        with self._io_lock:
            raw = self._data.get(camera_id)
        if raw is None:
            return None
        try:
            return NormalizedFence(**raw)
        except Exception as e:
            logger.warning(f"Invalid fence data for camera {camera_id}: {e}")
            return None

    def save(self, camera_id: str, fence: NormalizedFence) -> None:
        """Save (or overwrite) fence for a camera and persist to disk."""
        with self._io_lock:
            self._data[camera_id] = fence.model_dump()
            self._save()
        logger.info(f"Saved custom fence for camera {camera_id} ({len(fence.points)} pts)")

    def delete(self, camera_id: str) -> bool:
        """Delete the saved fence for a camera. Returns True if deleted."""
        with self._io_lock:
            if camera_id in self._data:
                del self._data[camera_id]
                self._save()
                logger.info(f"Deleted custom fence for camera {camera_id}")
                return True
        return False

    def all_camera_ids(self) -> List[str]:
        with self._io_lock:
            return list(self._data.keys())


# Global singleton
fence_store = FenceStore()
