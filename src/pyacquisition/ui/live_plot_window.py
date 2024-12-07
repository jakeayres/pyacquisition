import asyncio
import json
import dearpygui.dearpygui as gui
import pandas as pd
from functools import partial
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
	'no_gridlines',
	'no_tick_marks',
	'no_tick_labels',
	'log_scale',
	'invert',
	'lock_min',
	'lock_max',
]

Y_AXIS_KEYS = [
	'no_gridlines',
	'no_tick_marks',
	'no_tick_labels',
	'log_scale',
	'invert',
	'lock_min',
	'lock_max',
]

LEGEND_KEYS = [
	'label',
	'location',
	'horizontal',
	'outside',
]


class LivePlotWindow(Consumer):


	_window_uuid_suffix = '_window'
	_plot_uuid_suffix = '_plot'
	_legend_uuid_suffix = '_legend'
	_x_axis_uuid_suffix = '_x_axis'
	_y_axis_uuid_suffix = '_y_axis'
	_series_uuid_suffix = '_series'



	def __init__(
		self,
		all_keys,
		x_key, 
		y_keys,
		pos=[150, 150],
		window_config={'label': 'Live Plot', 'min_size': [300, 300]},
		plot_config={'height': -1, 'width': -1, 'no_title': True},
		legend_config={},
		x_axis_config={},
		y_axis_config={},
		on_close_callback=lambda *args: None,
		**kwargs
		):
		super().__init__()

		self._uuid = str(gui.generate_uuid())
		self._all_keys = all_keys
		self._x_key = x_key
		self._y_keys = y_keys
		self._data = None
		self._on_close_callback = on_close_callback

		with gui.window(
			tag=self.window_uuid,
			pos=pos,
			on_close=self.close,
			**window_config,
			):


			with gui.menu_bar():

				with gui.menu(label='Clear'):
					gui.add_button(
						label='All',
						callback=self.clear_data,
					)

				with gui.menu(label='x-axis'):
					for key in self._all_keys:
						gui.add_button(
							label=f'{key}',
							callback=self._update_x_key_callback,
							user_data=key
						)

				with gui.menu(label='y-axis'):
					with gui.menu(label='Add'):
						for key in self._all_keys:
							gui.add_button(
								label=f'{key}',
								callback=self._add_y_key_callback,
								user_data=key,
							)

					with gui.menu(label='Remove'):
						for key in self._all_keys:
							gui.add_button(
								label=f'{key}',
								callback=self._remove_y_key_callback,
								user_data=key,
							)


			with gui.plot(
				tag=self.plot_uuid,
				**plot_config,
				):
				gui.add_plot_axis(gui.mvXAxis, label=self._x_key, tag=self.x_axis_uuid, **x_axis_config)
				gui.add_plot_axis(gui.mvYAxis, label='', tag=self.y_axis_uuid, **y_axis_config)
				gui.add_plot_legend(tag=self.legend_uuid, **legend_config)

				for y_key in self._y_keys:
					self.add_scatter_series(self.series_uuid(y_key), self._x_key, y_key)


	def close(self, data):
		self.clear_data()
		gui.delete_item(self.window_uuid, children_only=True)
		gui.delete_item(self.window_uuid)
		self._on_close_callback()




	@classmethod
	def from_config(cls, config):

		return cls(
			config['all_keys'],
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
			'all_keys': self._all_keys,
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


	def series_uuid(self, key):
		return self._uuid + key + self._series_uuid_suffix
	

	def clear_data(self):
		self._data = None


	def add_scatter_series(self, series_uuid, x_key, y_key):
		gui.add_scatter_series(
			[0], 
			[0], 
			parent=self.y_axis_uuid, 
			tag=series_uuid,
			label=y_key,
			)


	def add_line_series(self, series_uuid, x_key, y_key):
		gui.add_line_series(
			[0], 
			[0], 
			parent=self.y_axis_uuid, 
			tag=series_uuid,
			label=y_key,
			)


	def delete_series(self, series_uuid):
		gui.delete_item(series_uuid)


	def update_line(self, series_uuid, x_key, y_key):
		gui.set_value(
			series_uuid, 
			#[self._data[self._x_key].tolist(), self._data[y_key].tolist()],
			[self._data[self._x_key], self._data[y_key]],
			)


	def _set_x_key(self, x_key):
		self._x_key = x_key


	def _update_x_key_callback(self, sender, app_data, user_data):
		gui.configure_item(self.x_axis_uuid, label=user_data)
		self._set_x_key(user_data)


	def _add_y_key_callback(self, sender, app_data, user_data):
		key = user_data
		if key not in self._y_keys:
			self._y_keys.append(key)
			self.add_scatter_series(self.series_uuid(key), self._x_key, key)


	def _remove_y_key_callback(self, sender, app_data, user_data):
		key = user_data
		if key in self._y_keys:
			self._y_keys.remove(key)
			self.delete_series(self.series_uuid(key))


	async def run_once(self):
		try:
			print('PLOT LOOP')
			data = await self._queue.get()
			if self._data is None:
				#self._data = pd.DataFrame(data=data, index=[0])
				self._data = {k: [v] for k, v in data.items()}
			else:
				#self._data = pd.concat([self._data, pd.DataFrame(data=data, index=[0])])
				for k, v in data.items():
					self._data[k].append(v)
				for y_key in self._y_keys:
					self.update_line(self.series_uuid(y_key), self._x_key, y_key)
		except Exception as e:
			print('EXCEPTION IN PLOT LOOP')
			print(e)


	async def run(self):
		while True:
			await self.run_once()