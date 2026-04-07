import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from api.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@patch('api.main.flow.run')
def test_analyze(mock_flow_run):
    mock_flow_run.return_value = {
        "vision": {"objects": ["knife"]},
        "risk": {"severity": "high"},
        "decision": {"action": "ALERT"},
        "recommendations": ["test"]
    }
    
    response = client.post("/analyze", json={
        "image_path": "test.jpg",
        "child_id": "child_001"
    })
    
    assert response.status_code == 200
    assert response.json()["decision"]["action"] == "ALERT"

def test_history():
    response = client.get("/history/child_001")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
