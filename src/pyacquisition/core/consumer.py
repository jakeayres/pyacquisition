import asyncio
from .logging import logger


class Consumer:
    """
    A consumer class that can subscribe and unsubscribe to a Broadcaster.
    """

    def __init__(self, callbacks=[], async_callbacks=[]):
        """
        Initialize the Consumer.
        """
        self.queue = asyncio.Queue()
        self._callbacks = callbacks
        self._async_callbacks = async_callbacks
        
        
    def _execute_callbacks(self, message):
        """
        Execute all registered callbacks with the given message.

        Args:
            message (Any): The message to pass to the callbacks.
        """
        for callback in self._callbacks:
            callback(message)
            
            
    async def _execute_async_callbacks(self, message):
        """
        Execute all registered async callbacks with the given message.

        Args:
            message (Any): The message to pass to the async callbacks.
        """
        for async_callback in self._async_callbacks:
            await async_callback(message)
            
            
    def add_callback(self, callback):
        """
        Add a callback to be executed when a message is consumed.

        Args:
            callback (callable): The callback function to add.
        """
        self._callbacks.append(callback)
        
        
    def remove_callback(self, callback):
        """
        Remove a callback from the list of callbacks.

        Args:
            callback (callable): The callback function to remove.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
        
        
    def add_async_callback(self, async_callback):
        """
        Add an async callback to be executed when a message is consumed.

        Args:
            async_callback (callable): The async callback function to add.
        """
        self._async_callbacks.append(async_callback)
        
        
    def remove_async_callback(self, async_callback):
        """
        Remove an async callback from the list of async callbacks.

        Args:
            async_callback (callable): The async callback function to remove.
        """
        if async_callback in self._async_callbacks:
            self._async_callbacks.remove(async_callback)
        

    def subscribe_to(self, broadcaster):
        """
        Subscribe to a Broadcaster.

        Args:
            broadcaster (Broadcaster): The broadcaster to subscribe to.
        """
        broadcaster.subscribe(self)

        
    def unsubscribe(self, broadcaster):
        """
        Unsubscribe from a Broadcaster.

        Args:
            broadcaster (Broadcaster): The broadcaster to unsubscribe from.
        """
        broadcaster.unsubscribe(self)   


    async def consume(self, timeout=None):
        """
        Consume a single message from the queue with a timeout.

        Args:
            timeout (float or None): The maximum time (in seconds) to wait for a message. Defaults to None (no timeout).

        Returns:
            Any: The message from the queue, or None if the timeout is reached.
        """
        try:
            message = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            self._execute_callbacks(message)
            await self._execute_async_callbacks(message)
            return message
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error consuming message: {e}")
            return None
        
        
    async def consume_all(self, timeout=None):
        """
        Consume all messages from the queue with a timeout.

        Args:
            timeout (float or None): The maximum time (in seconds) to wait for messages. Defaults to None (no timeout).

        Returns:
            list: A list of messages from the queue.
        """
        messages = []
        while True:
            message = await self.consume(timeout=timeout)
            if message is None:
                break
            messages.append(message)
        return messages