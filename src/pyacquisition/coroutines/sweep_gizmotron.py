from ..instruments import Gizmotron
from ..scribe import Scribe
from ._coroutine import Coroutine


import asyncio
from dataclasses import dataclass



@dataclass
class SweepGizmotron(Coroutine):

	scribe: Scribe
	gizmo: Gizmotron
	max_value: float
	wait_time: float = 1
	from_cache: bool = False


	def string(self):
		return f'SweepGizmotron up to {self.max_value}'


	async def run(self):

		yield ''

		await asyncio.sleep(self.wait_time)
		self.scribe.next_file('Up Positive', new_chapter=True)
		await asyncio.sleep(self.wait_time)

		self.gizmo.set_setpoint(self.max_value)
		while self.gizmo.get_value(from_cache=self.from_cache) < self.max_value:
			await asyncio.sleep(self.wait_time)

		yield ''

		await asyncio.sleep(self.wait_time)
		self.scribe.next_file('Down Positive')
		await asyncio.sleep(self.wait_time)

		self.gizmo.set_setpoint(0)
		while self.gizmo.get_value(from_cache=self.from_cache) > 0:
			await asyncio.sleep(self.wait_time)

		yield ''

		await asyncio.sleep(self.wait_time)
		self.scribe.next_file('Up Negative')
		await asyncio.sleep(self.wait_time)

		self.gizmo.set_setpoint(-self.max_value)
		while self.gizmo.get_value(from_cache=self.from_cache) > -self.max_value:
			await asyncio.sleep(self.wait_time)

		yield ''

		await asyncio.sleep(self.wait_time)
		self.scribe.next_file('Down Negative')
		await asyncio.sleep(self.wait_time)

		self.gizmo.set_setpoint(0)
		while self.gizmo.get_value(from_cache=self.from_cache) < 0:
			await asyncio.sleep(self.wait_time)

		await asyncio.sleep(self.wait_time)
		self.scribe.next_file('Teardown')

		yield ''




