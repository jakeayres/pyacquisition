import asyncio


class InspectableQueue:


	def __init__(self):

		self.queue = asyncio.Queue()


	async def put(self, item):
		await self.queue.put(item)


	async def get(self):
		return await self.queue.get()


	def inspect(self):
		return list(self.queue._queue)