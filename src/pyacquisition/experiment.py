import asyncio
from datetime import datetime
from .rack import Rack
from .scribe import Scribe
from .consumer import Consumer
from .inspectable_queue import InspectableQueue
from .api import API
from .coroutines import WaitFor
from .dataframe import DataFrame

from .ui.ui import UI


class Experiment:

	def __init__(self, root):
		self._rack = Rack()
		self._scribe = Scribe(root=root)
		self._scribe.subscribe_to(self.rack)
		self._api = API(allowed_cors_origins=['http://localhost:3000'])
		self._api.subscribe_to(self.rack)

		#self._ui = UI()

		self.running = True
		self.current_task = None
		self.current_task_string = None
		self.task_queue = InspectableQueue()

		self.setup()
		self.register_endpoints()


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


	def add_software_instrument(self, key: str, instrument_class):
		"""
		Adds a software instrument to the Rack.

		:param      key:               The key
		:type       key:               { type_description }
		:param      instrument_class:  The instrument class
		:type       instrument_class:  { type_description }

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		inst = self.rack.add_software_instrument(key, instrument_class)
		inst.register_endpoints(self.api)
		return inst


	def add_hardware_instrument(self, key: str, instrument_class, visa_resource):
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
		inst = self.rack.add_instrument(key, instrument_class, visa_resource)
		inst.register_endpoints(self.api)
		return inst


	def add_measurement(self, key: str, func: callable, call_every=1):
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
		meas = self.rack.add_measurement(key, func, call_every=call_every)
		return func


	def create_dataframe(self):
		"""
		Instantiate a dataframe (consumer) object that is subscribed to the rack.
		
		:returns:   the dataframe
		:rtype:     DataFrame
		"""
		dataframe = DataFrame(self.rack.measurement_keys)
		dataframe.subscribe_to(self.rack)
		return dataframe



	async def add_task(self, task):
		"""
		Add a task to the end of the task queue

		:param      task:  The task
		:type       task:  { type_description }
		"""
		await self.task_queue.put(task)
		self.scribe.log(f'{task.string()}', stem='Task Added')


	async def get_task(self):
		"""
		Get and return the next task from the queue

		:returns:   The task.
		:rtype:     { return_type_description }
		"""
		task = await self.task_queue.get()
		self.scribe.log(f'{task.string()}', stem='Task Retrieved')
		return task


	def remove_task(self, index):
		"""
		Removes a task from the queue at provided index

		:param      index:  The index
		:type       index:  { type_description }
		"""
		task = self.task_queue.remove(index)
		self.scribe.log(f'{task.string()} ({index})', stem='Task Removed')


	def insert_task(self, task, index):
		"""
		Insert a task into the queue at the provided index

		:param      task:   The task
		:type       task:   { type_description }
		:param      index:  The index
		:type       index:  { type_description }
		"""
		task = self.task_queue.insert(task, index)
		self.scribe.log(f'{task.string()} ({index})', stem="Task Inserted")


	def list_tasks(self):
		"""
		Return a list of task descriptions (not the objects themselves)

		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		return [t.string() for t in self.task_queue.inspect()]


	def clear_tasks(self):
		"""
		Clear all tasks from the queue
		"""
		self.task_queue.clear()
		self.scribe.log(f'All tasks cleared', stem='Tasks Cleared')


	def pause_task(self):
		"""
		Pause the current task
		"""
		self.current_task.pause()
		self.scribe.log('Paused', stem='Experiment')


	def resume_task(self):
		"""
		Resume the current task
		"""
		self.current_task.resume()
		self.scribe.log('Resumed', stem='Experiment')


	async def execute_task(self, task):
		"""
		Execute the provided task

		:param      task:  The task
		:type       task:  { type_description }
		"""
		try:
			await task.execute()
		except Exception as e:
			print(f'Exception raised executing task')
			print(e)
			self.pause_task()


	def abort_task(self):
		"""
		Abort the current task and proceed
		"""

		self.current_task.abort()
		self.scribe.log('Aborted', stem='Aborted')


	async def execute(self):
		"""
		The main coroutine to run that handles the execution of
		tasks from the task_queue.
		"""
		
		while self.running:

			self.current_task = None
			self.current_task = await self.get_task()
			await self.execute_task(self.current_task)


	def register_endpoints(self):
		""" 
		OVERIDE IN INHERETING CLASS

		Add endpoints to the FastAPI api.

		CALL SUPER() to keep the below functionality
		"""


		@self.api.get('/experiment/current_task', tags=['Tasks'])
		async def current_task() -> str:
			try:
				return self.current_task.string()
			except:
				return 'None'


		@self.api.get('/experiment/pause/', tags=['Tasks'])
		async def pause_task() -> int:
			self.pause_task()
			return 0


		@self.api.get('/experiment/resume/', tags=['Tasks'])
		async def resume_task() -> int:
			self.resume_task()
			return 0


		@self.api.get('/experiment/abort/', tags=['Tasks'])
		async def abort_task() -> int:
			self.abort_task()
			return 0


		@self.api.get('/experiment/queued_tasks/', tags=['Tasks'])
		async def queued_tasks() -> list[str]:
			return self.list_tasks()


		@self.api.get('/experiment/remove_task/{index}/', tags=['Tasks'])
		async def remove_task(index: int) -> int :
			self.remove_task(index)
			return 0


		@self.api.get('/experiment/clear_tasks/', tags=['Tasks'])
		async def clear_tasks() -> int:
			self.clear_tasks()
			return 0


		from .coroutines import WaitFor
		WaitFor.register_endpoints(self)


		self.rack.register_endpoints(self.api)
		self.scribe.register_endpoints(self.api)


	def setup(self):
		"""
		OVERIDE IN INHERETING CLASS

		Intended to be called prior run()
		Add instruments and measurements in here
		"""
		pass


	async def run(self):
		"""
		The main entry point for the Experiment class
		"""

		rack_task = asyncio.create_task(self.rack.run())
		scribe_task = asyncio.create_task(self.scribe.run())
		main_task = asyncio.create_task(self.execute())
		fast_api_server_task = self._api.coroutine()
		ui_task = asyncio.create_task(UI().run())

		self.scribe.log('Started', stem='Experiment')
		
		done, pending = await asyncio.wait(
			[
			scribe_task,
			rack_task,
			#ws_task,
			main_task,
			fast_api_server_task,
			ui_task,
			],
			return_when=asyncio.FIRST_COMPLETED,
		)

		for task in pending:
			task.cancel()

		self.scribe.log('Ended', stem='Experiment')

