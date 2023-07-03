import asyncio


class Consumer:
	"""A consumer class that can subscribe and unsubsribe to a Broadcaster """

	def __init__(self):
		self._queue = asyncio.Queue()


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
