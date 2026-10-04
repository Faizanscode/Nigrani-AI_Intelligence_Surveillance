import numpy as np
import time
from typing import List, Dict, Any, Optional, Set

from .models import ANPRResult, OCRResult
from .plate_detector import OpenCVPlateDetector, MockPlateDetector
from .ocr_engine import EasyOCREngine, MockOCREngine
from .plate_validator import PlateValidator
from .temporal_aggregator import TemporalAggregator
from backend.app.core.logger import get_logger

logger = get_logger("ANPREngine")

class ANPREngine:
    """
    Orchestrates the ANPR pipeline for a single camera.
    Uses OpenCV color & contour detection + EasyOCR text recognition.
    Filters specifically for vehicles intruding into configured virtual fences.
    """
    def __init__(self, camera_id: str):
        self.camera_id = camera_id

        # Use real detector and OCR with fallback
        try:
            self.detector = OpenCVPlateDetector()
            self.ocr = EasyOCREngine()
        except Exception as e:
            logger.warning(f"[ANPR][{self.camera_id}] Falling back to mock ANPR engines: {e}")
            self.detector = MockPlateDetector()
            self.ocr = MockOCREngine()

        self.validator = PlateValidator()
        self.aggregator = TemporalAggregator(min_observations=1, cooldown_seconds=20.0)

        self.target_classes = ["car", "truck", "bus", "motorcycle"]
        self.frame_skip = 2      # process every 2nd frame for balance of latency and CPU
        self.frame_counter = 0

    def process(self, frame: np.ndarray, tracks: List[Any], metadata: Dict[str, Any],
                active_intruders: Optional[Set[int]] = None) -> List[ANPRResult]:
        """
        Process the frame and tracks to find and read license plates.
        If active_intruders is provided, only processes tracks that have intruded the virtual fence.
        """
        results = []
        self.frame_counter += 1

        if self.frame_counter % self.frame_skip != 0:
            return results

        current_time = metadata.get("timestamp", time.time())
        h_frame, w_frame = frame.shape[:2]

        for track in tracks:
            if hasattr(track, 'class_name'):
                class_name = track.class_name
                track_id = track.track_id
                bbox_obj = track.bbox
                bbox = [bbox_obj.x1, bbox_obj.y1, bbox_obj.x2, bbox_obj.y2]
            else:
                class_name = track.get("class_name")
                track_id = track.get("track_id")
                bbox = track.get("bbox")

            if class_name not in self.target_classes:
                continue

            if track_id is None or bbox is None:
                continue

            # ── Intrusion Filtering ──────────────────────────────────────────
            # If active_intruders filter is active, only process vehicles inside/intruding fence!
            is_intruder = False
            if active_intruders is not None:
                if track_id not in active_intruders:
                    logger.debug(f"[ANPR][{self.camera_id}] Track#{track_id} is outside fence — skipped")
                    continue
                is_intruder = True
            else:
                is_intruder = True

            x1, y1, x2, y2 = [int(v) for v in bbox]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_frame, x2), min(h_frame, y2)

            if x2 - x1 < 60 or y2 - y1 < 50:
                continue

            # ── 1. Crop vehicle ──────────────────────────────────────────────
            vehicle_crop = frame[y1:y2, x1:x2]

            # ── 2. Detect plate candidates within crop ───────────────────────
            plate_detections = self.detector.detect(vehicle_crop)
            if not plate_detections:
                continue

            # Evaluate each plate candidate (up to 2 best)
            sorted_candidates = sorted(plate_detections, key=lambda p: p.confidence, reverse=True)[:2]
            best_reading = None
            best_candidate_det = None

            for candidate in sorted_candidates:
                px1, py1, px2, py2 = candidate.bbox
                plate_crop = vehicle_crop[py1:py2, px1:px2]
                if plate_crop.size == 0 or plate_crop.shape[0] < 15 or plate_crop.shape[1] < 25:
                    continue

                ocr_result = self.ocr.read(plate_crop, seed=track_id)
                if ocr_result.normalized_text and len(ocr_result.normalized_text) >= 4:
                    if best_reading is None or ocr_result.confidence > best_reading.confidence:
                        best_reading = ocr_result
                        best_candidate_det = candidate

            if not best_reading or not best_reading.normalized_text:
                continue

            # Clean and normalize
            plate_text = self.validator.normalize(best_reading.normalized_text)
            validation = self.validator.validate(plate_text)

            # ── 3. Temporal aggregation (dedup) ──────────────────────────────
            stable_reading = self.aggregator.add_observation(
                track_id=track_id,
                plate_text=plate_text,
                confidence=best_reading.confidence,
                current_time=current_time
            )

            # ── 4. Emit if consensus reached ─────────────────────────────────
            if stable_reading:
                abs_px1 = x1 + best_candidate_det.bbox[0]
                abs_py1 = y1 + best_candidate_det.bbox[1]
                abs_px2 = x1 + best_candidate_det.bbox[2]
                abs_py2 = y1 + best_candidate_det.bbox[3]

                res = ANPRResult.create(
                    camera_id=self.camera_id,
                    track_id=track_id,
                    vehicle_class=class_name,
                    bbox=[abs_px1, abs_py1, abs_px2, abs_py2],
                    ocr=OCRResult(
                        raw_text=best_reading.raw_text,
                        normalized_text=stable_reading['plate_text'],
                        confidence=stable_reading['confidence']
                    ),
                    validation=validation,
                    det_conf=best_candidate_det.confidence,
                    is_fence_intruder=is_intruder
                )
                results.append(res)
                logger.info(
                    f"[ANPR][{self.camera_id}] FENCE INTRUDER PLATE DETECTED: plate='{res.plate_text}' "
                    f"vehicle={class_name} track=#{track_id} "
                    f"confidence={res.ocr_confidence:.2f} status={res.validation_status}"
                )

        return results

