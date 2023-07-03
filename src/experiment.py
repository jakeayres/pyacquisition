import asyncio
from .rack import Rack
from .scribe import Scribe
from .graph import Graph
from .consumer import Consumer


from quart import Quart
import json

class Server(Consumer):


	def __init__(self):
		super().__init__()
		self.app = Quart(__name__)
		self.configure()


	def configure(self):
		pass


	def register_routes(self):

		@self.app.route('/')
		async def hello():
			return 'hELLO Message'


		@self.app.route('/stream')
		async def stream():
			while True:
				x = await self._queue.get()
				print(x)
				yield json.dumps(x)


	async def run(self, host='localhost', port=5000):
		self.register_routes()
		await self.app.run_task(host=host, port=port)



class Experiment:

	def __init__(self, root, rack_config):
		self.rack = Rack.from_filepath(rack_config)
		
		self.scribe = Scribe(root='./data/')
		self.scribe.subscribe_to(self.rack)

		self.server = Server()
		self.server.subscribe_to(self.rack)

		self.graphs = set()
		self.graph_tasks = set()
	
		# Somehow deal with addition of measurement funcs 
		# without explicit declaration here
		self.rack.add_measurement('time', self.rack.clock.time)
		self.rack.add_measurement('value', self.rack.gizmo.get_value)
		self.rack.add_measurement('signal_1', self.rack.wave1.get_signal)
		self.rack.add_measurement('signal_2', self.rack.wave2.get_signal)


	def add_graph(self, x, y):
		graph = Graph()
		self.graphs.add(graph)
		return graph


	def add_async_graph(self, x, y):
		graph = self.add_graph(x, y)
		graph.subscribe_to(self.rack)
		self.graph_tasks.add(
			asyncio.create_task(graph.run(x, y))
		)
		return graph


	async def execute(self):
		""" OVERIDE IN INHERETING CLASS
		"""
		pass


	async def teardown(self):
		for task in asyncio.all_tasks():
			task.cancel()


	async def run(self):

		self.scribe_task = asyncio.create_task(self.scribe.run())
		self.rack_task = asyncio.create_task(self.rack.run())
		self.main_task = asyncio.create_task(self.execute())
		self.server_task = asyncio.create_task(self.server.run())

		try:
			done, pending = await asyncio.wait(
				[
				self.scribe_task,
				self.rack_task,
				self.main_task,
				#self.server_task,
				*(task for task in self.graph_tasks),
				],
				return_when=asyncio.FIRST_COMPLETED,
			)

			print(done)

			for task in pending:
				task.cancel()
		except asyncio.CancelledError:
			print('Experiment Complete')
			self.scribe.log('Experiment complete')


