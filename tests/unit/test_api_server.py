import pytest
import asyncio
from enum import Enum
from fastapi.testclient import TestClient
from pyacquisition.core.api_server import APIServer, SHUTDOWN_TIMEOUT


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
    coroutine.close()


@pytest.mark.asyncio
async def test_shutdown_finishes_even_if_a_connection_is_never_released():
    """
    On Windows, a client that drops its connection at the wrong moment can leave
    asyncio counting a connection that is gone, so that waiting for the server's
    connections to close never ends. The server must stop anyway.
    """
    import socket

    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]

    api_server = APIServer(port=port)
    serving = asyncio.create_task(api_server.run())
    while not getattr(api_server, "server", None) or not api_server.server.started:
        await asyncio.sleep(0.05)

    async def never_closes():
        await asyncio.Event().wait()

    for server in api_server.server.servers:  # what the leaked connection causes
        server.wait_closed = never_closes

    await api_server.shutdown()

    await asyncio.wait_for(serving, timeout=SHUTDOWN_TIMEOUT + 5)


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


def test_making_an_endpoint_leaves_the_methods_annotations_alone(api_server):
    """They belong to the method's class: an instrument's getter must still say
    what it returns after its endpoint is made."""

    def get_level(channel: int) -> float:
        return 1.0

    api_server.create_endpoint_function(get_level)

    assert get_level.__annotations__ == {"channel": int, "return": float}
