import threading
import queue
import time
from typing import Optional, Dict, Any
import numpy as np

from ai_engine.ingestion.source import BaseVideoSource
from ai_engine.detection.visualizer import DetectionVisualizer
from ai_engine.tracking.visualizer import TrackVisualizer
from backend.app.core.config import settings
from backend.app.core.event_bus import event_bus
from backend.app.core.logger import get_logger

logger = get_logger("CameraPipeline")


class CameraPipeline:
    """
    Manages the ingestion thread, frame rate throttling, and bounded queue
    for a single video source.

    Architecture:
    - _run_loop: reads frames at source FPS, always keeps latest_raw_frame updated
    - _detection_loop: picks up latest_raw_frame, runs AI pipeline, updates latest_frame
    - MJPEG stream: serves latest_frame directly

    This decouples streaming from AI processing so the stream is always live.
    """

    def __init__(self, source: BaseVideoSource, process_fps: int = 10, queue_size: int = 2):
        self.source = source
        self.process_fps = process_fps
        self.queue_size = queue_size

        # Single-slot queues - always has latest frame, never blocks
        self.frame_queue = queue.Queue(maxsize=self.queue_size)
        self.output_queue = queue.Queue(maxsize=self.queue_size)

        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.detection_thread: Optional[threading.Thread] = None
        self.detector = None
        self.tracker = None
        self.fence_engine = None
        self.anpr_engine = None
        self.behavior_engine = None
        self.face_engine = None

        # Health metrics
        self.frames_received = 0
        self.frames_processed = 0
        self.errors = 0
        self.last_successful_frame_time = 0.0
        self.start_time = 0.0
        self.total_detections = 0

        # Shared state for MJPEG streaming - always has the latest frame
        self.latest_frame = None       # Raw frame (no annotations) - always current
        self.latest_annotated_frame = None  # AI-annotated frame - updated when detection finishes
        self.latest_metadata = None

        # Pending normalized fence to install once source dimensions are known
        self._pending_normalized_fence = None
        self._frame_lock = threading.Lock()
        self.fence_intruder_tracks = set()
        self.face_recognition_events_emitted = set()

    def add_detector(self, detector):
        self.detector = detector
        if self.detector:
            self.detector.load_model()

    def add_tracker(self, tracker):
        self.tracker = tracker

    def add_fence_engine(self, engine):
        self.fence_engine = engine

    def add_anpr_engine(self, engine):
        self.anpr_engine = engine

    def add_behavior_engine(self, engine):
        self.behavior_engine = engine

    def add_face_engine(self, engine):
        self.face_engine = engine

    def start(self) -> bool:
        if self.is_running:
            logger.warning(f"[{self.source.source_id}] Pipeline is already running.")
            return True

        if not self.source.connect():
            logger.error(f"[{self.source.source_id}] Pipeline failed to start. Cannot connect to source.")
            return False

        self.is_running = True
        self.start_time = time.time()
        self.thread = threading.Thread(
            target=self._run_loop,
            name=f"Pipeline-{self.source.source_id}",
            daemon=True
        )
        self.thread.start()

        # Apply pending normalized fence now that we have real video dimensions
        self._apply_pending_fence()

        if self.detector:
            self.detection_thread = threading.Thread(
                target=self._detection_loop,
                name=f"Detector-{self.source.source_id}",
                daemon=True
            )
            self.detection_thread.start()

        logger.info(
            f"[{self.source.source_id}] Pipeline started. "
            f"Throttling to {self.process_fps} FPS. Queue size: {self.queue_size}"
        )
        return True

    def _apply_pending_fence(self):
        """If a saved normalized fence exists, convert to pixels and install it."""
        if not self._pending_normalized_fence or not self.fence_engine:
            return
        from ai_engine.analytics.fence.models import VirtualFence
        w = self.source.width or 1280
        h = self.source.height or 720
        nf = self._pending_normalized_fence
        abs_poly = nf.to_absolute(w, h)
        vf = VirtualFence(
            fence_id="custom_fence",
            camera_id=self.source.source_id,
            name=nf.name,
            description=nf.description or "",
            polygon=abs_poly,
            enabled=nf.enabled,
            target_classes=nf.target_classes,
        )
        self.fence_engine.fences.clear()
        self.fence_engine.track_states.clear()
        self.fence_engine.add_fence(vf)
        logger.info(
            f"[{self.source.source_id}] Applied custom fence '{nf.name}' "
            f"({len(abs_poly)} pts) at {w}x{h}"
        )
        self._pending_normalized_fence = None


    def stop(self) -> None:
        if not self.is_running:
            return

        logger.info(f"[{self.source.source_id}] Stopping pipeline...")
        self.is_running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)

        self.source.release()

        # Clear queues
        for q in [self.frame_queue, self.output_queue]:
            while not q.empty():
                try:
                    q.get_nowait()
                except queue.Empty:
                    break

        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=3.0)

        logger.info(f"[{self.source.source_id}] Pipeline stopped.")

    def _run_loop(self):
        """
        Reads frames from the source.
        Always stores the latest raw frame in self.latest_frame for streaming.
        Only puts frames into the detection queue at process_fps rate.
        """
        from ai_engine.ingestion.file_source import FileVideoSource

        frame_interval = 1.0 / self.process_fps if self.process_fps > 0 else 0.1
        last_process_time = time.time()
        last_loop_count = 0  # track video file loops

        is_file_source = isinstance(self.source, FileVideoSource)
        file_fps_interval = 1.0 / self.source.fps if self.source.fps > 0 else (1.0 / 30.0)
        last_read_time = time.time()

        while self.is_running:
            if is_file_source:
                now = time.time()
                elapsed_read = now - last_read_time
                if elapsed_read < file_fps_interval:
                    time.sleep(file_fps_interval - elapsed_read)
                    
            success, frame = self.source.read_frame()
            last_read_time = time.time()

            if not success:
                self.errors += 1
                if not self.source.is_connected:
                    logger.info(f"[{self.source.source_id}] Source disconnected or EOF. Exiting loop.")
                    self.is_running = False
                    break
                time.sleep(0.05)
                continue

            # Detect video file loop restart → clear tracker & fence state to prevent alert re-spam
            current_loop = getattr(self.source, 'loop_count', 0)
            if current_loop != last_loop_count:
                last_loop_count = current_loop
                logger.info(f"[{self.source.source_id}] Video looped (#{current_loop}). Clearing tracker & fence state.")
                if self.tracker:
                    try:
                        self.tracker.reset()
                    except Exception:
                        pass
                if self.fence_engine:
                    self.fence_engine.track_states.clear()
                self.fence_intruder_tracks.clear()
                self.face_recognition_events_emitted.clear()

            self.frames_received += 1
            self.last_successful_frame_time = last_read_time

            # Always store the latest raw frame for streaming
            with self._frame_lock:
                self.latest_frame = frame.copy()

            # Throttle sending to AI queue
            current_time = time.time()
            elapsed_process = current_time - last_process_time
            if elapsed_process >= frame_interval:
                last_process_time = current_time

                # Send to detection queue - drop frame if queue is full (non-blocking)
                metadata = {
                    "source_id": self.source.source_id,
                    "timestamp": current_time,
                    "width": self.source.width,
                    "height": self.source.height,
                }

                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()  # Drop oldest
                    except queue.Empty:
                        pass

                try:
                    self.frame_queue.put_nowait((frame, metadata))
                    self.frames_processed += 1
                except queue.Full:
                    pass  # Skip this frame if we still can't fit

    def _detection_loop(self):
        """
        AI processing loop: YOLO → Tracking → Fencing → ANPR → Behavior.
        Runs at whatever speed the CPU allows. Stores annotated frames.
        """
        import cv2
        import os
        from ai_engine.detection.visualizer import DetectionVisualizer

        os.makedirs("outputs/detections", exist_ok=True)
        frame_counter = 0

        while self.is_running:
            try:
                frame, metadata = self.frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # Run YOLO detection
            detections = self.detector.detect(frame)
            metadata["detections"] = detections
            self.total_detections += len(detections)

            # Run tracking
            tracks = []
            if self.tracker:
                tracks = self.tracker.update(detections, frame)
                metadata["tracks"] = tracks

            # Run virtual fencing
            active_intruders = None
            if self.fence_engine:
                fence_events = self.fence_engine.evaluate(tracks, metadata["timestamp"])
                metadata["events"] = fence_events
                metadata["fences"] = self.fence_engine.get_fences()
                metadata["fence_states"] = self.fence_engine.track_states.copy()
                for evt in fence_events:
                    logger.info(f"[{self.source.source_id}] Intrusion event: {evt.event_type} - {evt.object_class} #{evt.track_id}")
                    event_bus.publish("events.intrusion", evt)
                    self.fence_intruder_tracks.add(evt.track_id)

                # Collect active tracks currently inside any virtual fence
                for (f_id, t_id), state in self.fence_engine.track_states.items():
                    if state == "INSIDE":
                        self.fence_intruder_tracks.add(t_id)

                # Only restrict ANPR to fence intruders if virtual fences are active
                if self.fence_engine.get_fences():
                    active_intruders = self.fence_intruder_tracks

            # Run ANPR (focused on fence intruders)
            if self.anpr_engine:
                try:
                    anpr_results = self.anpr_engine.process(frame, tracks, metadata, active_intruders=active_intruders)
                    metadata["anpr"] = [r.model_dump() for r in anpr_results]
                    for r in anpr_results:
                        event_bus.publish("events.anpr", r.model_dump())
                except Exception as e:
                    logger.warning(f"[{self.source.source_id}] ANPR error: {e}")

            # Run Behavior Analysis (Loitering + Night Movement)
            if self.behavior_engine:
                try:
                    behavior_events = self.behavior_engine.evaluate(
                        self.source.source_id, tracks, metadata["timestamp"]
                    )
                    metadata["behavior"] = [evt.model_dump() for evt in behavior_events]
                    for evt in behavior_events:
                        logger.info(f"[{self.source.source_id}] Behavior event: {evt.event_type} - {evt.object_type} #{evt.track_id}")
                        event_bus.publish("events.behavior", evt)
                except Exception as e:
                    logger.warning(f"[{self.source.source_id}] Behavior engine error: {e}")

            # Run Face Recognition
            if self.face_engine:
                try:
                    face_results = self.face_engine.process(frame, tracks, metadata, active_intruders=active_intruders)
                    metadata["face_recognition"] = [r.model_dump() for r in face_results]
                    
                    # Deduplicate events by track_id
                    current_active_tracks = {t.track_id for t in tracks} if tracks else set()
                    
                    # Cleanup old tracks that are no longer active
                    self.face_recognition_events_emitted = {
                        tid for tid in self.face_recognition_events_emitted if tid in current_active_tracks
                    }

                    for r in face_results:
                        if r.status in ["RECOGNIZED", "UNKNOWN"]:
                            track_id = r.track_id
                            if track_id is not None:
                                if track_id not in self.face_recognition_events_emitted:
                                    event_bus.publish("events.face_recognition", r.model_dump())
                                    self.face_recognition_events_emitted.add(track_id)
                            else:
                                # Fallback if no track_id
                                event_bus.publish("events.face_recognition", r.model_dump())

                except Exception as e:
                    logger.warning(f"[{self.source.source_id}] Face recognition error: {e}")

            # Build annotated frame
            frame_counter += 1
            annotated = None
            try:
                if self.tracker and tracks:
                    from ai_engine.tracking.visualizer import TrackVisualizer
                    annotated = TrackVisualizer.draw_analytics(frame, metadata)
                elif detections:
                    annotated = DetectionVisualizer.draw_detections(frame, detections)
            except Exception as e:
                logger.warning(f"[{self.source.source_id}] Visualizer error: {e}")

            # Update latest annotated frame for streaming
            with self._frame_lock:
                self.latest_annotated_frame = annotated if annotated is not None else frame.copy()
                self.latest_metadata = metadata

            self.frame_queue.task_done()

    def get_stream_frame(self) -> Optional[np.ndarray]:
        """
        Returns the latest raw frame annotated with the latest available metadata.
        This allows the video to stream at source FPS while AI annotations update at AI FPS.
        """
        with self._frame_lock:
            if self.latest_frame is None:
                return None
            frame = self.latest_frame.copy()
            metadata = self.latest_metadata

        if metadata is not None:
            tracks = metadata.get("tracks")
            detections = metadata.get("detections")
            try:
                if self.tracker and tracks:
                    frame = TrackVisualizer.draw_analytics(frame, metadata)
                elif detections:
                    frame = DetectionVisualizer.draw_detections(frame, detections)
            except Exception:
                pass

        return frame

    def get_health(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_time if self.is_running else 0
        current_fps = self.frames_processed / uptime if uptime > 0 else 0

        health = {
            "is_running": self.is_running,
            "is_connected": self.source.is_open(),
            "frames_received": self.frames_received,
            "frames_processed": self.frames_processed,
            "current_fps": round(current_fps, 2),
            "errors": self.errors,
            "queue_size": self.frame_queue.qsize(),
            "last_frame_time": self.last_successful_frame_time,
        }

        if self.detector:
            health["output_queue_size"] = self.output_queue.qsize()
            health["total_detections"] = self.total_detections
            health["detector_metrics"] = self.detector.get_metrics()

        if self.tracker:
            health["tracker_active"] = True

        if self.fence_engine:
            health["fences_active"] = len(self.fence_engine.get_fences())

        return health
