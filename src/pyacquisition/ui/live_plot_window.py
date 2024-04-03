import asyncio
import json
import dearpygui.dearpygui as gui
import pandas as pd
from ..consumer import Consumer




class LivePlotWindow(Consumer):

	def __init__(self, x_key, y_keys):
		super().__init__()

		self._uuid = str(gui.generate_uuid())
		self._x_key = x_key
		self._y_keys = y_keys
		self._data = None

		with gui.window(label='Live Plot', tag=self._uuid+'_window'):

			with gui.plot(label='Data', height=600, width=600):
				gui.add_plot_axis(gui.mvXAxis, label=self._x_key)
				gui.add_plot_axis(gui.mvYAxis, label=self._y_keys[0], tag=self._uuid+'y_axis')
				gui.add_plot_legend()

				for y_key in self._y_keys:
					self.start_line(self._uuid+'series_tag_'+str(y_key), self._x_key, y_key)


			gui.add_radio_button(tag=self._uuid+'_x_radio', items=self._y_keys, callback=self._update_x_key, user_data=self._uuid+'_x_radio')


	def start_line(self, line_tag, x_key, y_key):
		gui.add_scatter_series(
			[0], 
			[0], 
			parent=self._uuid+'y_axis', 
			tag=line_tag,
			label=y_key,
			)


	def update_line(self, line_tag, x_key, y_key):
		gui.set_value(
			line_tag, 
			[self._data[self._x_key].tolist(), self._data[y_key].tolist()],
			)


	def _set_x_key(self, x_key):
		self._x_key = x_key


	def _update_x_key(self, sender, app_data, user_data):
		new_key = gui.get_value(user_data)
		self._set_x_key(new_key)


	async def run(self):

		while True:

			try:
				data = await self._queue.get()

				if self._data is None:
					self._data = pd.DataFrame(data=data, index=[0])

				else:
					self._data = pd.concat([self._data, pd.DataFrame(data=data, index=[0])])

					for y_key in self._y_keys:
						self.update_line(self._uuid+'series_tag_'+str(y_key), self._x_key, y_key)

			except Exception as e:
				print(e)
