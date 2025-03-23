import asyncio
from datetime import datetime
from functools import partial

from .logger import logger
from .rack import Rack
from .scribe import Scribe, scribe
from .consumer import Consumer
from .inspectable_queue import InspectableQueue
from .api import API
from .coroutines import WaitFor
from .dataframe import DataFrame
from .task_manager import TaskManager
from .dataframe import DataFrameManager
from .ui.ui import UI



class Experiment:

	def __init__(self, root):
		#self._logger = logger()

		self._rack = Rack()
		scribe.set_root_directory(root)
		scribe.subscribe_to(self.rack)
		self._api = API(allowed_cors_origins=['http://localhost:3000'])
		self._api.subscribe_to(self.rack)
		self._api.subscribe_to(logger)
		self._ui = UI()

		self.task_manager = TaskManager()
		self.dataframe_manager = DataFrameManager()

		self.setup()
		self.register_endpoints()


	@property
	def logger(self):
		"""
		Logger instance handling instruments and measurements

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return self._logger


	@property
	def rack(self):
		"""
		Rack instance handling instruments and measurements

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return self._rack


	@property
	def scribe(self):
		"""
		Scribe instance handling file io

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return self._scribe


	@property
	def api(self):
		"""
		API instance running the FastAPI webserver

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return self._api.app


	def add_software_instrument(self, key: str, instrument_class, *args, **kwargs):
		"""
		Adds a software instrument to the Rack.

		:param      key:               The key
		:type       key:               { type_description }
		:param      instrument_class:  The instrument class
		:type       instrument_class:  { type_description }

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		inst = self.rack.add_software_instrument(key, instrument_class, *args, **kwargs)
		inst.register_endpoints(self.api)
		return inst


	def add_hardware_instrument(self, key: str, instrument_class, visa_resource, *args, **kwargs):
		"""
		Adds a hardware instrument to the rack.

		:param      key:               The key
		:type       key:               { type_description }
		:param      instrument_class:  The instrument class
		:type       instrument_class:  { type_description }
		:param      visa_resource:     The visa resource
		:type       visa_resource:     { type_description }

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		inst = self.rack.add_instrument(key, instrument_class, visa_resource, *args, **kwargs)
		inst.register_endpoints(self.api)
		return inst


	def add_measurement(self, key: str, func: callable, call_every=1, **kwargs):
		"""
		Add a measurement (callable) to be polled by the Rack object.

		:param      key:         The key
		:type       key:         { type_description }
		:param      func:        The function
		:type       func:        { type_description }
		:param      call_every:  The call every
		:type       call_every:  int

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		meas = self.rack.add_measurement(key, partial(func, **kwargs), call_every=call_every)
		return partial(func, **kwargs)


	# def create_dataframe(self):
	# 	"""
	# 	Instantiate a dataframe (consumer) object that is subscribed to the rack.
		
	# 	:returns:   the dataframe
	# 	:rtype:     DataFrame
	# 	"""
	# 	dataframe = DataFrame(self.rack.measurement_keys)
	# 	dataframe.subscribe_to(self.rack)
	# 	return dataframe



	async def add_task(self, task):
		await self.task_manager.add_task(task)


	async def get_task(self):
		task = await self.task_manager.get_task()
		return task


	def remove_task(self, index):
		self.task_manager.remove_task(index)


	def insert_task(self, task, index):
		self.task_manager.insert_task(task, index)


	def list_tasks(self):
		return self.task_manager.list_tasks()


	def clear_tasks(self):
		self.task_manager.clear_tasks()


	def pause_task(self):
		self.task_manager.pause_task()


	def resume_task(self):
		self.task_manager.resume_task()


	async def execute_task(self, task):
		self.task_manager.execute_task(task)


	def abort_task(self):
		self.task_manager.abort_task()


	def register_endpoints(self):
		""" 
		OVERIDE IN INHERETING CLASS

		Add endpoints to the FastAPI api.

		CALL SUPER() to keep the below functionality
		"""


		from .coroutines import WaitFor
		WaitFor.register_endpoints(self)

		from .coroutines import CreateNewFile
		CreateNewFile.register_endpoints(self)

		self.task_manager.register_endpoints(self.api)
		self.dataframe_manager.register_endpoints(self.api)
		logger.register_endpoints(self.api)
		self.rack.register_endpoints(self.api)
		scribe.register_endpoints(self.api)


	def setup(self):
		"""
		OVERIDE IN INHERETING CLASS

		Intended to be called prior run()
		Add instruments and measurements in here
		"""
		pass


	def run(self):
		"""
		The main entry point for the Experiment class
		"""
		asyncio.run(self._async_run())


	async def _async_run(self):
		"""
		The main asyncio method
		"""

		logger.debug('Entered main async task')

		rack_task = asyncio.create_task(self.rack.run())
		scribe_task = asyncio.create_task(scribe.run())
		main_task = asyncio.create_task(self.task_manager.execute())
		dataframe_task = asyncio.create_task(self.dataframe_manager.run())
		fast_api_server_task = self._api.coroutine()

		logger.info('Experiment started')

		ui_process = self._ui.run_in_new_process()

		logger.debug('UI started in new process')
		
		done, pending = await asyncio.wait(
			[
			rack_task,
			main_task,
			dataframe_task,
			scribe_task,
			fast_api_server_task,
			],
			return_when=asyncio.FIRST_COMPLETED,
		)

		logger.debug('Ending tasks and joining processes')

		for task in pending:
			task.cancel()
		ui_process.join()

		logger.info('Experiment ended')