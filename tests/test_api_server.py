import pytest
import asyncio
from fastapi.testclient import TestClient
from pyacquisition.core.api_server import APIServer


@pytest.fixture
def api_server():
    """
    Fixture to initialize the APIServer instance.
    """
    return APIServer()


@pytest.fixture
def test_client(api_server):
    """
    Fixture to create a TestClient for the FastAPI app.
    """
    return TestClient(api_server.app)


def test_api_server_initialization(api_server):
    """
    Test if the APIServer is initialized with the correct attributes.
    """
    assert api_server.host == "localhost"
    assert api_server.port == 8000
    assert api_server.app.title == "PyAcquisition API"
    assert api_server.app.description == "API for PyAcquisition"


def test_cors_middleware(test_client):
    """
    Test if the CORS middleware is configured correctly.
    """
    response = test_client.options("/")
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_server_coroutine(api_server):
    """
    Test if the coroutine method is callable and returns a coroutine.
    """
    coroutine = api_server.coroutine()
    assert asyncio.iscoroutine(coroutine)