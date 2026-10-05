
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_DEVICE=cpu \
    ENVIRONMENT=production
    ENVIRONMENT=production \
    FACE_RECOGNITION_ENABLED=false

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

RUN pip install --upgrade pip && \
    pip install "setuptools>=77.0.3,<81"

# CPU-only PyTorch


COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Application source
COPY backend/ /app/backend/
COPY ai_engine/ /app/ai_engine/
COPY data/ /app/data/

# YOLO model
COPY yolo11n.pt /app/yolo11n.pt

# Runtime directories
RUN mkdir -p /app/data/videos /app/data/evidence

EXPOSE 8000

HEALTHCHECK --interval=60s \
    --timeout=10s \
    --start-period=120s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health').read()" || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]