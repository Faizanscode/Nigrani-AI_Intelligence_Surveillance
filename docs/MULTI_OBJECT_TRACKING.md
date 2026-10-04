# Multi-Object Tracking (Step 4)

This module implements persistent tracking of YOLO detections using Ultralytics' ByteTrack logic, providing each detected object with a persistent `track_id` over time.

## Architecture

We implemented a separated tracking layer that bridges the gap between raw YOLO detections and downstream analytics.

```
CameraPipeline
  -> frame
  -> YOLODetector -> List[DetectionResult]
  -> ByteTrackTracker -> List[TrackResult] (contains track_id, trajectory)
```

The tracker isolates its state per camera (`camera_id`). It retains the `track_id` for each object as it moves through the frame, and stores a trailing history of its positions (`trajectory`) up to a specified length.

## Selected Tracker: ByteTrack

**Why ByteTrack?**
- ByteTrack efficiently uses bounding box overlap (IOU) and confidence scores to associate detections across frames without requiring deeply embedded feature extraction networks.
- It operates natively on CPU with minimal latency penalty.
- It integrates seamlessly with Ultralytics logic. 

Our implementation (`ByteTrackTracker`) provides an adapter (`_MockResults`) that wraps our custom `DetectionResult` models into the data structure expected by `ultralytics.trackers.byte_tracker.BYTETracker`. This fulfills the requirement of decoupling detection from tracking while reusing reliable internal tracking algorithms.

## TrackResult Schema
```json
{
    "track_id": 1,
    "class_id": 0,
    "class_name": "person",
    "confidence": 0.89,
    "bbox": {
        "x1": 100, "y1": 100, "x2": 200, "y2": 300,
        "center_x": 150, "center_y": 200,
        "width": 100, "height": 200
    },
    "trajectory": [[150, 200], [152, 205]],
    "frames_seen": 2
}
```

## Configuration
Added to `.env`:
- `TRACKER_TYPE`: `bytetrack`
- `TRACKER_TRACK_BUFFER`: The number of frames an object is kept in memory (lost state) before being permanently dropped. Default `30`.
- `TRACKER_MATCH_THRESHOLD`: Threshold for assigning tracking matches. Default `0.80`.
- `TRACK_HISTORY_LENGTH`: The number of historical points saved in `trajectory` to form a path. Default `30`.

## API Integration
Exposes `GET /api/v1/cameras/{camera_id}/tracks` to retrieve the latest tracked objects in real-time.

## Visualization
The `TrackVisualizer` draws distinct colors per `track_id`, showing the label (e.g. `person #1 0.89`) and a short tail tracing its trajectory path.

## Limitations
- Tracker relies heavily on frame rate. If frames drop substantially, objects might swap IDs.
- Tracks are cleared when the pipeline restarts; cross-session persistence is not implemented yet.
