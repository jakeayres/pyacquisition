from .consumer import Consumer
from .broadcaster import Broadcaster
from .logging import logger
import asyncio


class Relay(Broadcaster, Consumer):
    """
    A class the both consumes and broadcasts messages between different components.
    """

    def __init__(self, callbacks=[], async_callbacks=[]):
        """
        Initialize the Relay.
        """
        self.queue = asyncio.Queue()
        self._subscribers = []
        self._callbacks = []
        self._async_callbacks = []

    async def relay(self, timeout=None):
        """
        Relay messages between consumers and broadcasters.
        """
        try:
            message = await self.consume(timeout=timeout)
            await self.broadcast(message)
            return message
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error relaying message: {e}")
            return None
