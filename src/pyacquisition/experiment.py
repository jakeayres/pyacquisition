import asyncio
from .rack import Rack
from .scribe import Scribe
from .graph import Graph
from .consumer import Consumer
from .websocket_server import WebSocketServer
from .api import API


class Experiment:

	def __init__(self, root):
		self.rack = Rack()
		self.scribe = Scribe(root=root)
		self.scribe.subscribe_to(self.rack)
		self.ws_server = WebSocketServer("localhost", 8765)
		self.ws_server.subscribe_to(self.rack)
		self._api = API(allowed_cors_origins=['http://localhost:3000/'])
		self._api.subscribe_to(self.rack)

		self.pause_event = asyncio.Event()

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


	def setup(self):
		""" OVERIDE IN INHERETING CLASS

		Add instruments and measurements in here
		"""
		pass


	async def pause(self):
		self.pause_event.set()


	async def resume(self):
		self.pause_event.clear()


	async def execute(self):
		""" OVERIDE IN INHERETING CLASS

		The main measurement coroutine
		"""
		pass


	def register_endpoints(self):
		""" OVERIDE IN INHERETING CLASS

			CALL SUPER() to keep the below functionality
		"""

		@self.api.get('/experiment/pause', tags=['Experiment'])
		def pause() -> str:
			return self.pause()

		@self.api.get('/experiment/resume', tags=['Experiment'])
		def resume() -> str:
			return self.resume()

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

