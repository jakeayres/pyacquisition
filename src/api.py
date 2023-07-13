from .consumer import Consumer

from fastapi import FastAPI, WebSocket
import uvicorn
import logging
import asyncio
import json


class API(Consumer):


	def __init__(self):
		super().__init__()

		self.app = FastAPI(
			title='PyAcquisition FastAPI',
			description='Connect your GUI to this.'
		)

		@self.app.websocket('/stream')
		async def stream_endpoint(websocket: WebSocket):
			await websocket.accept()
			while True:
				x = await self._queue.get()
				await websocket.send_json(x)


	def coroutine(self):
		uvicorn_logger = logging.getLogger("uvicorn")
		uvicorn_logger.setLevel(logging.WARNING)
		config = uvicorn.Config(self.app, host="localhost", port=8000, log_level=logging.WARNING)
		server = uvicorn.Server(config)
		return asyncio.create_task(server.serve())


