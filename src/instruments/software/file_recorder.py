from ...instruments._instrument import SoftInstrument, query, command
import time, enum
import numpy as np
import os

from typing import Callable



class FileRecorder(SoftInstrument):


	def __init__(self):
		super().__init__()

		self._directory = None
		self._filestem = None
		self._filenumber = 0
		self._extension = 'data'

		self._recorded_methods = {
			'time': f'{time.time():.1}'
		}
		self._running = False


	@property
	def _filenumber_string(self):
		return f'{self._filenumber:04}'


	@property
	def _full_filename(self):
		return f'{self._filestem}_{self._filenumber_string}.{self._extension}'


	@property
	def _full_filepath(self):
		return f'{self._directory}/{self._full_filename}'


	@query
	def get_directory(self) -> str:
		return str(self._directory)


	@command
	def set_directory(self, directory: str):
		self._directory = directory
		return 0


	@query
	def get_filestem(self) -> str:
		return f'{self._filestem}.{self._extension}'


	@command
	def set_filestem(self, filestem: str):
		self._filestem = filestem
		return 0


	@query
	def get_recorded_methods(self) -> dict:
		return self._recorded_methods


	@command
	def add_recorded_method(self, key: str, func: Callable):
		self._recorded_methods[key] = func
		return 0


	@command
	def record(self):
		pass