from ..scribe import Scribe

import asyncio
from datetime import datetime
from dataclasses import dataclass


async def pause(
	scribe: Scribe, 
	period=1
	):
	scribe.log(f'Pausing for {period} s')
	await asyncio.sleep(period)


@dataclass
class PauseFor:

	scribe: Scribe
	minutes: int = 0
	seconds: int = 0


	def string(self):
		return f'Pausing for {self.minutes}m {self.seconds}s'


	async def coroutine(self):
		self.scribe.log(self.string())
		await asyncio.sleep(self.minutes*60 + self.seconds)


@dataclass
class PauseUntil:

	scribe: Scribe
	date_time: datetime


	def string(self):
		return f'Pausing until {self.date_time}'


	async def coroutine(self):
		self.scribe.log(self.string())
		while datetime.now() < self.date_time:
			await asyncio.sleep(2)


