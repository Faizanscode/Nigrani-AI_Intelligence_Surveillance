# Video Ingestion Pipeline (Phase 1)

## Overview
The video ingestion module provides a robust, asynchronous pipeline for reading frames from various sources (files, webcams, RTSP streams), throttling them to a configured frame rate, and safely placing them in a bounded queue for downstream AI processing.

## Architecture
- **`BaseVideoSource`**: Abstract interface defining how to connect, read frames, check status, and release resources.
- **Implementations**:
  - `FileVideoSource`: For `.mp4`, `.avi`, etc.
  - `WebcamVideoSource`: For local USB/integrated webcams.
  - `RTSPVideoSource`: For IP CCTV cameras. Includes automatic reconnection logic if the stream drops.
- **`CameraPipeline`**: Manages a background thread per camera. Reads frames from the source, drops excess frames to match `PROCESS_FPS`, and pushes frames to a thread-safe `queue.Queue`.
- **`CameraManager`**: A singleton service in the FastAPI backend that orchestrates starting/stopping pipelines and tracking health metrics.

## Configuration
Key settings are managed via the `.env` file:
- `PROCESS_FPS`: Target frames per second to process. E.g., `10`. This prevents overwhelming the AI pipeline.
- `FRAME_QUEUE_SIZE`: Maximum frames to keep in memory before dropping oldest frames. E.g., `30`.

## Testing
Run the automated tests using Pytest:
```bash
set PYTHONPATH=.
pytest tests/test_ingestion.py -v
```

To manually verify, you can generate a synthetic test video:
```bash
set PYTHONPATH=.
python scripts/generate_test_video.py
```
And then run the FastAPI server:
```bash
set PYTHONPATH=.
uvicorn backend.app.main:app --reload
```
You can then add a camera via `POST /api/v1/cameras` and start it via `POST /api/v1/cameras/{id}/start`.

## Camera Health Monitoring
The API provides detailed health metrics for each camera stream, accessible via `GET /api/v1/cameras/{id}/status`.
Metrics tracked include:
- `is_connected`: Whether the source is currently reachable.
- `frames_received`: Total frames pulled from the source.
- `frames_processed`: Frames successfully enqueued.
- `current_fps`: Calculated processing FPS.
- `errors`: Count of dropped frames or read errors.
- `queue_size`: Current backlog of frames.
