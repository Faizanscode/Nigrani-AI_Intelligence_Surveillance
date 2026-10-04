# System Configuration

Configuration is managed via Environment Variables (`.env` file) to ensure security, prevent hard-coding, and allow flexibility across development, staging, and production (or edge vs. central) environments.

## Database Configuration
- `DATABASE_URL`: Full connection string (e.g., `postgresql+asyncpg://admin:password@localhost:5432/ibvap`)

## Application Server
- `API_PORT`: Integer (e.g., `8000`)
- `API_HOST`: String (e.g., `0.0.0.0`)
- `ENVIRONMENT`: String (`development`, `production`)
- `LOGGING_LEVEL`: String (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

## Security
- `JWT_SECRET_KEY`: String (Randomly generated key for token signing)
- `JWT_ALGORITHM`: String (e.g., `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Integer (e.g., `1440`)
- `CORS_ORIGINS`: Comma-separated list of allowed frontend URLs (e.g., `http://localhost:5173`)

## File Storage
- `SNAPSHOT_STORAGE_PATH`: Absolute path to save event images (e.g., `/app/data/snapshots/` or `C:\ibvap\data\snapshots`)
- `VIDEO_TEST_DIR`: Path to sample MP4s for prototyping.

## AI & Models
- `YOLO_MODEL_PATH`: Path to the `.pt` weights file.
- `DETECTION_CONFIDENCE_THRESHOLD`: Float (e.g., `0.5`).
- `TRACKER_TYPE`: String (`bytetrack`, `sort`, `botsort`).
- `ENABLE_ANPR`: Boolean (`True`/`False` to toggle module loading).
- `ENABLE_FRS`: Boolean (`True`/`False` to toggle module loading).
- `AI_PROCESSING_FPS`: Integer (e.g., `15` - limit processing FPS to save CPU, dropping intermediate frames).

## Rules & Alerts
- `ALERT_COOLDOWN_SECONDS`: Minimum time between alerts for the same event type / track ID (e.g., `30`).
- `NIGHT_MODE_START`: Time string (e.g., `18:00`).
- `NIGHT_MODE_END`: Time string (e.g., `06:00`).

*(Note: Actual secrets like passwords and keys should never be committed to source control. A `.env.example` file should be provided with dummy values).*
