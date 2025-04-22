import json
import aiohttp
import asyncio
import requests
from ..core.broadcaster import Broadcaster
from ..core.logging import logger


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
    
    
    async def async_get(self, endpoint: str, params: dict = None, callback: callable = None) -> dict:
        """
        Sends a GET request to the specified endpoint with optional parameters.
        
        Args:
            endpoint (str): The API endpoint to send the request to.
            params (dict, optional): The query parameters to include in the request.
        
        Returns:
            dict: The JSON response from the server.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{self.host}:{self.port}{endpoint}", params=params) as response:
                data = await response.text()
                if callback:
                    await callback(json.loads(data))
                return json.loads(data)
            
            
    def get(self, endpoint: str, params: dict = None, callback: callable = None) -> dict:
        """
        Sends a GET request to the specified endpoint with optional parameters.
        
        Args:
            endpoint (str): The API endpoint to send the request to.
            params (dict, optional): The query parameters to include in the request.
        
        Returns:
            dict: The JSON response from the server.
        """
        logger.debug(f"GET request to {endpoint} with params {params}")
        response = requests.get(f"http://{self.host}:{self.port}{endpoint}", params=params)
        logger.debug(f"Response: {response.json()}")
        data = response.json()
        if callback:
            callback(data)
        return data
            
    
    async def poll(self, endpoint: str, params: dict = None, period: float = 1.0, callback: callable = None) -> dict:
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
                async with session.get(f"http://{self.host}:{self.port}{endpoint}", params=params) as response:
                    data = await response.text()
                    json_data = json.loads(data)
                    if callback:
                        await callback(json_data)
                await asyncio.sleep(period)