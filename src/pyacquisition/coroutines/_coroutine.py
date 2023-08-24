import asyncio
from dataclasses import dataclass, field

from ..scribe import Scribe


@dataclass
class Coroutine:

	_pause_event: asyncio.Event = field(init=False)
	_abort_event: asyncio.Event = field(init=False)
	_is_paused: bool = field(init=False, default=False)


	def __post_init__(self):
		self._pause_event = asyncio.Event()
		self._pause_event.set()
		self._abort_event = asyncio.Event()
		self._is_paused = False
		self._status_message = ''


	def string(self):
		return f'Base coroutine'


	def status(self):
		return {
			'name': self.string(),
			'pause_raised': self.pause_raised(),
			'paused': self.is_paused()
		}


	async def coroutine(self):
		""" Step through generator (run()) and check
		flags at each yield.
		"""
		async for step in self.run():
			if self._abort_event.is_set():
				return  # or raise an exception
			_is_paused = True
			await self._pause_event.wait()
			_is_paused = False


	async def run(self):
		""" run() is to be overwriten in inheriting
		classes. Must be a generator method (ie yields stuff)
		"""

		self.scribe.log('started')

		self.scribe.log('running 1')
		await asyncio.sleep(3)
		yield ''
		self.scribe.log('running 2')
		await asyncio.sleep(3)
		yield ''
		self.scribe.log('running 3')
		await asyncio.sleep(3)
		yield ''
		self.scribe.log('running 4')
		await asyncio.sleep(3)
		yield ''

		self.scribe.log('finished')


	def pause(self):
		self._pause_event.clear()


	def resume(self):
		self._pause_event.set()


	def abort(self):
		self._abort_event.set()


	def pause_raised(self):
		return not self._pause_event.is_set()


	def is_paused(self):
		return self._is_paused
