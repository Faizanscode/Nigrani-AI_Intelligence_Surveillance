import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings

client = TestClient(app)

def test_get_night_movement_mode():
    settings.NIGHT_MOVEMENT_MODE = "AUTO"
    response = client.get("/api/v1/settings/night-movement")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "AUTO"
    assert "active" in data
    assert "is_night" in data

def test_update_night_movement_mode():
    response = client.post("/api/v1/settings/night-movement", json={"mode": "ON"})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "ON"
    assert data["active"] == True
    
    assert settings.NIGHT_MOVEMENT_MODE == "ON"
    
    response = client.post("/api/v1/settings/night-movement", json={"mode": "OFF"})
    assert response.status_code == 200
    assert response.json()["active"] == False
    assert settings.NIGHT_MOVEMENT_MODE == "OFF"

def test_invalid_night_movement_mode():
    response = client.post("/api/v1/settings/night-movement", json={"mode": "INVALID"})
    assert response.status_code == 400
