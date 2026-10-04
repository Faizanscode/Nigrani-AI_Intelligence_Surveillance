# Testing Strategy

Testing ensures stability and accuracy across the complex pipeline from video ingestion to UI alerts.

## 1. AI Modules (Unit Testing)
- **Objective**: Ensure detectors, trackers, and analyzers output correct formats and fire on expected conditions.
- **Strategy**: 
  - **Detectors**: Feed static, known images (with ground truth boxes) into `ObjectDetector` and assert the output bounding boxes and classes.
  - **Analyzers**: Feed mock `TrackedObject` data (simulating movement) into `IntrusionAnalyzer` and assert event triggers when coordinates cross the mock polygon.
- **Tools**: Pytest, Mocking.

## 2. Backend APIs
- **Objective**: Validate REST CRUD operations, authentication, and response formats.
- **Strategy**: 
  - Use `TestClient` from FastAPI.
  - Mock database sessions using an in-memory SQLite DB or isolated test PostgreSQL DB.
  - Verify HTTP status codes, JSON schemas, and error handling.
- **Tools**: Pytest, HTTPX.

## 3. Database
- **Objective**: Verify schema integrity, relationships, and cascades.
- **Strategy**: 
  - Apply Alembic migrations to a test DB.
  - Insert test records, assert foreign key constraints.
  - Verify cascade deletes (e.g., deleting an event deletes associated vehicles and faces).

## 4. WebSockets & Alert Generation
- **Objective**: Ensure real-time alerts are dispatched accurately and concurrently.
- **Strategy**: 
  - Pytest-asyncio to connect dummy WebSocket clients.
  - Inject mock events into the Alert Engine.
  - Verify reception, payload format, and speed by the clients.

## 5. Frontend
- **Objective**: Verify UI rendering, state management, and real-time updates.
- **Strategy**: 
  - Component-level testing for VideoPlayer, AlertCard.
  - Mock API responses (axios/fetch).
  - Mock WebSocket server to test real-time feed updates.
- **Tools**: Vitest, React Testing Library.

## 6. End-to-End (E2E)
- **Objective**: Validate the full pipeline from video file to UI alert.
- **Strategy**: 
  - Run the entire stack locally.
  - Feed a 10-second test video containing a known intrusion event.
  - Assert that an alert appears on the React dashboard within a reasonable latency limit.
- **Tools**: Playwright or Cypress.
