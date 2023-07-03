from typing import Any


class Broadcaster:
	"""A broadcaster class that can emit data to subscribed consumers."""

	def __init__(self):
		self._consumer_queues = set()


	def subscribe(self, consumer: 'Consumer') -> None:
		"""Subscribe a consumer to receive emitted data.

		Args:
			consumer (Consumer): The consumer to subscribe
		"""
		self._consumer_queues.add(consumer._queue)


	def unsubscribe(self, consumer: 'Consumer') -> None:
		"""Unsubscribe a consumer from receiving emitted data.

		Args:
			consumer (Consumer): The consumer to unsubscribe.
		"""
		self._consumer_queues.remove(consumer._queue)


	def emit(self, item: Any) -> None:
		"""Put data (item) on the queues of subscribed consumers.

		Args:
			item (Any): The data to send to consumers.
		"""
		for queue in self._consumer_queues:
			queue.put_nowait(item)