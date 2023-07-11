import asyncio
import websockets
import random
import json

from src.websocket_server import WebSocketServer
from src.rack import Rack
from src.scribe import Scribe
from src.experiment import Experiment

from src.coroutines import pause, sweep_gizmotron


from fastapi import FastAPI, WebSocket
from hypercorn.asyncio import serve
from hypercorn.config import Config
import uvicorn


class MyExperiment(Experiment):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, *kwargs)

		self.app = FastAPI()

		@self.app.websocket("/ws")
		async def websocket_endpoint(websocket: WebSocket):
			print('CONNECGING?')
			await websocket.accept()
			print('Connected')
			while True:
				await websocket.send_json(json.dumps({'message': 'This is a message'}))
				await asyncio.sleep(1)

		@self.app.get("/message")
		def message():
			return {'message': 'This is a message'}


		@self.app.get("/data")
		def message2():
			return {'message': 'This is a message'}


	async def execute(self):
		await pause(self.scribe, 3)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 3)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 4)


	async def run(self):

		rack_task = asyncio.create_task(self.rack.run())
		scribe_task = asyncio.create_task(self.scribe.run())
		#ws_task = asyncio.create_task(self.ws_server.run())
		main_task = asyncio.create_task(self.execute())

		# config = Config()
		# config.bind = ["localhost:8000"]
		# app_task = asyncio.create_task(serve(self.app, config))
		# 
		
		config = uvicorn.Config(self.app, host="localhost", port=8000)
		server = uvicorn.Server(config)
		app_task = asyncio.create_task(server.serve())

		
		done, pending = await asyncio.wait(
			[
			scribe_task,
			rack_task,
			#ws_task,
			main_task,
			app_task,
			],
			return_when=asyncio.FIRST_COMPLETED,
		)

		for task in pending:
			task.cancel()

		self.scribe.log('Experiment complete')




async def main():
	exp = MyExperiment("./data/", "soft_config.json")
	await asyncio.create_task(exp.run())



asyncio.run(main())
