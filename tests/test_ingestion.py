import pytest
import os
import cv2
import numpy as np
from fastapi.testclient import TestClient

# Mock settings before importing app
import os
os.environ["PROCESS_FPS"] = "30"
os.environ["FRAME_QUEUE_SIZE"] = "10"

from backend.app.main import app
from backend.app.services.camera_manager import camera_manager, CameraConfig
from ai_engine.ingestion.file_source import FileVideoSource
from ai_engine.pipeline import CameraPipeline
from scripts.generate_test_video import generate_test_video

client = TestClient(app)

TEST_VIDEO_PATH = "data/videos/test_fixture.mp4"

@pytest.fixture(scope="session", autouse=True)
def setup_test_video():
    generate_test_video(TEST_VIDEO_PATH, duration_sec=2)
    yield
    camera_manager.stop_all()
    import time
    time.sleep(0.5) # Wait for threads to close
    if os.path.exists(TEST_VIDEO_PATH):
        try:
            os.remove(TEST_VIDEO_PATH)
        except Exception:
            pass

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_camera_crud():
    # Clear manager
    camera_manager.pipelines.clear()
    camera_manager.configs.clear()
    
    # Add
    response = client.post("/api/v1/cameras/", json={"name": "TestCam", "source": TEST_VIDEO_PATH, "type": "file"})
    assert response.status_code == 200
    cam_id = response.json()["id"]
    
    # List
    response = client.get("/api/v1/cameras/")
    assert len(response.json()) == 1
    
    # Get
    response = client.get(f"/api/v1/cameras/{cam_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "TestCam"
    
    # Delete
    response = client.delete(f"/api/v1/cameras/{cam_id}")
    assert response.status_code == 200
    assert len(camera_manager.get_all_cameras()) == 0

def test_file_video_source():
    source = FileVideoSource("test_id", TEST_VIDEO_PATH)
    assert source.connect() == True
    assert source.is_open() == True
    
    meta = source.get_metadata()
    assert meta["width"] == 640
    assert meta["height"] == 480
    
    success, frame = source.read_frame()
    assert success == True
    assert isinstance(frame, np.ndarray)
    
    source.release()
    assert source.is_open() == False

def test_pipeline_queue_throttling():
    source = FileVideoSource("test_id2", TEST_VIDEO_PATH)
    pipeline = CameraPipeline(source, process_fps=15, queue_size=5)
    
    assert pipeline.start() == True
    
    import time
    time.sleep(0.5) # Let it process some frames
    
    health = pipeline.get_health()
    assert health["frames_processed"] > 0
    assert health["queue_size"] <= 5 # Bounded queue check
    
    pipeline.stop()
    assert pipeline.is_running == False

def test_camera_start_stop_api():
    # Add
    response = client.post("/api/v1/cameras/", json={"name": "StartCam", "source": TEST_VIDEO_PATH, "type": "file"})
    cam_id = response.json()["id"]
    
    # Start
    response = client.post(f"/api/v1/cameras/{cam_id}/start")
    assert response.status_code == 200
    
    # Status
    response = client.get(f"/api/v1/cameras/{cam_id}/status")
    assert response.status_code == 200
    assert response.json()["is_running"] == True or response.json().get("status") == "stopped" # might finish fast
    
    # Stop
    response = client.post(f"/api/v1/cameras/{cam_id}/stop")
    assert response.status_code == 200
    
    # Status
    response = client.get(f"/api/v1/cameras/{cam_id}/status")
    assert response.status_code == 200
    assert response.json().get("status") == "stopped"
    
    # Cleanup properly for file release
    client.delete(f"/api/v1/cameras/{cam_id}")
