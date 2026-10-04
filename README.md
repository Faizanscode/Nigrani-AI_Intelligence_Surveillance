# IBVAP – Intelligent Border Video Analytics Platform

## Problem Statement
Border security forces rely on CCTV cameras at strategic locations. Conventional CCTV mainly provides live monitoring and recording, requiring continuous human observation. Advanced capabilities such as Facial Recognition, ANPR, intrusion detection, and object tracking often require specialized, expensive hardware and proprietary solutions.

## Proposed Solution
IBVAP is a software-defined surveillance platform that transforms standard IP-based CCTV infrastructure into an intelligent, AI-powered network. It provides automated human/vehicle detection, virtual fence intrusion alerts, and specialized analytics purely through software, without requiring dedicated smart cameras.

## Key Features
- **Real-Time Detection & Tracking**: Human and vehicle detection using YOLO and tracking algorithms.
- **Virtual Fencing**: Customizable intrusion detection zones overlaid on camera feeds.
- **Specialized Analytics**: Extensible architecture for ANPR, Loitering, and Face Recognition.
- **Live Dashboard**: Centralized React-based UI with WebSocket integration for real-time alerts.
- **Agnostic Ingestion**: Supports recorded MP4s (for prototyping) and standard RTSP IP streams (for production).
- **Event Logging**: Comprehensive PostgreSQL database recording events and snapshot evidence.

## Architecture Overview
IBVAP separates heavy AI inference (OpenCV, YOLO, ByteTrack) from the web backend (FastAPI). The backend serves a REST API and WebSockets to a React frontend, persisting events to a PostgreSQL database. The AI Engine operates as a pipeline: Ingestion -> Detection -> Tracking -> Analytics -> Alerting.

## Technology Stack
- **Frontend**: React, Vite, Tailwind CSS
- **Backend**: Python, FastAPI
- **Computer Vision / AI**: OpenCV, Ultralytics YOLOv8, ByteTrack (or similar)
- **Database**: PostgreSQL, SQLAlchemy
- **Real-time**: WebSockets

## Current Development Status
- Phase: **Architecture & Planning**
- Note: Implementation has not yet begun.

## Future Roadmap
Refer to `DEVELOPMENT_PLAN.md` for the detailed 11-phase implementation roadmap, progressing from basic video ingestion to advanced complex event processing.

## Setup Instructions
*(Placeholder: Setup instructions will be provided once Phase 1 development commences.)*
