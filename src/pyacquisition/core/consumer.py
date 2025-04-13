import asyncio

class Consumer:
    """
    A consumer class that can subscribe and unsubscribe to a Broadcaster.
    """

    def __init__(self):
        """
        Initialize the Consumer.
        """
        self.queue = asyncio.Queue()


    def subscribe(self, broadcaster):
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
            return message
        except asyncio.TimeoutError:
            return None