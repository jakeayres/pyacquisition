import pytest
import asyncio
from pyacquisition import Experiment
import threading
import requests
from aiohttp import ClientSession
import tomllib


async def next_row(websocket, timeout=5.0):
    """The values of the next row on `/stream/data`, past any other event."""
    while True:
        event = await asyncio.wait_for(websocket.receive_json(), timeout=timeout)
        if event["type"] == "row":
            return event["values"]


@pytest.fixture(scope="module")
def toml_config():
    with open("tests/integration/calculator.toml", "rb") as file:
        return tomllib.load(file)


@pytest.fixture(scope="module")  # Explicitly set the scope to "module"
def basic_experiment():
    experiment = Experiment.from_config("tests/integration/calculator.toml")
    return experiment


@pytest.fixture(scope="module")
def running_experiment(basic_experiment):
    def run_server():
        asyncio.run(basic_experiment.run())

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    asyncio.run(asyncio.sleep(2))
    yield  # Yield control to the test
    # Stopped, so that its port is free for the next module's experiment.
    try:
        requests.get("http://localhost:8006/experiment/shutdown", timeout=5)
    except requests.exceptions.RequestException:
        pass
    server_thread.join(timeout=15)


@pytest.mark.asyncio
def test_instruments_exists(running_experiment, toml_config, basic_experiment):
    instruments = toml_config["instruments"]
    for instrument in instruments:
        assert instrument in basic_experiment.instruments, (
            f"Instrument {instrument} should exist in the experiment"
        )
    assert "random_instrument_xyzxyxz" not in basic_experiment.instruments, (
        "Instrument 'random_instrument_xyzxyxz' should not exist in the experiment"
    )


@pytest.mark.asyncio
def test_instrument_identify_endpoint(running_experiment, toml_config):
    for instrument in toml_config["instruments"]:
        response = requests.get(f"http://localhost:8006/{instrument}/identify")
        assert response.status_code == 200, (
            f"Identify endpoint for {instrument} should return 200 OK"
        )


def test_set_get_enum_endpoints(running_experiment):
    response = requests.get(
        "http://localhost:8006/calculator/set_angle_unit?unit=degree"
    )
    assert response.status_code == 200
    assert response.json()["data"] == 0

    response = requests.get("http://localhost:8006/calculator/get_angle_unit")
    assert response.status_code == 200
    assert response.json()["data"] == "degree"

    response = requests.get(
        "http://localhost:8006/calculator/set_angle_unit?unit=radian"
    )
    assert response.status_code == 200
    assert response.json()["data"] == 1

    response = requests.get("http://localhost:8006/calculator/get_angle_unit")
    assert response.status_code == 200
    assert response.json()["data"] == "radian"


def test_float_endpoint(running_experiment):
    response = requests.get("http://localhost:8006/calculator/one")
    assert response.status_code == 200
    assert response.json()["data"] == 1.0


def test_float_endpoint_with_float_args(running_experiment):
    response = requests.get("http://localhost:8006/calculator/add?x=1.0&y=2.0")
    assert response.status_code == 200
    assert response.json()["data"] == 3.0


def test_float_endpoint_with_enum_args(running_experiment):
    response = requests.get("http://localhost:8006/calculator/trig?x=1.0&function=sine")
    assert response.status_code == 200
    assert response.json()["data"] == pytest.approx(0.8415, rel=1e-4)


@pytest.mark.asyncio
async def test_length_of_data(running_experiment, toml_config):
    async with ClientSession() as session:
        async with session.ws_connect("ws://localhost:8006/stream/data") as websocket:
            message = await next_row(websocket)
            assert len(message) == len(toml_config["measurements"])


@pytest.mark.asyncio
async def test_float_measurement(running_experiment):
    async with ClientSession() as session:
        async with session.ws_connect("ws://localhost:8006/stream/data") as websocket:
            message = await next_row(websocket)
            assert message["one"] == 1.0, "Response should contain the key 'one'"
            assert "random_key" not in message, (
                "Response should not contain the key 'random_key'"
            )


@pytest.mark.asyncio
async def test_float_measurement_with_float_args(running_experiment):
    async with ClientSession() as session:
        async with session.ws_connect("ws://localhost:8006/stream/data") as websocket:
            message = await next_row(websocket)
            assert message["add"] == 3.0, "Response should contain the key 'add'"
            assert "random_key" not in message, (
                "Response should not contain the key 'random_key'"
            )


@pytest.mark.asyncio
async def test_float_measurement_with_enum_args(running_experiment):
    async with ClientSession() as session:
        async with session.ws_connect("ws://localhost:8006/stream/data") as websocket:
            message = await next_row(websocket)
            assert message["sine_one"] == pytest.approx(0.8415, rel=1e-4), (
                "Response should contain the key 'trig'"
            )
            assert "random_key" not in message, (
                "Response should not contain the key 'random_key'"
            )


@pytest.mark.asyncio
async def test_temperature_measurement(running_experiment):
    async with ClientSession() as session:
        async with session.ws_connect("ws://localhost:8006/stream/data") as websocket:
            message = await next_row(websocket)
            assert message["temperature"] == 25.0, (
                "Response should contain the key 'temperature'"
            )
            assert "random_key" not in message, (
                "Response should not contain the key 'random_key'"
            )
