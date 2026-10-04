import os
import cv2
import json
import numpy as np
from typing import Dict, List, Any, Optional
from backend.app.core.logger import get_logger
from pydantic import BaseModel

logger = get_logger("FaceRecognitionEngine")

class FaceRecognitionResult(BaseModel):
    event_id: str
    event_type: str = "FACE_RECOGNITION"
    camera_id: str
    object_class: str = "person"
    track_id: int
    name: str
    confidence: float
    status: str  # RECOGNIZED, UNKNOWN, LOW_CONFIDENCE, NO_FACE
    bbox: List[int]
    timestamp: float

class FaceRecognitionEngine:
    def __init__(self, camera_id: str, registry_file: str = "data/face_registry.json"):
        self.camera_id = camera_id
        self.registry_file = registry_file
        self.known_face_encodings = []
        self.known_face_names = []
        self.track_cache = {}  # track_id -> {"name": str, "status": str, "confidence": float, "last_check": float, "frame_num": int}
        self.frame_counter = 0
        self.frame_skip = 3    # Process new faces every 3rd frame to keep CPU light
        
        # Load face_recognition library lazily to avoid crashing if not installed
        try:
            import face_recognition
            self.face_recognition = face_recognition
            self.is_available = True
            self._load_registry()
            logger.info(f"[{self.camera_id}] FaceRecognitionEngine initialized. Loaded {len(self.known_face_names)} faces.")
        except ImportError:
            self.is_available = False
            logger.error(f"[{self.camera_id}] face_recognition library not found. Face Recognition will be disabled.")
            
    def _load_registry(self):
        """Loads known faces from JSON registry. Extracts embeddings if needed, or stores pre-computed ones."""
        if not os.path.exists(self.registry_file):
            # Create empty if not exist
            os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
            with open(self.registry_file, 'w') as f:
                json.dump([], f)
            return

        try:
            with open(self.registry_file, 'r') as f:
                faces = json.load(f)
            
            self.known_face_encodings = []
            self.known_face_names = []
            
            for face in faces:
                if 'embedding' in face and face['embedding']:
                    self.known_face_encodings.append(np.array(face['embedding']))
                    self.known_face_names.append(face['name'])
            # Clear cache so new enrollments take effect immediately
            self.track_cache.clear()
        except Exception as e:
            logger.error(f"Error loading face registry: {e}")

    def process(self, frame: np.ndarray, tracks: List[Any], metadata: Dict[str, Any], active_intruders: Optional[set] = None) -> List[FaceRecognitionResult]:
        if not self.is_available:
            return []

        self.frame_counter += 1
        results = []
        timestamp = metadata.get("timestamp", 0)
        current_track_ids = set()

        for track in tracks:
            # Extract track fields supporting both TrackResult objects and dicts
            if hasattr(track, 'class_name'):
                class_name = track.class_name
                track_id = track.track_id
                bbox_obj = track.bbox
                x1, y1, x2, y2 = map(int, [bbox_obj.x1, bbox_obj.y1, bbox_obj.x2, bbox_obj.y2])
            elif isinstance(track, dict):
                class_name = track.get('class_name')
                track_id = track.get('track_id')
                box = track.get('bbox', track.get('box', [0, 0, 0, 0]))
                x1, y1, x2, y2 = map(int, box)
            else:
                continue

            # Only process persons
            if class_name != 'person':
                continue

            current_track_ids.add(track_id)

            # Ensure within bounds
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            if x2 <= x1 or y2 <= y1:
                continue

            # Fast cache check:
            # If this person has already been recognized, reuse their identity across frames!
            # Only re-evaluate recognized faces once every 30 frames (~3s) to save heavy CPU work.
            cached = self.track_cache.get(track_id)
            need_eval = False
            if cached is None:
                need_eval = True
            elif cached["status"] == "RECOGNIZED":
                if self.frame_counter - cached.get("frame_num", 0) > 30:
                    need_eval = (self.frame_counter % self.frame_skip == 0)
            else:
                # If unknown or no-face, re-check periodically
                if self.frame_counter - cached.get("frame_num", 0) > 10:
                    need_eval = (self.frame_counter % self.frame_skip == 0)

            if not need_eval and cached is not None:
                # Instant return from cache (0ms CPU time!)
                results.append(FaceRecognitionResult(
                    event_id=f"face_{self.camera_id}_{track_id}_{timestamp}",
                    camera_id=self.camera_id,
                    track_id=track_id,
                    name=cached["name"],
                    confidence=cached["confidence"],
                    status=cached["status"],
                    bbox=[x1, y1, x2, y2],
                    timestamp=timestamp
                ))
                continue
                
            # Crop the person
            person_crop = frame[y1:y2, x1:x2]
            if person_crop.size == 0:
                continue

            # Downscale large crops for significantly faster face detection on CPU
            crop_h, crop_w = person_crop.shape[:2]
            max_dim = max(crop_h, crop_w)
            scale = 1.0
            if max_dim > 300:
                scale = 300.0 / max_dim
                eval_crop = cv2.resize(person_crop, (int(crop_w * scale), int(crop_h * scale)))
            else:
                eval_crop = person_crop
                
            # Convert to RGB (face_recognition expects RGB)
            rgb_crop = cv2.cvtColor(eval_crop, cv2.COLOR_BGR2RGB)
            
            # Detect faces in the crop
            face_locations = self.face_recognition.face_locations(rgb_crop, model="hog")
            
            if not face_locations:
                status = "NO_FACE"
                name = "Unknown"
                confidence = 0.0
                self.track_cache[track_id] = {
                    "name": name, "status": status, "confidence": confidence, "frame_num": self.frame_counter
                }
                results.append(FaceRecognitionResult(
                    event_id=f"face_{self.camera_id}_{track_id}_{timestamp}",
                    camera_id=self.camera_id,
                    track_id=track_id,
                    name=name,
                    confidence=confidence,
                    status=status,
                    bbox=[x1, y1, x2, y2],
                    timestamp=timestamp
                ))
                continue
                
            # Extract encodings for faces found
            face_encodings = self.face_recognition.face_encodings(rgb_crop, face_locations)
            
            if not face_encodings:
                continue
                
            # Take the largest / first face found in the person crop
            face_encoding = face_encodings[0]
            
            # See if the face is a match for the known face(s)
            name = "Unknown"
            status = "UNKNOWN"
            confidence = 0.0
            
            if self.known_face_encodings:
                matches = self.face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                if True in matches:
                    face_distances = self.face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    best_match_index = int(np.argmin(face_distances))
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        status = "RECOGNIZED"
                        confidence = float(max(0.0, min(1.0, 1.0 - face_distances[best_match_index])))

            # Save in track cache
            self.track_cache[track_id] = {
                "name": name, "status": status, "confidence": confidence, "frame_num": self.frame_counter
            }
                    
            results.append(FaceRecognitionResult(
                event_id=f"face_{self.camera_id}_{track_id}_{timestamp}",
                camera_id=self.camera_id,
                track_id=track_id,
                name=name,
                confidence=confidence,
                status=status,
                bbox=[x1, y1, x2, y2],
                timestamp=timestamp
            ))
            
        # Clean up cache for old tracks
        stale_tracks = [tid for tid in self.track_cache if tid not in current_track_ids]
        if len(stale_tracks) > 50:
            for tid in stale_tracks:
                del self.track_cache[tid]

        return results
