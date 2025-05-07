import pytest
import asyncio
from pyacquisition import Experiment
import threading
import requests
from aiohttp import ClientSession
import tomllib


@pytest.fixture(scope="module")
def toml_config():
    with open('tests/integration/basic.toml', "rb") as file:
        return tomllib.load(file)


@pytest.fixture(scope="module")  # Explicitly set the scope to "module"
def basic_experiment():
    experiment = Experiment.from_config("tests/integration/basic.toml")
    return experiment


@pytest.fixture(scope="module")
def running_experiment(basic_experiment):
    def run_server():
        asyncio.run(basic_experiment.run())

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    asyncio.run(asyncio.sleep(2))
    yield  # Yield control to the test
    server_thread.join(timeout=1)


@pytest.mark.asyncio
async def test_fastapi_service(running_experiment):
    response = requests.get("http://localhost:8005/ping")
    assert response.status_code == 200, "Health check endpoint should return 200 OK"
    assert response.json() == "pong", "Health check endpoint should return 'pong'"


@pytest.mark.asyncio
async def test_websockets_streaming_data(running_experiment):
    async with ClientSession() as session:
        async with session.ws_connect("ws://localhost:8005/data") as websocket:
            for _ in range(3):
                message = await websocket.receive_json()
                assert "time" in message, "Response should contain the key 'time'"
                assert isinstance(message["time"], float), "The 'time' field should be of type float"
                
                
@pytest.mark.asyncio
async def test_websockets_streaming_logs(running_experiment):
    async with ClientSession() as session:
        async with session.ws_connect("ws://localhost:8005/logs") as websocket:
            for _ in range(3):
                message = await websocket.receive_json()
                assert "time" in message, "Response should contain the key 'time'"
                assert isinstance(message["time"], float), "The 'time' field should be of type float"
                

@pytest.mark.asyncio
async def test_rack_period(running_experiment, toml_config):
    config_period = toml_config["rack"]["period"]
    tolerance = 0.025
    async with ClientSession() as session:
        async with session.ws_connect("ws://localhost:8005/data") as websocket:
            for _ in range(3):
                message = await websocket.receive_json()
                if _ > 0:  # Skip the first message as there's no previous timestamp to compare
                    assert abs(message["time"] - previous_time - config_period) < tolerance, (
                        f"Timestamps should be approximately {config_period} seconds apart"
                    )
                previous_time = message["time"]
                

@pytest.mark.asyncio
async def test_rack_pause_resume(running_experiment, toml_config):
    config_period = toml_config["rack"]["period"]
    tolerance = 0.050
    async with ClientSession() as session:
        async with session.ws_connect("ws://localhost:8005/data") as websocket:
            
            # Drain the queue by fetching all data points until a timeout occurs
            while True:
                try:
                    await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
                except asyncio.TimeoutError:
                    break
            
            try:
                await asyncio.wait_for(websocket.receive_json(), timeout=config_period+tolerance)
            except asyncio.TimeoutError:
                pytest.fail("Message not received during the initial wait, but one was expected")   
            
            response = requests.get("http://localhost:8005/rack/pause")
            assert response.status_code == 200, "Pause endpoint should return 200 OK"
            
            try:
                await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                pytest.fail("Message received during pause, but none was expected")
            except asyncio.TimeoutError:
                pass

            response = requests.get("http://localhost:8005/rack/resume")
            assert response.status_code == 200, "Pause endpoint should return 200 OK"
            
            try:
                await asyncio.wait_for(websocket.receive_json(), timeout=config_period+tolerance)
            except asyncio.TimeoutError:
                pytest.fail("Message not received after resuming, but one was expected")
            
            