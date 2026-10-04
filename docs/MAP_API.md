# MAP-01: National Border Camera Map API

This document details the new backend API support for the National Border Camera Surveillance Map.

## Endpoints

### 1. `GET /api/v1/cameras/map`

Returns a list of all registered cameras, enriched with their geographic metadata and real-time operational status.

**Query Parameters (Optional):**
- `status` (str): Filter by status (`ACTIVE ALERT`, `ONLINE`, `OFFLINE`)
- `border_sector` (str): Filter by border sector (e.g., `NORTH-01`)
- `border_state` (str): Filter by state (e.g., `Punjab`)
- `border_region` (str): Filter by region (e.g., `WEST`)

**Response:**
```json
[
  {
    "id": "CAM-DEMO-001",
    "name": "North Sector Demo 1",
    "type": "rtsp",
    "url": "rtsp://demo/fake/stream",
    "latitude": 34.0,
    "longitude": 74.8,
    "border_sector": "NORTH-01",
    "border_state": "Jammu and Kashmir",
    "border_region": "NORTH",
    "bop_name": "BOP-DEMO-N",
    "status": "OFFLINE"
  }
]
```

#### Status Inference Logic
The `status` field is dynamically computed based on the underlying event engine:
- **`ACTIVE ALERT`**: The camera is currently running AND has at least one unacknowledged high/medium severity alert in the Event Engine.
- **`ONLINE`**: The camera is running and processing frames normally.
- **`OFFLINE`**: The camera's pipeline is stopped.

---

### 2. `POST /api/v1/cameras`

The camera creation endpoint has been updated to accept map metadata.

**Request Body:**
```json
{
  "name": "Custom Camera",
  "source": 0,
  "type": "webcam",
  "latitude": 30.5,
  "longitude": 75.0,
  "border_sector": "WEST-03",
  "border_state": "Punjab",
  "border_region": "WEST",
  "bop_name": "BOP-CUSTOM"
}
```

---

## Seed Data & Persistence

The project now features a `CameraStore` backed by `data/cameras.json`. 
When the backend starts for the very first time (or if the store is empty), it will automatically seed **4 demo cameras** located across different fictional border regions in India.

These demo cameras use a mock RTSP stream and will default to `OFFLINE` status. They are intended strictly for prototyping the frontend map interface in MAP-02. No real military or border coordinates have been used, following strict security constraints.
