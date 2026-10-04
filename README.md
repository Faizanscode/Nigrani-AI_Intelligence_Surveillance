# Nigrani AI — Intelligent Surveillance

Nigrani AI is an AI-powered software-defined surveillance platform designed to transform existing CCTV infrastructure into an intelligent real-time monitoring system.

Instead of requiring expensive dedicated smart cameras, FRS systems or proprietary surveillance hardware, the platform performs advanced video analytics through software.

## 1. Project Overview
Nigrani AI provides automated human and vehicle detection, virtual fence intrusion alerts, and specialized analytics purely through software, operating on any standard IP-based CCTV infrastructure.

## 2. Problem Statement
Border security forces and organizations rely on CCTV cameras at strategic locations. Conventional CCTV mainly provides live monitoring and recording, requiring continuous human observation. Advanced capabilities such as Facial Recognition, ANPR, intrusion detection, and object tracking often require specialized, expensive hardware and proprietary solutions.

## 3. Proposed Solution
Nigrani AI offers a software-defined surveillance platform that transforms standard IP-based CCTV infrastructure into an intelligent, AI-powered network. It executes specialized analytics purely through software, eliminating the need for dedicated smart cameras.

## 4. Key Features
- **Real-Time Detection & Tracking**: Human and vehicle detection using YOLO and ByteTrack algorithms.
- **Virtual Fencing**: Customizable intrusion detection zones overlaid on camera feeds.
- **Face Recognition**: Detects and recognizes registered faces.
- **ANPR**: Automatic Number Plate Recognition for vehicles.
- **Loitering Detection**: Detects suspicious loitering in specified zones.
- **Night Movement Detection**: Enhanced tracking and alerts during nighttime.
- **Live Dashboard**: Centralized React-based UI with WebSocket integration for real-time alerts.
- **Event Logging**: Comprehensive PostgreSQL database recording events, incidents, and snapshot evidence.

## 5. System Architecture
Nigrani AI separates heavy AI inference from the web backend. The backend serves a REST API and WebSockets to a React frontend, persisting events to a PostgreSQL database. 

## 6. AI Pipeline
```
CCTV / Video Source
        ↓
Video Ingestion
        ↓
YOLO Object Detection
        ↓
ByteTrack Tracking
        ↓
AI Analytics
        ├── Face Detection
        ├── Face Recognition
        ├── ANPR
        ├── Virtual Fence
        ├── Loitering Detection
        └── Night Movement
        ↓
Event Engine
        ↓
Alert Manager
        ↓
Multi-Camera Correlation
        ↓
Incident Management
        ↓
Dashboard / Alerts / Event History
```

## 7. Technology Stack
- **Frontend**: React, Vite, Leaflet, Tailwind CSS, JavaScript
- **Backend**: Python, FastAPI, Uvicorn, SQLAlchemy, PostgreSQL
- **AI & Vision**: Ultralytics YOLOv8/YOLO11, ByteTrack, OpenCV, Face Recognition, ANPR

## 8. Project Structure
```
Nigrani-AI/
├── ai_engine/          # Core AI, detection, tracking, analytics
├── backend/            # FastAPI backend, DB models, APIs, WebSocket
├── data/               # Local data storage, uploaded evidence
├── docs/               # Technical documentation
├── frontend/           # React + Vite frontend application
├── scripts/            # Utility and testing scripts
├── tests/              # Pytest test suite
├── README.md           # Project documentation
├── .gitignore          # Git ignore configuration
└── .env.example        # Environment variables template
```

## 9. Installation
*Ensure Python 3.9+ and Node.js are installed. For GPU acceleration, CUDA must be properly configured.*

1. Clone the repository
2. Set up backend and frontend separately as below.

## 10. Backend Setup
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
# Start the backend server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 11. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 12. Environment Variables
Copy `.env.example` to `.env` and fill in the required details (e.g., database URL, model configuration, API keys). Never commit `.env` to the repository.

## 13. Running the Application
Ensure the database is running and accessible. Start both the backend (FastAPI/Uvicorn) and the frontend (React/Vite). The web UI will be accessible at `http://localhost:5173`.

## 14. Supported Video Sources
Supports local MP4 files (for prototyping and testing) and RTSP IP streams (for production surveillance).

## 15. AI Modules
- **YOLO Detection**: Real-time object bounding boxes.
- **ByteTrack**: Multi-object tracking across frames.
- **Specialized Analyzers**: Face Recognition, ANPR, Virtual Fence, Loitering, and Night Movement.

## 16. Event & Alert Engine
Filters frame-level detections into discrete, actionable events (e.g., "Person crossed fence"). Triggers real-time alerts distributed via WebSockets.

## 17. Evidence Capture
Automatically saves snapshot images of incidents and stores metadata/timestamps for later review in the event history dashboard.

## 18. Multi-Camera Threat Correlation
Analyzes events across multiple camera feeds to identify correlated threats or tracking a single entity moving through different zones.

## 19. Camera Map
Leaflet-based interactive map visualizing camera locations, statuses, active alerts, and virtual fencing configurations.

## 20. Performance Optimization
Adjustable frame processing rate (`PROCESS_FPS`) and buffer queuing to handle heavy inference workloads without breaking the ingestion pipeline.

## 21. Screenshots
*(To be added)*

## 22. Future Scope
- Integration with external VMS (Video Management Systems).
- Advanced PTZ (Pan-Tilt-Zoom) camera control from the dashboard.
- Further hardware acceleration optimizations (TensorRT).

## 23. Disclaimer
This software is intended for authorized surveillance and security purposes only. Ensure compliance with local privacy laws and regulations regarding video monitoring and facial recognition.

## 24. License
[Add License Information Here]
