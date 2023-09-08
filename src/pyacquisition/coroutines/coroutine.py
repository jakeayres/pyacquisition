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
		"""
		Coroutine description. Expected to be overidden.

		:returns:   Descriptive string
		:rtype:     str
		"""
		return f'Base coroutine'


	def status(self):
		return {
			'name': self.string(),
			'pause_raised': self.pause_raised(),
			'paused': self.is_paused()
		}


	async def coroutine(self):
		""" 
		The main entry point to execute the Coroutine.
		Step through run() generator and check flags at each yield.
		This is the method that is ultimately called by the Experiment class.

		"""
		returns = {}
		async for step in self.run():

			if isinstance(step, dict):
				returns.update(step)

			if self._abort_event.is_set():
				return  # or raise an exception
			self._is_paused = True
			await self._pause_event.wait()
			self._is_paused = False
		return returns


	async def execute(self):

		try:
			return await self.coroutine()

		except Exception as e:
			print(f'Exception raised executing this coroutine')
			print(e)
			raise e


	async def execute_another_coroutine(self, coroutine):
		"""
		Execute a provided coroutine within this coroutine
		
		:param      coroutine:  The coroutine
		:type       coroutine:  { type_description }
		"""
		try:
			return await coroutine.coroutine()

		except Exception as e:
			print(f'Exception raised executing child coroutine')
			print(e)
			raise e


	async def execute_concurrent_coroutines(self, coroutines: list):
		try:
			return await asyncio.gather(*[c.coroutine() for c in coroutines])

		except Exception as e:
			print(f'Exception raised executing concurrent child coroutines')
			print(e)
			raise e




	async def run(self):
		""" run() is to be overwriten in inheriting
		classes. Must be a generator method (ie yields stuff)
		"""
		yield ''


	def pause(self):
		"""
		Clear the pause event
		"""
		self._pause_event.clear()


	def resume(self):
		"""
		Set the pause event
		"""
		self._pause_event.set()


	def abort(self):
		"""
		Set the pause event
		"""
		self._abort_event.set()


	def pause_raised(self):
		"""
		Return whether a pause event has been raised

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return not self._pause_event.is_set()


	def is_paused(self):
		"""
		Return whether the task is paused

		:returns:   True if paused, False otherwise.
		:rtype:     bool
		"""
		return self._is_paused


	@classmethod
	def register_endpoints(cls, app, experiment):
		"""
		Overide this function in inheriting classes
		"""
		pass
