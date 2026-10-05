from contextlib import asynccontextmanager
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api import (
    cameras,
    health,
    fences,
    events,
    alerts,
    ws,
    anpr,
    settings as api_settings,
    face_recognition,
    incidents,
    system,
)
from backend.app.services.camera_manager import camera_manager
from backend.app.core.config import settings
from backend.app.core.logger import get_logger


logger = get_logger("Main")


# ============================================================
# Ensure evidence directory exists
# ============================================================

os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)


# ============================================================
# Evidence cleanup task
# ============================================================

async def cleanup_evidence_task():
    import asyncio
    import glob

    while True:
        try:
            evidence_dir = settings.EVIDENCE_DIR
            files = glob.glob(os.path.join(evidence_dir, "*.jpg"))

            # Keep only the newest 500 evidence images
            if len(files) > 500:
                files.sort(key=os.path.getmtime)

                for f in files[:-500]:
                    try:
                        os.remove(f)
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Error in evidence cleanup: {e}")

        await asyncio.sleep(300)  # Run every 5 minutes


# ============================================================
# Application lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    from backend.app.core.event_bus import event_bus

    # Startup
    loop = asyncio.get_running_loop()
    event_bus.set_main_loop(loop)

    cleanup_task = asyncio.create_task(
        cleanup_evidence_task()
    )

    logger.info(
        "Starting IBVAP Backend with event_bus linked to main event loop"
    )

    yield

    # Shutdown
    logger.info("Shutting down IBVAP Backend...")

    cleanup_task.cancel()

    camera_manager.stop_all()


# ============================================================
# FastAPI application
# ============================================================

app = FastAPI(
    title="IBVAP API",
    version="0.1.0",
    lifespan=lifespan,
)


# ============================================================
# CORS Configuration
# ============================================================

# Production frontend hosted on Render
PRODUCTION_FRONTEND_URL = (
    "https://nigrani-ai-intelligence-surveillance-1.onrender.com"
)

if settings.ENVIRONMENT == "production":

    allowed_origins = [
        PRODUCTION_FRONTEND_URL,
    ]

    # Also allow FRONTEND_URL from Render environment/config
    if settings.FRONTEND_URL:
        frontend_url = settings.FRONTEND_URL.strip().rstrip("/")

        if frontend_url:
            allowed_origins.append(frontend_url)

    # Also allow additional origins configured in ALLOWED_ORIGINS
    if settings.ALLOWED_ORIGINS:
        configured_origins = [
            origin.strip().rstrip("/")
            for origin in settings.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

        allowed_origins.extend(configured_origins)

    # Remove duplicates while preserving order
    allowed_origins = list(dict.fromkeys(allowed_origins))

else:

    # Local development
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        PRODUCTION_FRONTEND_URL,
    ]

    if settings.FRONTEND_URL:
        frontend_url = settings.FRONTEND_URL.strip().rstrip("/")

        if frontend_url:
            allowed_origins.append(frontend_url)

    if settings.ALLOWED_ORIGINS:
        configured_origins = [
            origin.strip().rstrip("/")
            for origin in settings.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

        allowed_origins.extend(configured_origins)

    # Remove duplicates
    allowed_origins = list(dict.fromkeys(allowed_origins))


logger.info(
    f"CORS allowed origins: {allowed_origins}"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Mount evidence static files
# ============================================================

app.mount(
    "/api/v1/evidence",
    StaticFiles(directory=settings.EVIDENCE_DIR),
    name="evidence",
)


# ============================================================
# Request processing time middleware
# ============================================================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):

    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time

    print(
        f"MEASURE_ENDPOINT: "
        f"{request.method} "
        f"{request.url.path} "
        f"took {process_time:.4f}s"
    )

    return response


# ============================================================
# Initialize event engine singleton
# ============================================================

import backend.app.services.event_engine


# ============================================================
# API Routers
# ============================================================

app.include_router(
    health.router,
    prefix="/api/v1",
)

app.include_router(
    system.router,
    prefix="/api/v1",
)

app.include_router(
    cameras.router,
    prefix="/api/v1",
)

app.include_router(
    fences.router,
    prefix="/api/v1",
)

app.include_router(
    events.router,
)

app.include_router(
    alerts.router,
)

app.include_router(
    ws.router,
    prefix="/api/v1",
)

app.include_router(
    anpr.router,
    prefix="/api/v1",
)

app.include_router(
    api_settings.router,
    prefix="/api/v1",
)

app.include_router(
    face_recognition.router,
    prefix="/api/v1",
)

app.include_router(
    incidents.router,
    prefix="/api/v1/incidents",
    tags=["incidents"],
)


# ============================================================
# Local development entry point
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=(settings.ENVIRONMENT != "production"),
    )