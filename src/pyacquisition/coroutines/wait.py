from ..scribe import Scribe
from ..logger import logger
from .coroutine import Coroutine

import asyncio
from datetime import datetime
from dataclasses import dataclass
from dataclasses import dataclass
from pydantic import BaseModel
from fastapi import Depends



class WaitDuration(BaseModel):
	hours: int = 0
	minutes: int = 0
	seconds: int = 0


@dataclass
class WaitFor(Coroutine):

	hours: int = 0
	minutes: int = 0
	seconds: int = 0


	def string(self):
		return f'Pausing for {self.hours}:{self.minutes}:{self.seconds}'


	def _seconds(self):
		return self.hours*60*60 + self.minutes*60 + self.seconds


	async def run(self):
		logger.info(self.string())
		await asyncio.sleep(self._seconds())
		yield ''


	@classmethod
	def register_endpoints(cls, experiment):

		@experiment.api.get('/experiment/wait_for/', tags=['Routines'])
		async def wait_for(duration: WaitDuration = Depends()) -> int:
			""" Wait for given time """
			await experiment.add_task(cls(**duration.dict()))
			return 0


@dataclass
class WaitUntil(Coroutine):

	date_time: datetime


	def string(self):
		return f'Pausing until {self.date_time}'


	async def run(self):
		logger.info(self.string())
		while datetime.now() < self.date_time:
			await asyncio.sleep(1)
		yield ''


