import asyncio
import websockets
import json

from .consumer import Consumer



class WebSocketServer(Consumer):


	def __init__(self, host, port):
		super().__init__()
		self.host = host
		self.port = port
		self.clients = set()



	async def handle_connection(self, websocket, path):
		""" 
		Called when a connection is made to the server		

		:param      websocket:  The websocket
		:type       websocket:  { type_description }
		:param      path:       The path
		:type       path:       { type_description }
		"""
		self.clients.add(websocket)

		try:
			while True:
				message = await websocket.recv()
				# Do something with the message
				# Perhaps send a response:
				# #await self.send_message_to_clients(message)
		except Exception as e:
			print(e)
		finally:
			self.clients.remove(websocket)


	async def send(self, message):
		"""
		Broadcast message to connected clients

		:param      message:  The message
		:type       message:  { type_description }
		"""

		if self.clients:
			await asyncio.gather(*[client.send(message) for client in self.clients])


	async def start_server(self):
		"""
		Starts a websocket server.
		"""
		server = await websockets.serve(self.handle_connection, self.host, self.port)
		await server.wait_closed()


	async def relay_messages_from_queue(self):
		"""
		Take messages from the Consumer queue and send them to websocket
		"""
		while True:
			# Generate real-time data here
			x = json.dumps(await self._queue.get())
			await self.send(x)



	async def run(self):
		"""
		asyncio coroutine
		"""
		server_task = asyncio.create_task(self.start_server())
		data_task = asyncio.create_task(self.relay_messages_from_queue())

		await asyncio.gather(server_task, data_task)