import asyncio
import dearpygui.dearpygui as dpg
import json
import aiohttp
from ..broadcaster import Broadcaster




class ApiClient(Broadcaster):
	"""
	Connect to the FastAPI and deal with websocket
	and http communication.
	"""


	def __init__(self):
		super().__init__()


	async def get(self, endpoint):
		"""
		Get response from endpoint

		:param      endpoint:  The endpoint
		:type       endpoint:  { type_description }
		"""

		async with aiohttp.ClientSession() as session:
			async with session.get(endpoint) as resp:
				response = await resp.text()
				return json.loads(response)


	async def poll_endpoint(self, endpoint, callback=None, period=1):
		"""
		Poll a http GET endpoint and pass the response into a callback
		if one is provided
		
		:param      endpoint:  The endpoint
		:type       endpoint:  { type_description }
		:param      callback:  The callback
		:type       callback:  Function
		:param      period:    The period
		:type       period:    int
		"""
		async with aiohttp.ClientSession() as session:
			async with session.get(endpoint) as resp:
				while True:
					await asyncio.sleep(period)
					response = await resp.text()
					if callback is not None:
						callback(json.loads(response))


	async def broadcast_websocket(self, endpoint):
		"""
		Broadcasts the response from a websocket.
		
		:param      endpoint:  The endpoint
		:type       endpoint:  { type_description }
		"""
		async with aiohttp.ClientSession() as session:
			async with session.ws_connect(endpoint) as ws:
				while True:
					message = await ws.receive()
					self.emit(json.loads(message.data))
	