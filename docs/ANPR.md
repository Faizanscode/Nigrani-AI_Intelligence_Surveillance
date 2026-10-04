# Step 8: Automatic Number Plate Recognition (ANPR)

This document describes the ANPR architecture integrated into the IBVAP pipeline.

## Pipeline Integration
The ANPR system operates asynchronously on the `CameraPipeline`'s frame processing loop. 

`Camera Frame` -> `Vehicle Tracker` -> `Plate Detector (Mock)` -> `OCR (Mock)` -> `Temporal Aggregation` -> `ANPR Result`

By operating downstream of the tracker, the ANPR system associates plates directly with existing vehicle `track_id`s, allowing it to aggregate readings over time without needing to run OCR on every frame or perform redundant object tracking.

## Components
- **PlateDetector**: Currently mocked (`MockPlateDetector`) to avoid large model downloads during prototyping. It simulates finding a bounding box within the lower section of a detected vehicle.
- **OCREngine**: Currently mocked (`MockOCREngine`). It generates a noisy string that fluctuates per frame but centers around a seeded license plate based on the `track_id`.
- **TemporalAggregator**: Collects OCR readings for a specific `track_id`. It counts occurrences and weights by confidence to determine the most stable reading. It also enforces a cooldown to prevent spamming events for a stationary vehicle.
- **PlateValidator**: Uses regular expressions to validate standard Indian registration plate formats (e.g., `CG04AB1234`). It returns `VALID`, `INVALID`, or `UNKNOWN`.

## API Endpoints
- `GET /api/v1/anpr`: Returns the most recent 50 ANPR records across all cameras.
- `GET /api/v1/anpr?camera_id=...`: Filters by camera.

## Dashboard Integration
The dashboard connects via WebSockets to listen for `NEW_ANPR` events. The `DashboardOverview` component features an ANPR column that displays the latest recognized plates, their validation status, and OCR confidence in real-time.
