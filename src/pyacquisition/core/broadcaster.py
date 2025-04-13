import asyncio

class Broadcaster:
    """
    A class responsible for broadcasting messages to subscribed consumers.
    """

    def __init__(self):
        """
        Initialize the Broadcaster.
        """
        self._subscribers = []


    def subscribe(self, consumer):
        """
        Subscribe a consumer to this broadcaster.

        Args:
            consumer (Consumer): The consumer to subscribe.
        """
        self._subscribers.append(consumer)
        
        
    def unsubscribe(self, consumer):
        """
        Unsubscribe a consumer from this broadcaster.

        Args:
            consumer (Consumer): The consumer to unsubscribe.
        """
        self._subscribers.remove(consumer)
        

    async def broadcast(self, message):
        """
        Broadcast a message to all subscribed consumers.

        Args:
            message (Any): The message to broadcast.
        """
        for subscriber in self._subscribers:
            await subscriber.queue.put(message)