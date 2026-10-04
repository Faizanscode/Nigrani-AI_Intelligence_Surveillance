import pytest
import os
import json
import numpy as np
from ai_engine.face_recognition.engine import FaceRecognitionEngine, FaceRecognitionResult

def test_face_recognition_engine_initialization():
    engine = FaceRecognitionEngine(camera_id="cam_test", registry_file="data/face_registry.json")
    assert engine.is_available is True
    assert len(engine.known_face_names) >= 1
    print(f"Loaded faces: {engine.known_face_names}")

def test_face_recognition_process_no_persons():
    engine = FaceRecognitionEngine(camera_id="cam_test", registry_file="data/face_registry.json")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Track with class 'car'
    tracks = [{
        "track_id": 1,
        "class_name": "car",
        "box": [10, 10, 100, 100]
    }]
    metadata = {"timestamp": 123456.78}
    results = engine.process(dummy_frame, tracks, metadata)
    assert len(results) == 0

def test_face_recognition_process_person_blank_image():
    engine = FaceRecognitionEngine(camera_id="cam_test", registry_file="data/face_registry.json")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Track with class 'person'
    tracks = [{
        "track_id": 2,
        "class_name": "person",
        "box": [50, 50, 200, 300]
    }]
    metadata = {"timestamp": 123456.78}
    results = engine.process(dummy_frame, tracks, metadata)
    assert len(results) == 1
    assert results[0].status == "NO_FACE"
    assert results[0].track_id == 2
    assert results[0].event_id.startswith("face_cam_test_2_")

if __name__ == "__main__":
    test_face_recognition_engine_initialization()
    test_face_recognition_process_no_persons()
    test_face_recognition_process_person_blank_image()
    print("All face recognition tests passed!")
