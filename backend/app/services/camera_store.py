"""
CameraStore: persistent camera configuration stored in data/cameras.json.
Survives backend restarts. Thread-safe for concurrent reads/writes.
"""
import json
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.app.core.logger import get_logger

logger = get_logger("CameraStore")

_STORE_PATH = Path("data/cameras.json")

class CameraStore:
    """
    Singleton JSON-backed store for camera configurations.
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
                    if not cls._instance._data:
                        cls._instance._seed_demo_cameras()
        return cls._instance

    def _load(self):
        """Load existing cameras from disk."""
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if _STORE_PATH.exists():
            try:
                with open(_STORE_PATH, "r") as f:
                    raw = json.load(f)
                self._data = raw
                logger.info(f"Loaded {len(raw)} camera(s) from {_STORE_PATH}")
            except Exception as e:
                logger.error(f"Failed to load camera store: {e}")
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
            logger.error(f"Failed to save camera store: {e}")

    def _seed_demo_cameras(self):
        """Seed 4 demo cameras with fictional locations if store is empty."""
        demo_cameras = [
            {
                "id": "CAM-DEMO-001",
                "name": "North Sector Demo 1",
                "type": "rtsp",
                "url": "rtsp://demo/fake/stream",
                "latitude": 34.0,
                "longitude": 74.8,
                "border_sector": "NORTH-01",
                "border_state": "Jammu and Kashmir",
                "border_region": "NORTH",
                "bop_name": "BOP-DEMO-N"
            },
            {
                "id": "CAM-DEMO-002",
                "name": "West Sector Demo 2",
                "type": "rtsp",
                "url": "rtsp://demo/fake/stream",
                "latitude": 30.0,
                "longitude": 73.5,
                "border_sector": "WEST-02",
                "border_state": "Punjab",
                "border_region": "WEST",
                "bop_name": "BOP-DEMO-W"
            },
            {
                "id": "CAM-DEMO-003",
                "name": "East Sector Demo 3",
                "type": "rtsp",
                "url": "rtsp://demo/fake/stream",
                "latitude": 24.5,
                "longitude": 88.5,
                "border_sector": "EAST-03",
                "border_state": "West Bengal",
                "border_region": "EAST",
                "bop_name": "BOP-DEMO-E"
            },
            {
                "id": "CAM-DEMO-004",
                "name": "Northeast Sector Demo 4",
                "type": "rtsp",
                "url": "rtsp://demo/fake/stream",
                "latitude": 27.5,
                "longitude": 94.5,
                "border_sector": "NORTHEAST-04",
                "border_state": "Assam",
                "border_region": "NORTHEAST",
                "bop_name": "BOP-DEMO-NE"
            }
        ]
        with self._io_lock:
            for cam in demo_cameras:
                self._data[cam["id"]] = cam
            self._save()
        logger.info("Seeded 4 demo cameras with fictional coordinates.")

    def get(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Return the saved dict for a camera, or None if not set."""
        with self._io_lock:
            raw = self._data.get(camera_id)
        return raw

    def save(self, camera_id: str, camera_dict: Dict[str, Any]) -> None:
        """Save (or overwrite) camera and persist to disk."""
        with self._io_lock:
            self._data[camera_id] = camera_dict
            self._save()
        logger.info(f"Saved camera config for {camera_id}")

    def delete(self, camera_id: str) -> bool:
        """Delete the saved camera. Returns True if deleted."""
        with self._io_lock:
            if camera_id in self._data:
                del self._data[camera_id]
                self._save()
                logger.info(f"Deleted camera {camera_id} from store")
                return True
        return False

    def all_cameras(self) -> List[Dict[str, Any]]:
        with self._io_lock:
            return list(self._data.values())

# Global singleton
camera_store = CameraStore()
