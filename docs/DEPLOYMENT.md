# Production Docker Deployment Guide: Nigrani AI

This document provides complete instructions for building, running, and deploying the **Nigrani AI — Intelligent Surveillance** backend in containerized environments.

---

## 1. Architecture & Design Principles

- **Runtime**: Python 3.11-slim Linux container.
- **Web Framework**: FastAPI served by Uvicorn (production multi-threaded, reload disabled).
- **AI Engines**:
  - **Object Detection**: Ultralytics YOLO11 (`yolo11n.pt` baked into image at `/app/yolo11n.pt` or mounted).
  - **Tracking**: ByteTrack multi-object tracker.
  - **ANPR**: OpenCV contour processing + EasyOCR (OCR models pre-cached in image at `/root/.EasyOCR/`).
  - **Face Recognition**: dlib + `face-recognition` with pre-computed embeddings registry.
  - **Behavior Analysis**: Loitering detection, night movement monitoring, and spatio-temporal incident correlation.
- **Storage Layer**: Lightweight, persistent file and JSON storage (`/app/data/`):
  - Cameras: `/app/data/cameras.json`
  - Fences: `/app/data/fences.json`
  - Face Registry: `/app/data/face_registry.json`
  - Video Sources: `/app/data/videos/`
  - Evidence Snaps: `/app/data/evidence/` (served statically at `/api/v1/evidence/`)
- **No Database Dependency**: The backend does NOT use PostgreSQL; all state is preserved via host volume mounts to `./data`.

---

## 2. Dependency Resolution Details

- **PyTorch 2.14.1** declares a requirement for `setuptools>=77.0.3`.
- **`face_recognition_models`** relies on `pkg_resources` to locate its landmark and ResNet `.dat` files.
- `setuptools` completely removed `pkg_resources` in version `82.0.0`.
- **Solution**: The Docker environment installs `setuptools>=77.0.3,<81`. This simultaneously satisfies PyTorch's `>=77.0.3` requirement while retaining `pkg_resources` for face recognition models without conflict.
- **PyTorch CPU Wheel**: The Dockerfile pulls CPU-specific wheels (`--index-url https://download.pytorch.org/whl/cpu`) to keep image sizes compact (~1.5GB total instead of ~6GB with unused CUDA bundles).

---

## 3. Directory & Video Path Mapping

### Local vs Container Video Storage
When adding pre-recorded file cameras, video files must be placed inside the project's `data/videos/` folder.

- **Host Path**: `D:\BSVIS\data\videos\sample.mp4`
- **Container Path**: `/app/data/videos/sample.mp4`
- **Config Path in `cameras.json`**: `"data/videos/sample.mp4"` or simply `"sample.mp4"`

The `FileVideoSource` engine automatically strips Windows path prefixes and resolves filenames against `/app/data/videos/` and `data/videos/`.

---

## 4. Frontend Integration

The frontend is a Vite + React application in `frontend/`.

### How Frontend Connects to Container Backend
1. In `frontend/src/services/api.js`:
   ```javascript
   export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
   ```
2. When deploying the frontend, configure the backend address via `.env.production` or CI/CD environment variables:
   ```env
   VITE_API_BASE_URL=https://api.yourdomain.com/api/v1
   ```
3. In the backend container environment, set `FRONTEND_URL` to allow CORS requests:
   ```env
   FRONTEND_URL=https://dashboard.yourdomain.com
   ```

---

## 5. Local Docker Testing

### Prerequisites
- Docker Engine / Docker Desktop (version 24+)
- Docker Compose (v2.20+)

### Step-by-Step Commands

1. **Prepare Environment File**:
   ```bash
   cp .env.example .env
   ```

2. **Validate Compose Configuration**:
   ```bash
   docker compose config
   ```

3. **Build the Container Image**:
   ```bash
   docker compose build
   ```

4. **Start the Container**:
   ```bash
   docker compose up -d
   ```

5. **Check Container Logs**:
   ```bash
   docker compose logs -f backend
   ```

6. **Check Health Status**:
   ```bash
   docker inspect --format='{{json .State.Health.Status}}' nigrani_backend
   ```
   Or via curl:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
   Expected response:
   ```json
   {"status":"healthy","cameras_configured":10,"pipelines_running":0}
   ```

7. **Stop Container**:
   ```bash
   docker compose down
   ```

---

## 6. Remote / Cloud Build & Deployment

### Tagging Strategy
Replace `<REGISTRY>` and `<TAG>` with your specific registry (e.g. AWS ECR, GCP Artifact Registry, or Docker Hub) and version tag (e.g. `v1.0.0` or `latest`):
- Docker Hub: `yourusername/nigrani-backend:v1.0.0`
- AWS ECR: `<aws_account_id>.dkr.ecr.<region>.amazonaws.com/nigrani-backend:v1.0.0`
- GCP Artifact Registry: `<region>-docker.pkg.dev/<project_id>/nigrani/backend:v1.0.0`

### Option A: Docker Hub
```bash
# 1. Login to Docker Hub
docker login

# 2. Build for Linux AMD64 target
docker build --platform linux/amd64 -t yourusername/nigrani-backend:latest .

# 3. Push image
docker push yourusername/nigrani-backend:latest
```

### Option B: AWS ECR
```bash
# 1. Authenticate with ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com

# 2. Build for Linux AMD64
docker build --platform linux/amd64 -t <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/nigrani-backend:latest .

# 3. Push image
docker push <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/nigrani-backend:latest
```

### Option C: Google Cloud Artifact Registry
```bash
# 1. Authenticate Docker with gcloud
gcloud auth configure-docker us-central1-docker.pkg.dev

# 2. Build for Linux AMD64
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/my-project/nigrani/backend:latest .

# 3. Push image
docker push us-central1-docker.pkg.dev/my-project/nigrani/backend:latest
```

---

## 7. Cloud Server Deployment (Ubuntu / Debian VM)

On your remote production server (e.g. AWS EC2, GCP Compute Engine, DigitalOcean Droplet):

1. **Install Docker & Docker Compose Plugin**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-v2
   sudo systemctl enable --now docker
   ```

2. **Create Project Directory & Persistent Data Directory**:
   ```bash
   mkdir -p /opt/nigrani/data/videos /opt/nigrani/data/evidence
   cd /opt/nigrani
   ```

3. **Deploy `docker-compose.yml` and `.env`**:
   Copy `docker-compose.yml` and configured `.env` to `/opt/nigrani/`.
   In `docker-compose.yml`, reference your remote image:
   ```yaml
   image: yourusername/nigrani-backend:latest
   ```

4. **Launch the Container**:
   ```bash
   docker compose up -d
   ```

5. **Verify Running State & Health**:
   ```bash
   docker ps
   docker compose logs -f backend
   ```
