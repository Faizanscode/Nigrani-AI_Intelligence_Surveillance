from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from backend.app.api import cameras, health, fences, events, alerts, ws
from backend.app.services.camera_manager import camera_manager
from backend.app.core.logger import get_logger

logger = get_logger("Main")

# Ensure evidence directory exists
os.makedirs("data/evidence", exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    import asyncio
    from backend.app.core.event_bus import event_bus
    loop = asyncio.get_running_loop()
    event_bus.set_main_loop(loop)
    logger.info("Starting IBVAP Backend with event_bus linked to main event loop")
    yield
    # Shutdown
    logger.info("Shutting down IBVAP Backend...")
    camera_manager.stop_all()

app = FastAPI(title="IBVAP API", version="0.1.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"], # Support Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount evidence static files
app.mount("/api/v1/evidence", StaticFiles(directory="data/evidence"), name="evidence")

import time
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    # logger.info(f"{request.method} {request.url.path} - {process_time:.4f}s")
    print(f"MEASURE_ENDPOINT: {request.method} {request.url.path} took {process_time:.4f}s")
    return response

# Initialize event engine singleton
import backend.app.services.event_engine

from backend.app.api import cameras, health, fences, events, alerts, ws, anpr, settings as api_settings, face_recognition, incidents, system

# API Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(cameras.router, prefix="/api/v1")
app.include_router(fences.router, prefix="/api/v1")
app.include_router(events.router)
app.include_router(alerts.router)
app.include_router(ws.router, prefix="/api/v1")
app.include_router(anpr.router, prefix="/api/v1")
app.include_router(api_settings.router, prefix="/api/v1")
app.include_router(face_recognition.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["incidents"])

if __name__ == "__main__":
    import uvicorn
    from backend.app.core.config import settings
    uvicorn.run("backend.app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
