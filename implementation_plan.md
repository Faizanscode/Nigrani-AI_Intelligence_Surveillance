# Multi-Object Tracking (Step 4)

This plan details how we will integrate persistent object tracking using ByteTrack, satisfying the strict requirement to decouple the Tracker from YOLO while reusing Ultralytics' tracker logic.

## Goal
To implement a tracker layer that consumes `DetectionResult` objects from the pipeline, applies ByteTrack association, and returns `TrackResult` objects with persistent IDs, bounding boxes, and trajectory history per camera.

## Architecture & Integration

- **Models (`ai_engine/tracking/models.py`)**: Define `TrackResult` and `TrajectoryPoint`.
- **Tracker Interface (`ai_engine/tracking/tracker.py`)**: Abstract base class `BaseTracker`.
- **ByteTrack Implementation (`ai_engine/tracking/bytetrack.py`)**: We will select **ByteTrack** over BoT-SORT because it provides excellent performance on CPU and associates bounding boxes cleanly without requiring deeply embedded feature extraction maps, fitting our requirement for decoupled `DetectionResult -> TrackResult` architecture.
    - We will write a lightweight adapter that converts our domain `DetectionResult` into a format that `ultralytics.trackers.byte_tracker.BYTETracker` can digest. This way, we decouple YOLO from tracking but still leverage Ultralytics' robust ByteTrack algorithm.
- **Pipeline Integration (`ai_engine/pipeline.py`)**: 
    - The pipeline will initialize a `ByteTrackTracker` per camera.
    - The `_detection_loop` thread will pass `frame` and `DetectionResult` to `tracker.update()`.
    - It will attach `TrackResult` objects to the frame metadata.

## Configuration Changes
Add tracking variables to `.env` and `config.py`:
- `TRACKER_TYPE`: `bytetrack`
- `TRACKER_TRACK_BUFFER`: `30`
- `TRACKER_MATCH_THRESHOLD`: `0.80`
- `TRACK_HISTORY_LENGTH`: `30`

## Proposed Changes

### 1. Data Models
Create `TrackResult` wrapping the existing detection plus tracking data.
```python
class TrackResult(BaseModel):
    track_id: int
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox # from Step 3
    trajectory: List[Tuple[int, int]] # history of center points
    frames_seen: int
```

### 2. Tracker Logic
- Ensure isolated tracker instances per camera.
- The `ByteTrackTracker` wraps Ultralytics `BYTETracker`. It will map `DetectionResult` lists to a mocked result matrix, invoke the BYTETracker, and then extract the persistent track IDs back into `TrackResult`.

### 3. Pipeline Integration
`pipeline.py`:
- Create `tracker = TrackerFactory.create(settings.TRACKER_TYPE)` in `__init__`.
- Within the detection loop:
  ```python
  detections = self.detector.detect(frame)
  tracks = self.tracker.update(detections, frame)
  ```
- Send annotated frames downstream displaying track IDs and short trails.

### 4. Visualization 
Update `DetectionVisualizer` to `TrackVisualizer`. It will draw the track ID and a fading line representing the object's recent trajectory.

### 5. API Update
Add `GET /api/v1/cameras/{camera_id}/tracks` that pulls the latest `TrackResult` metadata from the output queue.

## Verification Plan
### Unit Tests
- Create `tests/test_tracking.py`:
    - `test_tracker_initialization()`
    - `test_synthetic_association()`: Feed deterministic bounding boxes over sequential frames to ensure same `track_id` is maintained.
    - `test_per_camera_isolation()`: Ensure separate cameras assign independent IDs.
    - `test_track_history_limit()`: Check `TRACK_HISTORY_LENGTH`.

### Validation
- Run existing Step 2 and Step 3 tests.
- Launch the pipeline and inspect `outputs/detections/` to confirm objects have `person #1` identifiers and persistent paths.

## Open Questions
> [!NOTE]
> None at the moment. ByteTrack is standard and highly performant. If you agree with using the Ultralytics ByteTrack algorithm bridged to our custom data models, I will proceed.
