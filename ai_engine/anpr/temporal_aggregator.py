import time
from collections import defaultdict
from typing import Dict, Optional

class TemporalAggregator:
    """
    Aggregates OCR readings over multiple frames for the same vehicle track.
    Helps resolve OCR noise and outputs a stable, high-confidence reading.
    """
    def __init__(self, min_observations: int = 2, cooldown_seconds: float = 30.0, expiry_seconds: float = 30.0):
        # track_id -> dict of { 'plate_text': {'count': int, 'total_conf': float}, 'last_seen': float, 'reported': bool }
        self.track_history = {}
        self.min_observations = min_observations
        self.cooldown_seconds = cooldown_seconds
        self.expiry_seconds = expiry_seconds

    def add_observation(self, track_id: int, plate_text: str, confidence: float, current_time: float) -> Optional[Dict]:
        """
        Add a new OCR observation for a track. 
        Returns aggregated best string and average confidence if stable enough, else None.
        """
        if track_id not in self.track_history:
            self.track_history[track_id] = {
                'candidates': defaultdict(lambda: {'count': 0, 'total_conf': 0.0}),
                'last_seen': current_time,
                'last_reported': 0.0
            }
            
        history = self.track_history[track_id]
        history['last_seen'] = current_time
        
        cand = history['candidates'][plate_text]
        cand['count'] += 1
        cand['total_conf'] += confidence
        
        # Cleanup old tracks to prevent memory leaks
        self._cleanup(current_time)
        
        return self._evaluate(track_id, current_time)
        
    def _evaluate(self, track_id: int, current_time: float) -> Optional[Dict]:
        history = self.track_history.get(track_id)
        if not history:
            return None
            
        # Find the most frequent candidate
        best_plate = None
        best_count = 0
        best_conf_sum = 0.0
        
        for plate, data in history['candidates'].items():
            if data['count'] > best_count or (data['count'] == best_count and data['total_conf'] > best_conf_sum):
                best_plate = plate
                best_count = data['count']
                best_conf_sum = data['total_conf']
                
        if best_count >= self.min_observations:
            avg_conf = best_conf_sum / best_count
            
            # Duplicate suppression (cooldown)
            if current_time - history['last_reported'] >= self.cooldown_seconds:
                history['last_reported'] = current_time
                return {
                    'plate_text': best_plate,
                    'confidence': avg_conf,
                    'observations': best_count
                }
                
        return None

    def _cleanup(self, current_time: float):
        expired = [tid for tid, data in self.track_history.items() if current_time - data['last_seen'] > self.expiry_seconds]
        for tid in expired:
            del self.track_history[tid]
