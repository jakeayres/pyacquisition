import asyncio
from .rack import Rack
from .scribe import Scribe
from .graph import Graph
from .consumer import Consumer
from .websocket_server import WebSocketServer
from .inspectable_queue import InspectableQueue
from .api import API


class Experiment:

	def __init__(self, root):
		self.rack = Rack()
		self.scribe = Scribe(root=root)
		self.scribe.subscribe_to(self.rack)
		self.ws_server = WebSocketServer("localhost", 8765)
		self.ws_server.subscribe_to(self.rack)
		self._api = API(allowed_cors_origins=['http://localhost:3000'])
		self._api.subscribe_to(self.rack)

		self.running = True
		self.pause_event = asyncio.Event()
		self.current_task = None
		self.current_task_string = None
		self.task_queue = InspectableQueue()

		self.setup()
		self.register_endpoints()


	@property
	def api(self):
		return self._api.app


	def add_software_instrument(self, key, instrument_class):
		inst = self.rack.add_software_instrument(key, instrument_class)
		inst.register_endpoints(self.api)
		return inst


	def add_hardware_instrument(self, key, instrument_class, visa_resource):
		inst = self.rack.add_instrument(key, instrument_class, visa_resource)
		inst.register_endpoints(self.api)
		return inst


	def add_measurement(self, key, func):
		meas = self.rack.add_measurement(key, func)
		return func


	async def add_task(self, task):
		await self.task_queue.put(task)
		self.scribe.log(f'Task added : {task.string()}')


	async def get_task(self):
		task = await self.task_queue.get()
		self.scribe.log(f'Task retrieved : {task.string()}')
		return task


	def remove_task(self, index):
		task = self.task_queue.remove(index)
		self.scribe.log(f'Task {index} removed : {task.string()}')


	def insert_task(self, task, index):
		task = self.task_queue.insert(task, index)
		self.scribe.log(f'Task inserted {index} : {task.string()}')


	def list_tasks(self):
		return [t.string() for t in self.task_queue.inspect()]


	def clear_tasks(self):
		self.task_queue.clear()
		self.scribe.log(f'All tasks cleared')


	def pause_task(self):
		self.current_task.pause()
		self.scribe.log('Currnet task paused')


	def resume_task(self):
		self.current_task.resume()
		self.scribe.log('Current task resumed')


	def abort_task(self):
		self.current_task.abort()
		self.scribe.log(f'Current task aborted')


	def setup(self):
		""" OVERIDE IN INHERETING CLASS

		Add instruments and measurements in here
		"""
		pass


	async def execute(self):
		
		while self.running:

			self.current_task = None
			task = await self.get_task()
			self.current_task = task

			if asyncio.iscoroutinefunction(task.coroutine):
				await task.coroutine()

			elif asyncio.iscoroutine(task.coroutine):
				await task.coroutine

			else:
				async for _ in task.coroutine():
					pass


	def register_endpoints(self):
		""" OVERIDE IN INHERETING CLASS

			CALL SUPER() to keep the below functionality
		"""


		@self.api.get('/experiment/current_task', tags=['Experiment'])
		async def current_task() -> str:
			try:
				return self.current_task.string()
			except:
				return 'None'


		@self.api.get('/experiment/pause/', tags=['Experiment'])
		async def pause_task() -> int:
			self.pause_task()
			return 0


		@self.api.get('/experiment/resume/', tags=['Experiment'])
		async def resume_task() -> int:
			self.resume_task()
			return 0


		@self.api.get('/experiment/abort/', tags=['Experiment'])
		async def abort_task() -> int:
			self.abort_task()
			return 0


		@self.api.get('/experiment/queued_tasks/', tags=['Experiment'])
		async def queued_tasks() -> list[str]:
			return self.list_tasks()


		@self.api.get('/experiment/remove_task/{index}/', tags=['Experiment'])
		async def remove_task(index: int) -> int :
			self.remove_task(index)
			return 0


		@self.api.get('/experiment/clear_tasks/', tags=['Experiment'])
		async def clear_tasks() -> int:
			self.clear_tasks()
			return 0


		@self.api.get('/experiment/wait_for/{mins}/{secs}', tags=['Experiment'])
		async def wait_for(mins: int = 0, secs: int = 0) -> int:
			self.add_task(WaitFor(self.scribe, minutes=mins, seconds=secs))
			return 0


		self.rack.register_endpoints(self.api)
		self.scribe.register_endpoints(self.api)


	async def run(self):

		rack_task = asyncio.create_task(self.rack.run())
		scribe_task = asyncio.create_task(self.scribe.run())
		ws_task = asyncio.create_task(self.ws_server.run())
		main_task = asyncio.create_task(self.execute())
		fast_api_server_task = self._api.coroutine()

		self.scribe.log('Experiment started')
		
		done, pending = await asyncio.wait(
			[
			scribe_task,
			rack_task,
			ws_task,
			main_task,
			fast_api_server_task,
			],
			return_when=asyncio.FIRST_COMPLETED,
		)

		for task in pending:
			task.cancel()

		self.scribe.log('Experiment complete')

