import asyncio

class Broadcaster:
    """
    A class responsible for broadcasting messages to subscribed consumers.
    """

    def __init__(self):
        self._subscribers = []

    def subscribe(self, consumer):
        """
        Subscribe a consumer to this broadcaster.

        :param consumer: The consumer to subscribe.
        """
        self._subscribers.append(consumer)

    async def broadcast(self, message):
        """
        Broadcast a message to all subscribed consumers.

        :param message: The message to broadcast.
        """
        for subscriber in self._subscribers:
            await subscriber.queue.put(message)