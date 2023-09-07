import asyncio


class InspectableQueue:
	"""
	A wrapper for the asyncio.Queue that allows for inspection
	of items.
	"""


	def __init__(self):

		self.queue = asyncio.Queue()


	async def put(self, item):
		"""
		Put item onto the queue once granted control

		:param      item:  The item
		:type       item:  { type_description }
		"""
		await self.queue.put(item)


	def put_nowait(self, item):
		"""
		Put item onto the queue immediately

		:param      item:  The item
		:type       item:  { type_description }
		"""

		self.queue.put_nowait(item)


	async def get(self):
		"""
		Get the next item from the queue

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return await self.queue.get()


	def clear(self):
		"""
		Clear the queue
		"""
		self.queue._queue.clear()


	def inspect(self):
		"""
		Return a list of items from the queue

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return list(self.queue._queue)


	def insert(self, item, index):
		"""
		Insert an item into the queue at provided index

		:param      item:   The item
		:type       item:   { type_description }
		:param      index:  The index
		:type       index:  { type_description }

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		queue_list = list(self.queue._queue)
		queue_list.insert(index, item)
		self.clear()
		for item in queue_list:
			self.put_nowait(item)
		return item


	def remove(self, index):
		"""
		Remove the item from the queue at the provided index

		:param      index:  The index
		:type       index:  { type_description }

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		queue_list = list(self.queue._queue)
		popped = None
		if queue_list:
			popped = queue_list.pop(index)
		self.clear()
		for item in queue_list:
			self.put_nowait(item)
		return popped

