from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List
import os
import json
import uuid
import cv2
import numpy as np

from backend.app.core.logger import get_logger

router = APIRouter()
logger = get_logger("FaceRecognitionAPI")

REGISTRY_FILE = "data/face_registry.json"

class EnrolledFace(BaseModel):
    id: str
    name: str
    # we don't return embedding to frontend usually

def _load_registry():
    if not os.path.exists(REGISTRY_FILE):
        return []
    try:
        with open(REGISTRY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load face registry: {e}")
        return []

def _save_registry(data):
    os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@router.get("/faces", response_model=List[EnrolledFace])
async def get_faces():
    data = _load_registry()
    faces = []
    for f in data:
        faces.append(EnrolledFace(id=f['id'], name=f['name']))
    return faces

@router.post("/faces", response_model=EnrolledFace)
async def add_face(
    name: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        import face_recognition
    except ImportError:
        raise HTTPException(status_code=500, detail="face_recognition library not installed")

    # Read image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    face_locations = face_recognition.face_locations(rgb_img)
    if not face_locations:
        raise HTTPException(status_code=400, detail="No face detected in the image")
        
    if len(face_locations) > 1:
        raise HTTPException(status_code=400, detail="More than one face detected. Please upload an image with exactly one face.")
        
    face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
    if not face_encodings:
        raise HTTPException(status_code=400, detail="Could not extract face encoding")
        
    encoding = face_encodings[0].tolist()
    
    face_id = str(uuid.uuid4())
    new_face = {
        "id": face_id,
        "name": name,
        "embedding": encoding
    }
    
    data = _load_registry()
    data.append(new_face)
    _save_registry(data)
    
    # Reload registry in active pipelines (Optional, or just restart them)
    from backend.app.services.camera_manager import camera_manager
    for cam_id, pipeline in camera_manager.pipelines.items():
        if pipeline.face_engine:
            pipeline.face_engine._load_registry()
            
    return EnrolledFace(id=face_id, name=name)

@router.delete("/faces/{face_id}")
async def delete_face(face_id: str):
    data = _load_registry()
    new_data = [f for f in data if f['id'] != face_id]
    
    if len(data) == len(new_data):
        raise HTTPException(status_code=404, detail="Face not found")
        
    _save_registry(new_data)
    
    from backend.app.services.camera_manager import camera_manager
    for cam_id, pipeline in camera_manager.pipelines.items():
        if pipeline.face_engine:
            pipeline.face_engine._load_registry()
            
    return {"status": "success"}
