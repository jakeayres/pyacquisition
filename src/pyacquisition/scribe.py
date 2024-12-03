from .logger import logger
from .consumer import Consumer
import asyncio, os, datetime
import pandas as pd

from dataclasses import dataclass
from pydantic import BaseModel
from fastapi import Depends



class Scribe(Consumer):
	"""
	A singleton class to manage writing data to files and logging
	to stdout.
	"""

	# LEVEL_CHAR = {
	# 	'info': ('>  ', 'bold green'),
	# 	'warning': ('#  ', 'bold magenta'),
	# 	'error': ('@! ', 'bold red'),
	# }
	
	_instance = None
	_initialized = False


	def __init__(self, root='./'):

		if not self._initialized:
			super().__init__()
			self.subscribe_to(logger)

			self._root = root
			self._chapter = 0
			self._section = 0
			self._label = 'Start up'
			self._data_extension = '.data'
			self._meta_extension = '.meta'
			self._log_extension = '.log'
			self._n_to_skip = 0

			self.set_root_directory(self._root)


	def __new__(cls, *args, **kwargs):
		if not cls._instance:
			cls._instance = super().__new__(cls)
		return cls._instance


	@property
	def current_data_file(self):
		"""
		Name of the current data file

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		chapter = f'{self._chapter:0{2}}'
		section = f'{self._section:0{2}}'
		return f'{chapter}.{section} {self._label}{self._data_extension}'


	@property
	def current_meta_file(self):
		"""
		Name of the current meta file

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		chapter = f'{self._chapter:0{2}}'
		section = f'{self._section:0{2}}'
		return f'{chapter}.{section} {self._label}{self._meta_extension}'


	@property
	def current_data_path(self):
		"""
		The full path to the current data file

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return f'{self._root}{self.current_data_file}'


	@property
	def current_meta_path(self):
		"""
		The full path to the current meta file

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return f'{self._root}{self.current_meta_file}'


	@property
	def current_filelog_path(self):
		"""
		The full path to the log of files

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return f'{self._root}files{self._log_extension}'


	@property 
	def current_log_path(self):
		"""
		The full path to the log file

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return f'{self._root}log{self._log_extension}'


	def _make_root_directory(self):
		if not os.path.isdir(self._root):
			os.mkdir(self._root)


	def _increment_to_non_existant_chapter(self):
		largest = None
		for filename in os.listdir(self._root):
			if os.path.isfile(os.path.join(self._root, filename)):
				if filename[:2].isdigit():
					number = int(filename[:2])
					if (largest is None):
						largest = number
					elif (largest is not None) and (number > largest):
						largest = number
		if largest is None:
			self._chapter = 0
		else:
			self._chapter = largest+1


	def _increment_section(self):
		self._section += 1


	def _increment_chapter(self):
		self._chapter += 1
		self._section = 0


	def set_root_directory(self, root):
		"""
		Sets the root.
		
		:param      root:  The root
		:type       root:  { type_description }
		
		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		self._root = root
		logger.info(f'Root directory changed: {self._root}')
		self._make_root_directory()
		self._increment_to_non_existant_chapter()
		self.increment_file(self._label, new_chapter=True)


	def increment_file(self, label, new_chapter=False):
		"""
		Increment the current file names.

		:param      label:        The label
		:type       label:        { type_description }
		:param      new_chapter:  The new chapter
		:type       new_chapter:  bool
		"""
		if new_chapter:
			self._increment_chapter()
		else:
			self._increment_section()
		self._label = label
		self._log_new_file()


	def next_file(self, *args, **kwargs):
		"""
		Alias for increment_file

		:param      args:    The arguments
		:type       args:    list
		:param      kwargs:  The keywords arguments
		:type       kwargs:  dictionary
		"""
		self.increment_file(*args, **kwargs)



	def _write(self, data):
		df = pd.DataFrame({k: [v] for k, v in data.items()})
		df.to_csv(self.current_data_path, mode='w', header=True, index=False)


	def _append(self, data):
		df = pd.DataFrame({k: [v] for k, v in data.items()})
		df.to_csv(self.current_data_path, mode='a', header=False, index=False)


	def record(self, data: dict):
		"""
		Save data to the current data file
		
		:param      data:  The data
		:type       data:  dict
		"""
		if not os.path.exists(self.current_data_path):
			self._write(data)
		else:
			self._append(data)


	def save_meta(self, data):
		"""
		Saves data to the current meta file.

		:param      data:  The data
		:type       data:  { type_description }
		"""
		with open(self.current_meta_path, 'w') as file:
			json.dump(data, file, indent=4, sort_keys=True)


	def log(self, entry, stem='', level='info'):
		if not os.path.exists(self.current_log_path):
			mode = 'w'
		else:
			mode = 'a'
		with open(self.current_log_path, mode) as file:
			file.write(f'{entry}\n')


	def _log_new_file(self):
		"""
		Appends an entry to the log of files
		"""
		if not os.path.exists(self.current_filelog_path):
			mode = 'w'
		else:
			mode = 'a'
		with open(self.current_filelog_path, mode) as file:
			file.write(f'{self._formatted_date} {self._formatted_time} : {self.current_data_file}\n')
			logger.info(f'New file: {self.current_data_file}')


	@property
	def _formatted_time(self):
		return datetime.datetime.now().strftime("%H:%M:%S")


	@property
	def _formatted_date(self):
		return datetime.datetime.now().strftime("%Y-%m-%d")


	def register_endpoints(self, app):
		""" Register endpoints to the FastAPI app.
		"""

		@app.get('/scribe/current_filename', tags=['Scribe'])
		def current_filename() -> str:
			"""Get current filename
			
			Returns:
			    str: Current filename
			"""
			return self.current_data_file

		@app.get('/scribe/next_file/', tags=['Scribe'])
		def next_file(
			label: str, 
			next_chapter: bool = False,
			) -> int:
			"""Create a new file.
			"""
			self.increment_file(label, new_chapter=next_chapter)
			return 0


	async def run(self): 
		while True:
			x = await self._queue.get()

			if x['message_type'] == 'data':
				self.record(x['data'])
			elif x['message_type'] == 'log':
				self.log(x['data'])
			else:
				logger.error('Message of unknown type received by Scribe')


scribe = Scribe()