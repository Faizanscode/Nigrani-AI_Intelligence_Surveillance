import numpy as np
from typing import List, Tuple, Dict
from pathlib import Path
import ultralytics
from ultralytics.cfg import get_cfg
from ultralytics.trackers.byte_tracker import BYTETracker

from backend.app.core.config import settings
from ai_engine.detection.models import DetectionResult, BoundingBox
from ai_engine.tracking.tracker import BaseTracker
from ai_engine.tracking.models import TrackResult

class _MockResults:
    """
    Mock object to simulate Ultralytics Results object for BYTETracker.
    """
    def __init__(self, size: int):
        self.size = size
        self.conf = np.zeros(size)
        self.xywh = np.zeros((size, 4))
        self.cls = np.zeros(size)
        self.xywhr = self.xywh

    def __len__(self):
        return self.size

    def __getitem__(self, idx):
        res = _MockResults(size=0)
        res.conf = self.conf[idx]
        res.xywh = self.xywh[idx]
        res.cls = self.cls[idx]
        res.xywhr = self.xywhr[idx]
        if isinstance(idx, (slice, np.ndarray)):
            res.size = len(res.conf)
        else:
            res.size = 1
        return res

class ByteTrackTracker(BaseTracker):
    """
    Object tracker implementation wrapping Ultralytics BYTETracker.
    Maintains independent track states per camera.
    """
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        
        # Load default bytetrack config from ultralytics and override with our settings
        cfg_path = Path(ultralytics.__file__).parent / 'cfg' / 'trackers' / 'bytetrack.yaml'
        self.args = get_cfg(cfg_path)
        
        self.args.track_buffer = settings.TRACKER_TRACK_BUFFER
        self.args.match_thresh = settings.TRACKER_MATCH_THRESHOLD
        
        # Instantiate the actual tracker
        self.tracker = BYTETracker(self.args)
        
        # Track history mapping: track_id -> List of (center_x, center_y)
        self.trajectories: Dict[int, List[Tuple[int, int]]] = {}
        self.history_length = settings.TRACK_HISTORY_LENGTH

    def reset(self):
        """Reset all tracker state (e.g. on video file loop so IDs don't re-trigger)."""
        self.tracker = BYTETracker(self.args)
        self.trajectories.clear()

    def update(self, detections: List[DetectionResult], frame: np.ndarray) -> List[TrackResult]:
        """
        Updates the tracker with YOLO DetectionResults.
        """
        if not detections:
            # When there are no detections, we must still call update so ByteTrack updates states of lost tracks
            self.tracker.update(_MockResults(size=0), frame)
            return []
            
        # Convert our application DetectionResult to _MockResults
        res = _MockResults(size=len(detections))
        # Keep a mapping from bbox center back to class_name since BYTETracker just outputs class_id
        # Actually BYTETracker returns the original class_id and conf, so we just map class_id to name
        class_name_map = {}
        
        for i, det in enumerate(detections):
            res.conf[i] = det.confidence
            res.cls[i] = det.class_id
            res.xywh[i] = [det.bbox.center_x, det.bbox.center_y, det.bbox.width, det.bbox.height]
            class_name_map[det.class_id] = det.class_name
            
        # Run ByteTrack update
        # Output shape is (N, 8): [x1, y1, x2, y2, track_id, conf, cls, idx]
        try:
            tracks_array = self.tracker.update(res, frame)
        except Exception as e:
            import logging
            logging.getLogger("ByteTrackTracker").error(f"Tracker update failed: {e}")
            return []
            
        track_results = []
        active_ids = set()
        
        for t in tracks_array:
            x1, y1, x2, y2, track_id, conf, cls_id, idx = t
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            track_id = int(track_id)
            cls_id = int(cls_id)
            
            width = x2 - x1
            height = y2 - y1
            center_x = x1 + width // 2
            center_y = y1 + height // 2
            
            # Update trajectory
            if track_id not in self.trajectories:
                self.trajectories[track_id] = []
            
            self.trajectories[track_id].append((center_x, center_y))
            # Keep bounded history
            if len(self.trajectories[track_id]) > self.history_length:
                self.trajectories[track_id] = self.trajectories[track_id][-self.history_length:]
                
            active_ids.add(track_id)
            
            bbox = BoundingBox(
                x1=x1, y1=y1, x2=x2, y2=y2,
                center_x=center_x, center_y=center_y,
                width=width, height=height
            )
            
            cls_name = class_name_map.get(cls_id, str(cls_id))
            
            # Count frames seen based on trajectory length (approximate)
            frames_seen = len(self.trajectories[track_id])
            
            track_res = TrackResult(
                track_id=track_id,
                class_id=cls_id,
                class_name=cls_name,
                confidence=float(conf),
                bbox=bbox,
                trajectory=list(self.trajectories[track_id]),
                frames_seen=frames_seen
            )
            track_results.append(track_res)
            
        # Cleanup stale trajectories
        stale_ids = [tid for tid in self.trajectories if tid not in active_ids]
        # Wait, if an object is temporarily occluded, ByteTrack might not return it this frame, 
        # but it remembers it for `track_buffer` frames.
        # If we remove its trajectory instantly, it will lose its tail if it reappears.
        # Better to not clean up here, or use ByteTrack's internal `lost_stracks`?
        # A simple cleanup is checking if track_id exists in tracker's active or lost stracks.
        # BYTETracker has self.tracker.tracked_stracks and self.tracker.lost_stracks
        tracked_and_lost = set()
        if hasattr(self.tracker, 'tracked_stracks'):
            tracked_and_lost.update(t.track_id for t in self.tracker.tracked_stracks)
        if hasattr(self.tracker, 'lost_stracks'):
            tracked_and_lost.update(t.track_id for t in self.tracker.lost_stracks)
            
        if tracked_and_lost:
            for tid in list(self.trajectories.keys()):
                if tid not in tracked_and_lost:
                    del self.trajectories[tid]
                    
        return track_results
