import json
import aiohttp
import asyncio
import requests
import websockets
from ..core.broadcaster import Broadcaster
from ..core.logging import logger


class Stream(Broadcaster):
    def __init__(self, name: str, url: str, params: dict = None) -> None:
        """
        Initializes the Stream with the specified name.

        Args:
            name (str): The name of the stream.
        """
        super().__init__()
        self.name = name
        self.url = url
        self.params = params if params else {}

    async def run(self):
        """
        Connects to a websocket endpoint and yields messages as they arrive.

        Args:
            endpoint (str): The websocket endpoint to connect to (e.g., '/ws').
            params (dict, optional): Query parameters to include in the connection URL.

        """
        async with websockets.connect(self.url) as websocket:
            try:
                while True:
                    message = await websocket.recv()
                    await self.broadcast(json.loads(message))
            except websockets.ConnectionClosed:
                logger.debug("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error in WebSocket connection: {e}")


class Poller:
    """
    A class for polling an API endpoint and broadcasting the response.
    """

    def __init__(
        self, name: str, url: str, params: dict = None, period: float = 1.0
    ) -> None:
        """
        Initializes the Poller with the specified name and URL.

        Args:
            name (str): The name of the poller.
            url (str): The URL to poll.
            params (dict, optional): Query parameters to include in the request.
            period (float, optional): The time interval between requests in seconds.
        """
        super().__init__()
        self.name = name
        self.url = url
        self.params = params if params else {}
        self.period = period
        self.callbacks = []

    def add_callback(self, callback: callable) -> None:
        """
        Adds a callback to be called with the response data.

        Args:
            callback (callable): The callback function to add.
        """
        self.callbacks.append(callback)

    async def run(self):
        """
        Repeatedly poll an API endpoint and broadcast the response.
        """
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(self.url, params=self.params) as response:
                        data = await response.text()
                        json_data = json.loads(data)
                        try:
                            for callback in self.callbacks:
                                callback(json_data)
                        except Exception as e:
                            logger.error(f"Error in poller [{self.name}] callback: {e}")
                    await asyncio.sleep(self.period)
                except Exception as e:
                    logger.error(f"Error in Poller run: {e}")
                    await asyncio.sleep(self.period)


class APIClient:
    """
    A class for facilitating the communication with the FastAPI
    server presented by the main process.
    """

    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        """
        Initializes the APIClient with the specified host and port.

        Args:
            host (str): The hostname of the FastAPI server.
            port (int): The port number of the FastAPI server.
        """
        self.host = host
        self.port = port
        self.streams = {}
        self.pollers = {}

    async def run(self):
        """
        Starts the APIClient and its streams.
        """
        try:
            async with asyncio.TaskGroup() as task_group:
                for name, stream in self.streams.items():
                    task_group.create_task(stream.run())
                for name, poller in self.pollers.items():
                    task_group.create_task(poller.run())
        except Exception as e:
            logger.error(f"Error in APIClient run: {e}")

    def add_stream(self, name: str, url: str) -> None:
        """
        Adds a new stream to the APIClient.

        Args:
            name (str): The name of the stream to add.
        """
        try:
            full_url = f"ws://{self.host}:{self.port}{url}"
            self.streams[name] = Stream(name, full_url)
            return self.streams[name]
        except Exception as e:
            logger.error(f"Error adding stream {name}: {e}")

    def add_poller(
        self, name: str, url: str, params: dict = None, period: float = 1.0
    ) -> None:
        """
        Adds a new poller to the APIClient.

        Args:
            name (str): The name of the poller to add.
            url (str): The URL to poll.
            params (dict, optional): Query parameters to include in the request.
            period (float, optional): The time interval between requests in seconds.
        """
        try:
            full_url = f"http://{self.host}:{self.port}{url}"
            self.pollers[name] = Poller(name, full_url, params, period)
            return self.pollers[name]
        except Exception as e:
            logger.error(f"Error adding poller {name}: {e}")

    async def async_get(
        self, endpoint: str, params: dict = None, callback: callable = None
    ) -> dict:
        """
        Sends a GET request to the specified endpoint with optional parameters.

        Args:
            endpoint (str): The API endpoint to send the request to.
            params (dict, optional): The query parameters to include in the request.

        Returns:
            dict: The JSON response from the server.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{self.host}:{self.port}{endpoint}", params=params
            ) as response:
                data = await response.text()
                if callback:
                    await callback(json.loads(data))
                return json.loads(data)

    def get(
        self, endpoint: str, params: dict = None, callback: callable = None
    ) -> dict:
        """
        Sends a GET request to the specified endpoint with optional parameters.

        Args:
            endpoint (str): The API endpoint to send the request to.
            params (dict, optional): The query parameters to include in the request.

        Returns:
            dict: The JSON response from the server.
        """
        logger.debug(f"GET request to {endpoint} with params {params}")
        response = requests.get(
            f"http://{self.host}:{self.port}{endpoint}", params=params
        )
        logger.debug(f"Response: {response.json()}")
        data = response.json()
        if callback:
            callback(data)
        return data

    async def poll(
        self,
        endpoint: str,
        params: dict = None,
        period: float = 1.0,
        callback: callable = None,
    ) -> dict:
        """
        Repeatedly poll an API endpoint and broadcast the response.

        Args:
            broadcaster (str): The name of the broadcaster to use.
            endpoint (str): The API endpoint to poll.
            params (dict, optional): The query parameters to include in the request.
            period (float, optional): The time interval between requests in seconds.
        """
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(
                    f"http://{self.host}:{self.port}{endpoint}", params=params
                ) as response:
                    data = await response.text()
                    json_data = json.loads(data)
                    if callback:
                        await callback(json_data)
                await asyncio.sleep(period)

    async def websocket_connect(self, endpoint: str, params: dict = None):
        """
        Connects to a websocket endpoint and yields messages as they arrive.

        Args:
            endpoint (str): The websocket endpoint to connect to (e.g., '/ws').
            params (dict, optional): Query parameters to include in the connection URL.

        Yields:
            str: Messages received from the websocket.
        """
        url = f"ws://{self.host}:{self.port}{endpoint}"

        async with websockets.connect(url) as websocket:
            try:
                while True:
                    message = await websocket.recv()
                    print(message)
                    # yield message
            except websockets.ConnectionClosed:
                logger.debug("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error in WebSocket connection: {e}")
