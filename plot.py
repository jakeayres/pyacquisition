import asyncio
import websockets
import json
import matplotlib.pyplot as plt
import numpy as np


class RealTimePlot:


	def __init__(self):

		plt.ion()
		self.fig, self.ax = plt.subplots()
		self.lines = {}


	def _create_line(self, key, **kwargs):
		self.lines[key] = self.ax.plot([], [], **kwargs)[-1]
		return self.lines[key]


	def _update_line(self, key, x, y):
		line = self.lines[key]
		x_data, y_data = line.get_data()[0], line.get_data()[1]
		x_data = np.append(x_data, x)
		y_data = np.append(y_data, y)
		line.set_data(x_data, y_data)


	def _redraw(self):
		self.ax.relim()
		self.ax.autoscale_view()
		plt.draw()
		plt.pause(0.1)


	async def websocket_handler(self, uri):

		line = self._create_line('async')

		async with websockets.connect(uri) as websocket:
			while True:
				data = await websocket.recv()
				print(type(data))
				data = json.loads(data)
				print(type(data))
				print(json.dumps(data, indent=2))
				x, y = data['time'], data['value']

				self._update_line('async', x, y)
				self._redraw()


	async def run(self, websocket_uri):
		# Create the event loop and start the WebSocket connection
		#loop = asyncio.get_event_loop()
		task = asyncio.create_task(self.websocket_handler(websocket_uri))

		await task


		# Start the application event loop
		plt.show()


# Define the WebSocket server URI
websocket_uri = "ws://localhost:8000/stream"  # Replace with the actual URI of your WebSocket server

# Create and run the real-time plot
real_time_plot = RealTimePlot()

asyncio.run(real_time_plot.run(websocket_uri))