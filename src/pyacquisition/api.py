from .consumer import Consumer

from fastapi import FastAPI, WebSocket
import uvicorn
import logging
import asyncio
import json
from fastapi.middleware.cors import CORSMiddleware


class API(Consumer):


	def __init__(self, allowed_cors_origins: list = None):
		super().__init__()

		self.app = FastAPI(
			title='PyAcquisition FastAPI',
			description='Connect your GUI to this.'
		)

		if allowed_cors_origins != None:

			self.app.add_middleware(
				CORSMiddleware,
				allow_origins=allowed_cors_origins,
				allow_credentials=True,
				allow_methods=["*"],
				allow_headers=["*"],
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


