from .consumer import Consumer

from fastapi import FastAPI, WebSocket
import uvicorn
import logging
import asyncio
import enum
from typing import Callable
from fastapi.middleware.cors import CORSMiddleware


class API(Consumer):
	"""
	API class that extends the Consumer class to provide WebSocket endpoints and FastAPI functionality.

	Args:
		allowed_cors_origins (List[str], optional): List of CORS origins to allow. Defaults to None.

	Usage:
		api = API(allowed_cors_origins=['*'])
		api.add_websocket_endpoints('/stream_one', get_data_one)
		api.add_websocket_endpoints('/stream_two', get_data_two)
		api.coroutine()
	"""

	def __init__(self, allowed_cors_origins: list = None):
		"""
		Initializes the API object.

		Args:
			allowed_cors_origins (List[str], optional): List of CORS origins to allow. Defaults to None.
		"""

		super().__init__()

		self.app = FastAPI(
			title='PyAcquisition FastAPI',
			description='Connect your GUI to this.'
		)

		if allowed_cors_origins is not None:
			self.app.add_middleware(
				CORSMiddleware,
				allow_origins=allowed_cors_origins,
				allow_credentials=True,
				allow_methods=["*"],
				allow_headers=["*"],
			)

		self.add_websocket_endpoint('/stream', self._queue.get)



	def add_websocket_endpoint(self, url: str, poll_function: Callable):
		"""
		Adds a new WebSocket endpoint with a specified URL and corresponding poll function.

		Args:
			url (str): The WebSocket endpoint URL.
			poll_function (Callable): The async function to poll for data (expecting dict returns).

		Usage:
			api.add_websocket_endpoints('/stream_custom', custom_poll_function)
		"""

		@self.app.websocket(url)
		async def websocket_endpoint(websocket: WebSocket):
			"""
			WebSocket endpoint that polls the provided async function and sends data to connected clients.

			Args:
				websocket (WebSocket): WebSocket connection object.
			"""
			def enum_to_selected_dict(enum_instance):
				return {
					item.name: {
						"value": item.value,
						"selected": item == enum_instance,
					} for item in enum_instance.__class__
				}

			await websocket.accept()
			while True:
				data = await poll_function()
				for key, value in data.items():
					if isinstance(value, enum.Enum):
						data[key] = enum_to_selected_dict(value)
				await websocket.send_json(data)


	def add_endpoint(self, url: str, func: Callable):

		@self.app.get(url)
		def endpoint():
			return func()



	def coroutine(self):
		"""
		Starts the FastAPI server in an asyncio task.

		Usage:
			api.coroutine()
		"""

		uvicorn_logger = logging.getLogger("uvicorn")
		uvicorn_logger.setLevel(logging.WARNING)
		config = uvicorn.Config(self.app, host="localhost", port=8000, log_level=logging.WARNING)
		server = uvicorn.Server(config)
		return asyncio.create_task(server.serve())
