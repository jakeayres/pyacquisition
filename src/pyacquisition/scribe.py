from .consumer import Consumer
import asyncio, os, datetime
import pandas as pd
import colorama
from rich.console import Console
from rich.text import Text


# WINDOWS SPECIFIC REQUIREMENT
#colorama.init(convert=True)


class Scribe(Consumer):

	LEVEL_CHAR = {
		'info': ('>  ', 'bold green'),
		'warning': ('#  ', 'bold magenta'),
		'error': ('@! ', 'bold red'),
	}


	def __init__(self, root='./'):
		super().__init__()

		self._root = root
		self._chapter = 1
		self._section = 0
		self._title = 'Start up'
		self._data_extension = '.data'
		self._meta_extension = '.meta'
		self._log_extension = '.log'
		self._console = Console()

		self._make_root_directory()
		self._increment_to_non_existant_chapter()
		self._log_new_file()


	@property
	def current_data_filename(self):
		chapter = f'{self._chapter:0{2}}'
		section = f'{self._section:0{2}}'
		return f'{chapter}.{section} {self._title}{self._data_extension}'


	@property
	def current_meta_filename(self):
		chapter = f'{self._chapter:0{2}}'
		section = f'{self._section:0{2}}'
		return f'{chapter}.{section} {self._title}{self._meta_extension}'


	@property
	def full_data_filepath(self):
		return f'{self._root}{self.current_data_filename}'


	@property
	def full_meta_filepath(self):
		return f'{self._root}{self.current_meta_filename}'


	@property
	def full_filelog_filepath(self):
		return f'{self._root}files{self._log_extension}'


	@property 
	def full_log_filepath(self):
		return f'{self._root}log{self._log_extension}'


	def _make_root_directory(self):
		if not os.path.isdir(self._root):
			os.mkdir(self._root)


	def _increment_to_non_existant_chapter(self):
		largest = 0
		for filename in os.listdir(self._root):
			if os.path.isfile(os.path.join(self._root, filename)):
				if filename[:2].isdigit():
					number = int(filename[:2])
					if number > largest:
						largest = number
		self._chapter = largest+1


	def next_section(self):
		self._section += 1


	def next_chapter(self):
		self._chapter += 1
		self._section = 1


	def next_file(self, title, new_chapter=False):
		if new_chapter:
			self.next_chapter()
		else:
			self.next_section()
		self._title = title
		self._log_new_file()


	def _write(self, data):
		df = pd.DataFrame({k: [v] for k, v in data.items()})
		df.to_csv(self.full_data_filepath, mode='w', header=True, index=False)


	def _append(self, data):
		df = pd.DataFrame({k: [v] for k, v in data.items()})
		df.to_csv(self.full_data_filepath, mode='a', header=False, index=False)


	def record(self, data):
		if not os.path.exists(self.full_data_filepath):
			self._write(data)
		else:
			self._append(data)


	def save_meta(self, data):
		with open(self.full_meta_filepath, 'w') as file:
			json.dump(data, file, indent=4, sort_keys=True)


	def log(self, entry, stem='', level='info'):
		if not os.path.exists(self.full_log_filepath):
			mode = 'w'
		else:
			mode = 'a'
		with open(self.full_log_filepath, mode) as file:
			file.write(f'{self._formatted_date} {self._formatted_time} : {entry}\n')

			text = Text.assemble(
				(f" {self._formatted_date} ", "blue"),
				(f"{self._formatted_time}  ", "bold blue"),
				self.LEVEL_CHAR[level],
				(f"{stem.ljust(20)} ", "bold white"),
				(f"{entry}", "dim white")
			)
			self._console.print(text)


	def _log_new_file(self):
		if not os.path.exists(self.full_filelog_filepath):
			mode = 'w'
		else:
			mode = 'a'
		with open(self.full_filelog_filepath, mode) as file:
			file.write(f'{self._formatted_date} {self._formatted_time} : {self.current_data_filename}\n')
			self.log(f'{self.current_data_filename}', stem='New File')


	@property
	def _formatted_time(self):
		return datetime.datetime.now().strftime("%H:%M:%S")


	@property
	def _formatted_date(self):
		return datetime.datetime.now().strftime("%Y-%m-%d")


	def register_endpoints(self, app):

		@app.get('/scribe/current_filename', tags=['Scribe'])
		def current_filename() -> str:
			"""Get current filename
			
			Returns:
			    str: Current filename
			"""
			return self.current_data_filename

		@app.get('/scribe/next_file/{title}/{next_chapter}', tags=['Scribe'])
		def next_file(title: str, next_chapter: bool = False) -> int:
			"""Create a new file.
			
			Args:
			    title (str): File title
			    next_chapter (bool, optional): Increment chapter
			
			Returns:
			    int: Description
			"""
			self.next_file(title, new_chapter=next_chapter)
			return 0

		@app.get('/scribe/log/{entry}', tags=['Scribe'])
		def log(entry: str) -> int:
			"""Log some text
			
			Args:
			    entry (str): Message to log
			
			Returns:
			    int: Description
			"""
			self.log(entry, stem='User Log')
			return 0


	async def run(self): 
		while True:
			x = await self._queue.get()
			self.record(x)
