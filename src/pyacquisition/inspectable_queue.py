import asyncio


class InspectableQueue:


	def __init__(self):

		self.queue = asyncio.Queue()


	async def put(self, item):
		await self.queue.put(item)


	def put_nowait(self, item):
		self.queue.put_nowait(item)


	async def get(self):
		return await self.queue.get()


	def clear(self):
		self.queue._queue.clear()


	def inspect(self):
		return list(self.queue._queue)


	def insert(self, item, index):
		queue_list = list(self.queue._queue)
		queue_list.insert(index, item)
		self.clear()
		for item in queue_list:
			self.put_nowait(item)
		return item


	def remove(self, index):
		queue_list = list(self.queue._queue)
		popped = None
		if queue_list:
			popped = queue_list.pop(index)
		self.clear()
		for item in queue_list:
			self.put_nowait(item)
		return popped

