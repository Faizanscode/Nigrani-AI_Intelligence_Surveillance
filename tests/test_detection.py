import pytest
import numpy as np
import time
from unittest.mock import MagicMock, patch

from backend.app.core.config import settings
from ai_engine.detection.models import DetectionResult, BoundingBox
from ai_engine.detection.yolo_detector import YOLODetector
from ai_engine.detection.visualizer import DetectionVisualizer
from ai_engine.pipeline import CameraPipeline
from ai_engine.ingestion.file_source import FileVideoSource
from scripts.generate_test_video import generate_test_video
import os

TEST_VIDEO_PATH = "data/videos/test_fixture.mp4"

@pytest.fixture(scope="session", autouse=True)
def setup_test_video():
    generate_test_video(TEST_VIDEO_PATH, duration_sec=2)
    yield
    import time
    time.sleep(0.5)
    if os.path.exists(TEST_VIDEO_PATH):
        try:
            os.remove(TEST_VIDEO_PATH)
        except Exception:
            pass

def test_yolo_detector_initialization():
    detector = YOLODetector()
    assert detector.model_path == settings.YOLO_MODEL
    assert detector.confidence == settings.YOLO_CONFIDENCE
    assert detector.iou == settings.YOLO_IOU
    assert "person" in detector.target_class_names

@patch("ai_engine.detection.yolo_detector.YOLO")
def test_yolo_detector_load(mock_yolo_class):
    mock_model_instance = MagicMock()
    mock_model_instance.names = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
    mock_yolo_class.return_value = mock_model_instance

    detector = YOLODetector()
    success = detector.load_model()
    
    assert success == True
    assert detector.model is not None
    # Check that it correctly filtered target classes
    # 'bicycle' is not in our defaults (person, car, motorcycle, bus, truck)
    assert 0 in detector.target_class_ids
    assert 2 in detector.target_class_ids
    assert 1 not in detector.target_class_ids

@patch("ai_engine.detection.yolo_detector.YOLO")
def test_yolo_detector_inference(mock_yolo_class):
    mock_model_instance = MagicMock()
    mock_model_instance.names = {0: "person", 2: "car"}
    
    # Mock result box
    mock_box = MagicMock()
    mock_box.cls = [np.array(0)] # class id 0 (person)
    mock_box.conf = [np.array(0.95)] # confidence
    mock_box.xyxy = [np.array([100, 100, 200, 300])]
    
    mock_result = MagicMock()
    mock_result.boxes = [mock_box]
    
    mock_model_instance.predict.return_value = [mock_result]
    mock_yolo_class.return_value = mock_model_instance
    
    detector = YOLODetector()
    detector.load_model()
    
    # Dummy frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = detector.detect(frame)
    
    assert len(detections) == 1
    det = detections[0]
    assert det.class_id == 0
    assert det.class_name == "person"
    assert det.confidence == 0.95
    assert det.bbox.x1 == 100
    assert det.bbox.y1 == 100
    assert det.bbox.x2 == 200
    assert det.bbox.y2 == 300
    assert det.bbox.width == 100
    assert det.bbox.height == 200

def test_visualizer():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    bbox = BoundingBox(x1=10, y1=10, x2=50, y2=100, center_x=30, center_y=55, width=40, height=90)
    det = DetectionResult(class_id=0, class_name="person", confidence=0.88, bbox=bbox)
    
    annotated = DetectionVisualizer.draw_detections(frame, [det])
    
    # The annotated frame should not be the same reference
    assert id(annotated) != id(frame)
    # Since we drew green on it, it shouldn't be all zeros anymore
    assert np.any(annotated > 0)
    
@patch("ai_engine.detection.yolo_detector.YOLO")
def test_pipeline_integration(mock_yolo_class):
    mock_model_instance = MagicMock()
    mock_model_instance.names = {0: "person"}
    mock_model_instance.predict.return_value = [] # Return empty detections for speed
    mock_yolo_class.return_value = mock_model_instance

    source = FileVideoSource("test_cam", "data/videos/test_fixture.mp4")
    pipeline = CameraPipeline(source, process_fps=15, queue_size=5)
    
    detector = YOLODetector()
    pipeline.add_detector(detector)
    
    # The start should load the model
    pipeline.start()
    
    time.sleep(0.5) # Let it process some frames
    
    health = pipeline.get_health()
    
    pipeline.stop()
    
    # We should have processed frames and triggered detection
    assert health["frames_processed"] > 0
    assert "output_queue_size" in health
    assert "detector_metrics" in health
    assert health["detector_metrics"]["inference_count"] > 0
