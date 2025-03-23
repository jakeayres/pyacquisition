from .broadcaster import Broadcaster
import asyncio, os, json, time, datetime
from pydantic import BaseModel
import colorama
from rich.console import Console
from rich.text import Text


class Entry(BaseModel):

	date: str
	time: str
	level: str
	message: str


class Logger(Broadcaster):
	""" A SINGLETON class for handling the broadcasting of logs around the application.

	This includes:
		1. broadcasting logs to the scribe for writing to file.
		2. broadcasting logs to the web api for retreival by the UI
	"""

	_instance = None
	_initialized = False

	LEVEL_CHAR = {
		'info': ('>  ', 'bold green'),
		'debug': ('>  ', 'bold cyan'),
		'warning': ('!  ', 'bold magenta'),
		'error': ('!! ', 'bold red'),
	}

	def __init__(self):
		if not self._initialized:
			super().__init__()
			self._console = Console()
			self._initialized = True


	def __new__(cls, *args, **kwargs):
		if not cls._instance:
			cls._instance = super().__new__(cls)
		return cls._instance


	@property
	def _formatted_time(self):
		"""Return time in a standard format
		"""
		return datetime.datetime.now().strftime("%H:%M:%S")


	@property
	def _formatted_date(self):
		"""Return date in a standard format
		"""
		return datetime.datetime.now().strftime("%Y-%m-%d")


	def _to_console(self, entry):
		"""
		Outputs a log entry to the console.
		Args:
			entry (LogEntry): The log entry object containing the date, time, level, and message to be logged.
		Returns:
			None
		"""
		
		text = Text.assemble(
			(f" {entry.date} ", "blue"),
			(f"{entry.time}  ", "bold blue"),
			self.LEVEL_CHAR[entry.level],
			(f"{entry.message}", "dim white")
		)
		self._console.print(text)


	def _to_queue(self, entry):
		"""
		Sends a log entry to the queue.

		This method takes a log entry, converts it to a dictionary, and emits it
		with a message type of 'log'.

		Args:
			entry (LogEntry): The log entry to be sent to the queue. It should have
							  a method `dict()` that converts it to a dictionary.
		"""
		self.emit({'message_type': 'log', 'data': entry.dict()})


	def info(self, message):
		"""
		Logs a message with the 'info' level.

		Parameters:
		message (str): The message to be logged.
		"""
		self.log(message, level='info')


	def debug(self, message):
		"""
		Logs a debug message.

		Parameters:
		message (str): The debug message to log.
		"""
		self.log(message, level='debug')


	def warning(self, message):
		"""
		Logs a warning message.

		Parameters:
		message (str): The warning message to be logged.
		"""
		self.log(message, level='warning')


	def error(self, message):
		"""
		Logs an error message.

		Parameters:
		message (str): The error message to log.
		"""
		self.log(message, level='error')


	def log(self, message, level='info'):
		"""
		Logs a message with a specified level.

		Parameters:
		message (str): The message to log.
		level (str): The level of the log entry. Default is 'info'.

		Returns:
		None
		"""
		entry = Entry(
			date=self._formatted_date,
			time=self._formatted_time,
			level=level,
			message=message,
		)
		self._to_console(entry)
		self._to_queue(entry)



	def register_endpoints(self, app):


		@app.get('/logger/log/', tags=['Scribe'])
		def log(entry: str) -> int:
			"""Log some text
			
			Args:
				entry (str): Message to log
			
			Returns:
				int: Description
			"""
			self.info(entry)
			return 0


logger = Logger()