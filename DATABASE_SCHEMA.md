# Database Schema

The database uses PostgreSQL. SQLAlchemy will manage ORM models and Alembic will handle migrations.

## `users`
- **id**: UUID (Primary Key)
- **username**: VARCHAR(50) (Unique, Indexed)
- **password_hash**: VARCHAR(255)
- **role**: VARCHAR(20) ('admin', 'operator')
- **is_active**: BOOLEAN (Default True)
- **created_at**: TIMESTAMP (Default NOW())

## `cameras`
- **id**: UUID (Primary Key)
- **name**: VARCHAR(100)
- **source_url**: VARCHAR(255) (Path or RTSP URL)
- **camera_type**: VARCHAR(20) ('rtsp', 'file', 'webcam')
- **is_active**: BOOLEAN (Default True)
- **created_at**: TIMESTAMP (Default NOW())

## `camera_zones`
- **id**: UUID (Primary Key)
- **camera_id**: UUID (Foreign Key -> `cameras.id`, Cascade Delete)
- **name**: VARCHAR(100)
- **zone_type**: VARCHAR(50) ('intrusion', 'loitering', 'ignore')
- **coordinates**: JSONB (Array of [x, y] points defining a polygon)
- **created_at**: TIMESTAMP

## `events`
- **id**: UUID (Primary Key)
- **camera_id**: UUID (Foreign Key -> `cameras.id`)
- **event_type**: VARCHAR(50) ('intrusion', 'loitering', 'suspicious', 'anpr')
- **severity**: VARCHAR(20) ('low', 'medium', 'high', 'critical')
- **timestamp**: TIMESTAMP (Indexed for fast chronological querying)
- **snapshot_path**: VARCHAR(255)
- **is_acknowledged**: BOOLEAN (Default False)
- **acknowledged_by**: UUID (Foreign Key -> `users.id`, Nullable)
- **created_at**: TIMESTAMP

## `vehicles`
- **id**: UUID (Primary Key)
- **event_id**: UUID (Foreign Key -> `events.id`, Cascade Delete)
- **vehicle_type**: VARCHAR(50) ('car', 'truck', 'bike')
- **color**: VARCHAR(30) (Nullable)

## `license_plates`
- **id**: UUID (Primary Key)
- **vehicle_id**: UUID (Foreign Key -> `vehicles.id`, Cascade Delete)
- **plate_text**: VARCHAR(20) (Indexed)
- **confidence**: FLOAT
- **ocr_timestamp**: TIMESTAMP

## `faces`
- **id**: UUID (Primary Key)
- **event_id**: UUID (Foreign Key -> `events.id`, Cascade Delete)
- **person_name**: VARCHAR(100) (Nullable, if recognized)
- **embedding**: VECTOR(512) (Using pgvector, Nullable)
- **confidence**: FLOAT

## `system_logs`
- **id**: UUID (Primary Key)
- **level**: VARCHAR(20) ('INFO', 'WARNING', 'ERROR')
- **source_module**: VARCHAR(50)
- **message**: TEXT
- **timestamp**: TIMESTAMP (Indexed)
