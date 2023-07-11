import asyncio
import websockets
import random

from src.websocket_server import WebSocketServer
from src.rack import Rack
from src.scribe import Scribe
from src.experiment import Experiment

from src.coroutines import pause, sweep_gizmotron





class MyExperiment(Experiment):
	
	async def execute(self):
		await pause(self.scribe, 3)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 3)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 4)


async def main():
	exp = MyExperiment("./data/", "soft_config.json")
	await asyncio.create_task(exp.run())


asyncio.run(main())
