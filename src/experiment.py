import asyncio
from .rack import Rack
from .scribe import Scribe
from .graph import Graph
from .consumer import Consumer
from .websocket_server import WebSocketServer


class Experiment:

	def __init__(self, root, rack_config):
		self.rack = Rack.from_filepath(rack_config)
		self.scribe = Scribe(root=root)
		self.scribe.subscribe_to(self.rack)
		self.ws_server = WebSocketServer("localhost", 8765)
		self.ws_server.subscribe_to(self.rack)

	
		# Somehow deal with addition of measurement funcs 
		# without explicit declaration here
		self.rack.add_measurement('time', self.rack.clock.time)
		self.rack.add_measurement('value', self.rack.gizmo.get_value)
		self.rack.add_measurement('signal_1', self.rack.wave1.get_signal)
		self.rack.add_measurement('signal_2', self.rack.wave2.get_signal)


	async def execute(self):
		""" OVERIDE IN INHERETING CLASS
		"""
		pass


	async def teardown(self):
		for task in asyncio.all_tasks():
			task.cancel()


	async def run(self):

		rack_task = asyncio.create_task(self.rack.run())
		scribe_task = asyncio.create_task(self.scribe.run())
		ws_task = asyncio.create_task(self.ws_server.run())
		main_task = asyncio.create_task(self.execute())

		
		done, pending = await asyncio.wait(
			[
			scribe_task,
			rack_task,
			ws_task,
			main_task,
			],
			return_when=asyncio.FIRST_COMPLETED,
		)

		for task in pending:
			task.cancel()

		self.scribe.log('Experiment complete')

