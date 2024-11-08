import asyncio
from .inspectable_queue import InspectableQueue


class Consumer:
	"""A consumer class that can subscribe and unsubsribe to a Broadcaster """

	def __init__(self):
		self._queue = InspectableQueue()


	def subscribe_to(self, broadcaster: 'Broadcaster') -> None:
		"""Subscribe to a Broadcaster.

		Args:
			broadcaster (Broadcaster): The broadcaster to subscribe to.
		"""
		broadcaster.subscribe(self)


	def unsubscribe_to(self, broadcaster: 'Broadcaster') -> None:
		"""Unsubscribe from a broadcaster

		Args:
			broadcaster (Broadcaster): The broadcaster to unsubscribe from.
		"""
		broadcaster.unsubscribe(self)


	async def get_from_queue(self):
		"""Get result from queue

		"""
		return await self._queue.get()
