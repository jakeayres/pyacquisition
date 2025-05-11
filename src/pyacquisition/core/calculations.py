from .broadcaster import Broadcaster
from .consumer import Consumer
from .logging import logger
import asyncio

class Calculations(Broadcaster, Consumer):
    """
    A class to perform calculations on the live data.
    """
    
    def __init__(self, callbacks=[], async_callbacks=[]):
        """
        Initialize the Relay.
        """
        self.queue = asyncio.Queue()
        self._subscribers = []
        self._callbacks = []
        self._async_callbacks = []
        
    
    def setup(self):
        """
        Setup the task manager.
        """
        logger.debug("[Calculations] Setup started")
        logger.debug("[Calculations] Setup completed")

    async def run(self, experiment) -> None:
        
        while True:
            try:
                message = await self.consume()
                await self.broadcast(message)
            except Exception as e:
                logger.error(f"Error in calculator run loop: {e}")
                
                
    def teardown(self):
        """
        Teardown the task manager.
        """
        logger.debug("[Calculations] Teardown started")
        logger.debug("[Calculations] Teardown completed")
        
        
    def _register_endpoints(self, api_server):
        """
        Register the endpoints for the calculations.
        """
        pass