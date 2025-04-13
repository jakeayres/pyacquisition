import asyncio

class Consumer:
    """
    A class responsible for consuming messages from a broadcaster.
    """

    def __init__(self):
        self.queue = asyncio.Queue()

    def subscribe_to(self, broadcaster):
        """
        Subscribe to a broadcaster.

        :param broadcaster: The broadcaster to subscribe to.
        """
        broadcaster.subscribe(self)

    async def consume(self):
        """
        Consume messages from the queue.
        """
        while True:
            message = await self.queue.get()
            # Process the message (implementation to be added)
            self.queue.task_done()