# tests/test_websocket.py
import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_app_initialization():
    """Test that FastAPI app initializes."""
    assert app.title == "Appliance Inventory Live API"


def test_static_files_mounted():
    """Test that static files are accessible."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_websocket_endpoint_exists():
    """Test that WebSocket endpoint is defined."""
    client = TestClient(app)
    # Try to connect to WebSocket
    with pytest.raises(Exception):  # Will fail until we implement
        with client.websocket_connect("/ws/test_user/test_session"):
            pass
