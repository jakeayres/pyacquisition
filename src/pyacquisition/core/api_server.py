from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedOK
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from .logging import logger
from .consumer import Consumer
from .response import StringResponse, DictResponse
from enum import Enum


class WebsocketEndpoint(Consumer):
    """
    A class that handles WebSocket connections and data streaming.
    """
    
    def __init__(self, url: str, function: callable):
        """
        Initialize the WebSocket endpoint.

        Args:
            url (str): The URL path for the WebSocket endpoint.
            function (callable): The function to call when data is received.
        """
        super().__init__()
        self.url = url
        self.function = function
        
        logger.debug(f"[SocketEndpoint] Initialized with URL: {url}")



class APIServer:
    
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        allowed_cors_origins: list = ["http://localhost:3000"],
    ):
        
        self.host = host
        self.port = port
        
        self.app = FastAPI(
            title="PyAcquisition API",
            description="API for PyAcquisition",
        )

        self.websocket_endpoints = {}
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        logger.debug("[FastApi] APIServer initialized")



    
    
    @staticmethod
    def _enum_to_selected_dict(enum_instance):
        """
        Converts an enum instance to a dictionary with enum names as keys and their values as values.
        """
        return {
            item.name: {
                "value": item.value,
                "selected": item == enum_instance,
            } for item in enum_instance.__class__
        }
    
    
    def add_websocket_endpoint(self, url: str, function: callable):
        """
        Adds a WebSocket endpoint to the FastAPI app.

        Args:
            url (str): The URL path for the WebSocket endpoint.
            function (callable): [MUST BE ASYNC] The result of this function is sent to the client.
        """

        self.websocket_endpoints[url] = WebsocketEndpoint(url, function)
        
        @self.app.websocket(url)
        async def websocket_endpoint(websocket: WebSocket):
            """
			WebSocket endpoint that polls the provided async function and sends data to connected clients.

			Args:
				websocket (WebSocket): WebSocket connection object.
			"""
            await websocket.accept()
            try:
                while True:
                    data = await function()
                    for key, value in data.items():
                        if isinstance(value, Enum):
                            data[key] = APIServer._enum_to_selected_dict(value)
                    await websocket.send_json(data)
            except WebSocketDisconnect:
                logger.debug("[FastApi] Client disconnected")
            except ConnectionClosedOK:
                logger.debug("[FastApi] Connection closed normally")
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                await websocket.close()
        
        logger.debug(f"WebSocket endpoint added at {url}")
            
    
    def setup(self):
        """
        Sets up the API server. This method is called before running the server.
        """
        logger.debug(f"[FastApi] Server setup started at {self.host}:{self.port}")
        logger.debug("[FastApi] Server setup completed")
        
        
    def run(self):
        """
        A coroutine that runs the FastAPI server.
        """
        try:
            config = uvicorn.Config(
                self.app,
                host=self.host,
                port=self.port,
                log_level="warning",
            )
            server = uvicorn.Server(config)
            return server.serve()
        except Exception as e:
            # Log the exception or handle it as needed
            logger.error(f"An error occurred while running the server: {e}")
            return None
        
        
    def teardown(self):
        """
        Cleans up the API server. This method is called after the server has stopped.
        """
        logger.debug("[FastApi] Server teardown started")
        logger.debug("[FastApi] Server teardown completed")
        
        
    def register_endpoints(self, api_server):
        """
        Registers endpoints to the FastAPI app. This method should be called to add any custom endpoints.
        """
        
        @api_server.app.get("/ping")
        async def ping() -> DictResponse:
            """
            Endpoint to check if the API server is running.
            """
            return DictResponse(
                status=200,
                data={"message": "Pong!"},
            )
        
    