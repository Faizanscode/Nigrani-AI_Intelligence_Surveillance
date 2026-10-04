# API Specification

Base URL: `/api/v1`

## Authentication

### `POST /auth/login`
- **Purpose**: Authenticate user and return JWT.
- **Request Body**: 
  ```json
  { "username": "admin", "password": "password" }
  ```
- **Response** (200 OK):
  ```json
  { "access_token": "jwt.token.string", "token_type": "bearer" }
  ```

## Cameras

### `GET /cameras`
- **Purpose**: List all configured cameras.
- **Response** (200 OK):
  ```json
  [
    { "id": "uuid", "name": "BOP Gate 1", "source": "rtsp://...", "status": "active" }
  ]
  ```

### `POST /cameras`
- **Purpose**: Add a new camera to the system.
- **Request Body**:
  ```json
  { "name": "BOP Gate 2", "source": "/data/videos/test.mp4", "type": "file" }
  ```
- **Response** (201 Created): Camera object.

### `GET /cameras/{id}/status`
- **Purpose**: Get current operational status, fps, and AI engine state for a camera.

## Zones / Virtual Fences

### `GET /cameras/{id}/zones`
- **Purpose**: Get defined polygons for analytics.
- **Response** (200 OK):
  ```json
  [
    { "id": "uuid", "name": "Fence A", "zone_type": "intrusion", "coordinates": [[10, 10], [10, 50], [50, 50], [50, 10]] }
  ]
  ```

### `PUT /cameras/{id}/zones`
- **Purpose**: Update virtual fence coordinates.

## Events & Alerts

### `GET /events`
- **Purpose**: Fetch paginated event history.
- **Query Params**: `page`, `limit`, `camera_id`, `event_type`
- **Response** (200 OK):
  ```json
  {
    "total": 100,
    "events": [
      { "id": "uuid", "type": "intrusion", "timestamp": "...", "snapshot_url": "..." }
    ]
  }
  ```

### `PUT /events/{id}/acknowledge`
- **Purpose**: Mark an alert as reviewed by an operator.
- **Request Body**: `{ "notes": "False alarm" }` (optional)

## Video Streams

### `GET /streams/{id}`
- **Purpose**: MJPEG stream endpoint for frontend viewing. Serves `multipart/x-mixed-replace` image frames.

## Analytics Data

### `GET /stats/detections`
- **Purpose**: Get aggregated detection statistics for charts (e.g., number of vehicles per hour).

## System Health

### `GET /health`
- **Purpose**: System liveness probe.

## WebSockets

### `WS /ws/alerts`
- **Purpose**: Real-time alert delivery.
- **Event Format** (JSON message sent from server to client):
  ```json
  {
    "event_id": "uuid",
    "type": "INTRUSION",
    "camera_id": "uuid",
    "camera_name": "BOP Gate 1",
    "timestamp": "2026-09-06T12:00:00Z",
    "description": "Person crossed Zone A",
    "snapshot_url": "/api/v1/media/snapshots/evt_123.jpg",
    "metadata": {
      "object_type": "person",
      "confidence": 0.88,
      "track_id": 45
    }
  }
  ```
