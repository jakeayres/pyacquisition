import pytest
import asyncio
from enum import Enum
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


def test_server_run(api_server):
    """
    Test if the coroutine method is callable and returns a coroutine.
    """
    coroutine = api_server.run()
    assert asyncio.iscoroutine(coroutine)


class SampleEnum(Enum):
    OPTION_ONE = 1
    OPTION_TWO = 2
    OPTION_THREE = 3


def test_enum_to_selected_dict():
    """
    Test the _enum_to_selected_dict function to ensure it converts an enum instance
    to the correct dictionary format.
    """
    enum_instance = SampleEnum.OPTION_TWO
    # Call the private method
    result = APIServer._enum_to_selected_dict(enum_instance)
    # Expected result
    expected_result = {
        "OPTION_ONE": {"value": 1, "selected": False},
        "OPTION_TWO": {"value": 2, "selected": True},
        "OPTION_THREE": {"value": 3, "selected": False},
    }
    assert result == expected_result
