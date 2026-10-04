import cv2
import numpy as np
from typing import List, Dict, Any
from ai_engine.tracking.models import TrackResult

class TrackVisualizer:
    @staticmethod
    def draw_analytics(frame: np.ndarray, metadata: Dict[str, Any]) -> np.ndarray:
        """
        Draws fences, tracks, trajectories, and intrusion events.
        """
        img = frame.copy()
        
        fences = metadata.get("fences", [])
        events = metadata.get("events", [])
        tracks = metadata.get("tracks", [])
        
        # Draw fences
        for fence in fences:
            if not fence.enabled:
                continue
            pts = np.array(fence.polygon, np.int32)
            pts = pts.reshape((-1, 1, 2))
            
            # Draw semi-transparent overlay
            overlay = img.copy()
            cv2.fillPoly(overlay, [pts], (0, 0, 255))
            cv2.addWeighted(overlay, 0.2, img, 0.8, 0, img)
            
            # Draw boundary
            cv2.polylines(img, [pts], isClosed=True, color=(0, 0, 255), thickness=2)
            
            # Draw fence name
            cv2.putText(img, f"FENCE: {fence.name}", (pts[0][0][0], pts[0][0][1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        
        # We can generate distinct colors based on track_id
        def get_color(track_id: int):
            np.random.seed(track_id)
            return tuple(int(c) for c in np.random.randint(0, 255, size=3))

        for track in tracks:
            color = get_color(track.track_id)
            x1, y1 = track.bbox.x1, track.bbox.y1
            x2, y2 = track.bbox.x2, track.bbox.y2
            # Find fence state for this track if it exists
            fence_states = metadata.get("fence_states", {})
            state_text = ""
            for (f_id, t_id), state_info in fence_states.items():
                if t_id == track.track_id:
                    state_text = f" [{state_info['status']}]"
                    break

            # Draw bbox
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            # Determine if this track has a recent event
            event_text = ""
            for evt in events:
                if evt.track_id == track.track_id:
                    event_text = " - INTRUSION!"
                    # Emphasize bbox for intrusion
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 4)
            
            # Draw evaluation point (bottom-center by default)
            pt_x = track.bbox.center_x
            pt_y = track.bbox.y2
            cv2.circle(img, (pt_x, pt_y), 5, (0, 255, 255), -1)
            
            # Face recognition label
            face_text = ""
            face_results = metadata.get("face_recognition", [])
            for f in face_results:
                if f.get("track_id") == track.track_id:
                    if f.get("status") == "RECOGNIZED":
                        face_text = f" [{f.get('name')}]"
                    elif f.get("status") == "UNKNOWN":
                        face_text = " [Unknown Face]"
                    break

            # Draw label: class_name #ID conf
            label = f"{track.class_name} #{track.track_id}{face_text} {track.confidence:.2f}{state_text}{event_text}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(img, (x1, y1 - 20), (x1 + w, y1), color, -1)
            cv2.putText(img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Draw trajectory tail
            if len(track.trajectory) > 1:
                pts = np.array(track.trajectory, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img, [pts], isClosed=False, color=color, thickness=2)
                
        # Draw top-level alerts if events present
        if events:
            alert_text = f"WARNING: {len(events)} INTRUSION(S) DETECTED!"
            cv2.putText(img, alert_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                
        return img

    @staticmethod
    def draw_tracks(frame: np.ndarray, tracks: List[TrackResult]) -> np.ndarray:
        """
        Draws bounding boxes, labels, and trajectories for tracked objects.
        """
        img = frame.copy()
        
        # We can generate distinct colors based on track_id
        def get_color(track_id: int):
            np.random.seed(track_id)
            return tuple(int(c) for c in np.random.randint(0, 255, size=3))

        for track in tracks:
            color = get_color(track.track_id)
            x1, y1 = track.bbox.x1, track.bbox.y1
            x2, y2 = track.bbox.x2, track.bbox.y2
            
            # Draw bbox
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            # Draw label: class_name #ID conf
            label = f"{track.class_name} #{track.track_id} {track.confidence:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(img, (x1, y1 - 20), (x1 + w, y1), color, -1)
            cv2.putText(img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Draw trajectory tail
            if len(track.trajectory) > 1:
                pts = np.array(track.trajectory, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img, [pts], isClosed=False, color=color, thickness=2)
                
        return img
