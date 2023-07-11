import matplotlib.pyplot as plt
import numpy as np

from .consumer import Consumer



class Graph(Consumer):

	
	def __init__(self):
		super().__init__()

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
		plt.pause(0.003)


	def plot(self, key, x, y, **kwargs):
		if key not in self.lines:
			self._create_line(key, **kwargs)
		self._update_line(key, x, y)
		self._redraw()


	def save(self, filename):
		self.fig.savefig(filename)


	def clear(self):
		self.ax.cla()
		for key in self.lines.keys():
			self._create_line(key)


	async def run(self, x, y):

		line = self._create_line('async')
		while True:
			data = await self._queue.get()
			self._update_line('async', data[x], data[y])
			self._redraw()