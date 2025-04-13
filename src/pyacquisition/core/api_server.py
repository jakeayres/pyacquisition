from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from .logging import logger



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
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        logger.debug("APIServer initialized")
            
        
        
    def coroutine(self):
        """
        A coroutine that runs the FastAPI server.
        """
        try:
            config = uvicorn.Config(
                self.app,
                host=self.host,
                port=self.port,
            )
            server = uvicorn.Server(config)
            return server.serve()
        except Exception as e:
            # Log the exception or handle it as needed
            logger.error(f"An error occurred while running the server: {e}")
            return None