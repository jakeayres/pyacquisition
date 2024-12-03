from ..logger import logger
from ..scribe import scribe
from .coroutine import Coroutine

import asyncio
import numpy as np
from dataclasses import dataclass


@dataclass
class CreateNewFile(Coroutine):

	filename: str
	new_chapter: bool = False
	wait_time: float = 1.0


	def string(self):
		return f"Create new file: {self.filename}"


	async def run(self):

		yield ''

		try:
			await asyncio.sleep(self.wait_time)
			scribe.next_file(self.filename, new_chapter=self.new_chapter)

		except Exception as e:
			logger.error('Error creating new file')
			print(e)
			raise e

		finally:
			yield ''



	@classmethod
	def register_endpoints(
		cls, 
		experiment,
		):

		@experiment.api.get('/experiment/create_new_file/', tags=['Routines'])
		async def create_new_file(
			filename: str,
			new_chapter: bool = False,
			) -> int:
			""" Create a new file"""
			await experiment.add_task(
				cls(
					filename=filename,
					new_chapter=new_chapter,
					)
				)
			return 0