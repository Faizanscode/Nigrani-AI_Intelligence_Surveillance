FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_DEVICE=cpu \
    ENVIRONMENT=production

# System dependencies for OpenCV, FFmpeg, dlib, EasyOCR and face recognition
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install setuptools version compatible with both PyTorch (>=77.0.3)
# and face_recognition_models (pkg_resources available in setuptools <82.0.0)
RUN pip install --upgrade pip && \
    pip install "setuptools>=77.0.3,<81"

# Install PyTorch CPU first to keep image lightweight and avoid multi-gigabyte CUDA packages
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download EasyOCR models (craft detector and english recognizer) into container image
# to ensure zero external network latency/failure on first inference at runtime
RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False)"

# Copy application source code and initial data configs
COPY backend/ /app/backend/
COPY ai_engine/ /app/ai_engine/
COPY data/ /app/data/

# Copy default YOLO model weights
COPY yolo11n.pt /app/yolo11n.pt

# Ensure persistent directories exist inside container
RUN mkdir -p /app/data/videos /app/data/evidence

EXPOSE 8000

# Healthcheck using standard library urllib (no external curl dependency needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health').read()" || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]