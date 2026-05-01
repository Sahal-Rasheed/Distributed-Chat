import pytest
from fastapi.testclient import TestClient


# Note: For testing WebSocket endpoints, We need to use TestClient from fastapi.testclient instead of httpx.AsyncClient, because httpx does not support WebSocket testing out of the box. We can use package like 'httpx-ws' for WebSocket testing using httpx, but for simplicity, we will use TestClient here.


@pytest.fixture
def client():
    """
    A test client for the FastAPI app.
    """
    from app.main import app

    client = TestClient(app)
    yield client
