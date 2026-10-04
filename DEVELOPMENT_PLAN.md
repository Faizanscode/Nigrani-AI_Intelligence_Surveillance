# IBVAP Development Roadmap

## Phase 1: Video Ingestion & Camera Abstraction
- **Objective:** Build the foundation for reading and serving video streams.
- **Features:** 
  - Camera configuration interface.
  - Reading MP4/Webcam using OpenCV.
  - Serving frames via MJPEG for basic viewing.
- **Files/modules expected:** `ai_engine/ingestion/video_streamer.py`, `backend/app/api/streams.py`
- **Dependencies:** OpenCV, FastAPI.
- **Inputs:** MP4 files, webcam.
- **Outputs:** Frame generators.
- **Testing requirements:** Verify frame rate, ensure no memory leaks on stream close.
- **Definition of done:** Stream can be viewed in browser via simple endpoint.

## Phase 2: Object Detection (Person & Vehicle)
- **Objective:** Integrate YOLO for basic object detection.
- **Features:**
  - YOLOv8 model loading.
  - Frame-by-frame inference for persons and vehicles.
  - Drawing bounding boxes on the output stream.
- **Files/modules expected:** `ai_engine/detection/yolo_detector.py`, `ai_engine/models/`
- **Dependencies:** Ultralytics YOLO, PyTorch.
- **Inputs:** Video frames.
- **Outputs:** Detections list (boxes, classes, confidences).
- **Testing requirements:** Unit tests for model inference, check detection on test images.
- **Definition of done:** Bounding boxes visible on MJPEG stream.

## Phase 3: Object Tracking
- **Objective:** Assign persistent IDs to objects.
- **Features:**
  - Integrate ByteTrack or similar tracker.
  - Maintain object history.
- **Files/modules expected:** `ai_engine/tracking/bytetrack_wrapper.py`
- **Dependencies:** ByteTrack/lap/filterpy.
- **Inputs:** Detections list, frames.
- **Outputs:** Tracked objects (persistent ID + box).
- **Testing requirements:** Verify IDs remain consistent across frames for moving objects.
- **Definition of done:** IDs displayed over objects in stream.

## Phase 4: Virtual Fence & Intrusion Detection
- **Objective:** Detect when tracked objects cross defined boundaries.
- **Features:**
  - Define polygon zones per camera.
  - Point-in-polygon logic.
  - Trigger intrusion events.
- **Files/modules expected:** `ai_engine/analytics/intrusion_analyzer.py`
- **Dependencies:** Shapely/OpenCV functions.
- **Inputs:** Tracked objects, zone coordinates.
- **Outputs:** Intrusion events.
- **Testing requirements:** Pass mock object paths over a polygon and assert trigger.
- **Definition of done:** Terminal logs "Intrusion detected" when object enters zone.

## Phase 5: Event and Alert Engine
- **Objective:** Manage events and broadcast alerts.
- **Features:**
  - Internal message queue or event bus.
  - WebSocket integration in FastAPI.
  - Snapshot capture on event.
- **Files/modules expected:** `backend/app/services/alert_engine.py`, `backend/app/api/websockets.py`
- **Dependencies:** websockets, asyncio.
- **Inputs:** Analyzer events.
- **Outputs:** WebSocket JSON messages, saved JPG files.
- **Testing requirements:** Mock WS clients receive alerts.
- **Definition of done:** Alerts received via WS client and snapshots saved to disk.

## Phase 6: PostgreSQL Database Integration
- **Objective:** Persist configuration and history.
- **Features:**
  - SQLAlchemy setup.
  - Models for users, cameras, events, zones.
  - CRUD APIs.
- **Files/modules expected:** `backend/app/db/models.py`, `backend/app/db/session.py`, `backend/alembic/`
- **Dependencies:** psycopg2, SQLAlchemy, Alembic.
- **Inputs:** API requests, Alert Engine logs.
- **Outputs:** DB records.
- **Testing requirements:** DB schema validation, CRUD endpoint tests.
- **Definition of done:** Events are saved and retrievable via API.

## Phase 7: React Surveillance Dashboard
- **Objective:** Build the frontend UI.
- **Features:**
  - Live video feeds.
  - Real-time alert sidebar (WebSockets).
  - Event history viewer.
- **Files/modules expected:** `frontend/src/pages/Dashboard.jsx`, `frontend/src/components/AlertFeed.jsx`
- **Dependencies:** React, Vite, Tailwind CSS, react-use-websocket.
- **Inputs:** User interaction, WS messages.
- **Outputs:** Rendered UI.
- **Testing requirements:** Component rendering, mock API hooks.
- **Definition of done:** Working visual dashboard connected to backend.

## Phase 8: ANPR (Automatic Number Plate Recognition)
- **Objective:** Detect and read license plates.
- **Features:** Plate detection model, OCR integration.
- **Files/modules expected:** `ai_engine/analytics/anpr_analyzer.py`
- **Dependencies:** EasyOCR/Tesseract.
- **Inputs:** Vehicle bounding box crops.
- **Outputs:** Plate text string.
- **Definition of done:** Text logged for detected cars.

## Phase 9: Loitering & Night Movement Detection
- **Objective:** Advanced behavioral analytics.
- **Features:** Time-in-zone tracking, low-light handling.
- **Files/modules expected:** `ai_engine/analytics/loitering_analyzer.py`
- **Definition of done:** Alert triggered after X seconds in zone.

## Phase 10: Face Detection & Recognition
- **Objective:** Identify individuals.
- **Features:** Face detection module, embedding matching.
- **Files/modules expected:** `ai_engine/analytics/face_analyzer.py`
- **Definition of done:** Faces cropped and compared.

## Phase 11: Suspicious Activity / Rule Engine
- **Objective:** Complex event processing.
- **Features:** Configurable rules combining multiple analytics.
- **Files/modules expected:** `backend/app/services/rule_engine.py`
- **Definition of done:** Complex rules trigger alerts.
