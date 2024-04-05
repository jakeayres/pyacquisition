import asyncio
import json
import dearpygui.dearpygui as gui
import pandas as pd
from ..consumer import Consumer



WINDOW_KEYS = [
	"label",
	"width",
	"height",
	"min_size",
]

PLOT_KEYS = [
	'label',
	'height',
	'width',
	'no_title',
]

X_AXIS_KEYS = [
	'label',
]

Y_AXIS_KEYS = [
	'label',
]

LEGEND_KEYS = [
	'label',
]


class LivePlotWindow(Consumer):


	_window_uuid_suffix = '_window'
	_plot_uuid_suffix = '_plot'
	_legend_uuid_suffix = '_legend'
	_x_axis_uuid_suffix = '_x_axis'
	_y_axis_uuid_suffix = '_y_axis'



	def __init__(
		self,
		x_key, 
		y_keys,
		pos=[150, 150],
		window_config={'label': 'Live Plot', 'min_size': [300, 300]},
		plot_config={'height': -1, 'width': -1, 'no_title': True},
		legend_config={},
		x_axis_config={},
		y_axis_config={},
		**kwargs
		):
		super().__init__()

		self._uuid = str(gui.generate_uuid())
		self._x_key = x_key
		self._y_keys = y_keys
		self._data = None

		with gui.window(
			tag=self.window_uuid,
			pos=pos,
			**window_config,
			):

			with gui.plot(
				tag=self.plot_uuid,
				**plot_config,
				):
				gui.add_plot_axis(gui.mvXAxis, label=self._x_key, tag=self.x_axis_uuid)
				gui.add_plot_axis(gui.mvYAxis, label=self._y_keys[0], tag=self.y_axis_uuid)
				gui.add_plot_legend(tag=self.legend_uuid)

				for y_key in self._y_keys:
					self.add_scatter_series(self._uuid+'series_tag_'+str(y_key), self._x_key, y_key)

	@classmethod
	def from_config(cls, config):

		return cls(
			config['x_key'],
			config['y_keys'],
			config['pos'],
			window_config=config['window'],
			plot_config=config['plot'],
			legend_config=config['legend'],
			x_axis_config=config['x_axis'],
			y_axis_config=config['y_axis'],
			)


	def config(self):
		data = {
			'x_key': self._x_key,
			'y_keys': self._y_keys,
			'pos': gui.get_item_pos(self.window_uuid),
			'window': {k: gui.get_item_configuration(self.window_uuid).get(k, None) for k in WINDOW_KEYS},
			'plot': {k: gui.get_item_configuration(self.plot_uuid).get(k, None) for k in PLOT_KEYS},
			'x_axis': {k: gui.get_item_configuration(self.x_axis_uuid).get(k, None) for k in X_AXIS_KEYS},
			'y_axis': {k: gui.get_item_configuration(self.y_axis_uuid).get(k, None) for k in Y_AXIS_KEYS},
			'legend': {k: gui.get_item_configuration(self.legend_uuid).get(k, None) for k in LEGEND_KEYS},
		}
		return data


		
	@property
	def window_uuid(self):
		return self._uuid + self._window_uuid_suffix
	

	@property
	def plot_uuid(self):
		return self._uuid + self._plot_uuid_suffix


	@property
	def legend_uuid(self):
		return self._uuid + self._legend_uuid_suffix


	@property
	def x_axis_uuid(self):
		return self._uuid + self._x_axis_uuid_suffix


	@property
	def y_axis_uuid(self):
		return self._uuid + self._y_axis_uuid_suffix
	


	def add_scatter_series(self, line_tag, x_key, y_key):
		gui.add_scatter_series(
			[0], 
			[0], 
			parent=self.y_axis_uuid, 
			tag=line_tag,
			label=y_key,
			)


	def add_line_series(self, line_tag, x_key, y_key):
		gui.add_line_series(
			[0], 
			[0], 
			parent=self.y_axis_uuid, 
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


	async def run_once(self):
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


	async def run(self):
		while True:
			await self.run_once()