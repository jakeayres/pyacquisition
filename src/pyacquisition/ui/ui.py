import asyncio
import dearpygui.dearpygui as dpg
import aiohttp
import requests
import json
from functools import partial

from ..broadcaster import Broadcaster
from ..consumer import Consumer

import pandas as pd
import numpy as np



class Endpoint(object):


	def __init__(self, session, schema, endpoint, display=True):

		self._path = endpoint
		self._params = self._make_parameter_dictionary(schema, endpoint)
		self._callbacks = []
		self._session = session

		if display:
			dpg.add_text(schema['paths'][endpoint]['get']['summary'], tag=f'{endpoint}_tooltip_parent')

			with dpg.tooltip(f"{endpoint}_tooltip_parent"):
				dpg.add_text(schema['paths'][endpoint]['get']['description'])

			if 'parameters' in schema['paths'][endpoint]['get']:
				for param in schema['paths'][endpoint]['get']['parameters']:
					if param['schema']['type'] == 'string':
						self._add_text_input(param)
					elif param['schema']['type'] == 'boolean':
						self._add_boolean_input(param)
					else:
						self._add_text_input(param)

			dpg.add_button(label='SEND', callback=self.request)


	def _make_parameter_dictionary(self, schema, endpoint):
		if 'parameters' in schema['paths'][endpoint]['get']:
			return {param['name']:'' for param in schema['paths'][endpoint]['get']['parameters']}
		else:
			return {}


	def _make_parameter_uuid(self, param):
		return '_'.join([self._path, param['name'], '_uuid'])


	def _make_endpoint(self):
		endpoint = self._path
		for k, v in self._params.items():
			endpoint = endpoint.replace('{'+k+'}', str(v))
		return endpoint


	def _add_text_input(self, param):
		_id = self._make_parameter_uuid(param)
		dpg.add_input_text(
			tag=_id,
			label=param['name'],
			callback=self._set_parameter, 
			user_data={'key': param['name'], 'uuid': _id},
			)


	def _add_boolean_input(self, param):
		_id = self._make_parameter_uuid(param)
		dpg.add_checkbox(
			tag=_id,
			label=param['name'],
			callback=self._set_parameter,
			user_data={'key': param['name'], 'uuid': _id},
			)


	def _set_parameter(self, sender, app_data, user_data):
		self._params[user_data['key']] = dpg.get_value(user_data['uuid'])


	def register_callback(self, f, **kwargs):
		self._callbacks.append(partial(f, **kwargs))


	def request(self):
		endpoint = 'http://localhost:8000'+self._make_endpoint()
		value = requests.get(endpoint, timeout=1)
		value = value.content.decode('utf-8')
		return value


	async def set_fetched_value(self, item):
		value = await self.get()
		dpg.set_value(item=item, value=value)


	async def get(self):
		async with aiohttp.ClientSession('http://localhost:8000') as session:
			async with session.get(self._make_endpoint()) as resp:
				x = json.loads(await resp.text())
				return x


	async def run(self, period=1):

		while True:
			await asyncio.sleep(period)
			for callback in self._callbacks:
				try:
					await callback()
				except Exception as e:
					print(e)




class LivePlotWindow(Consumer):

	def __init__(self, x_key, y_keys):
		super().__init__()

		self._uuid = str(dpg.generate_uuid())
		self._x_key = x_key
		self._y_keys = y_keys
		self._data = None

		with dpg.window(label='Live Plot', tag=self._uuid+'_window'):

			with dpg.plot(label='Data', height=600, width=600):
				dpg.add_plot_axis(dpg.mvXAxis, label=self._x_key)
				dpg.add_plot_axis(dpg.mvYAxis, label=self._y_keys[0], tag=self._uuid+'y_axis')
				dpg.add_plot_legend()

				for y_key in self._y_keys:
					self.start_line(self._uuid+'series_tag_'+str(y_key), self._x_key, y_key)


			dpg.add_radio_button(tag=self._uuid+'_x_radio', items=self._y_keys, callback=self._update_x_key, user_data=self._uuid+'_x_radio')


	def start_line(self, line_tag, x_key, y_key):
		dpg.add_scatter_series(
			[0], 
			[0], 
			parent=self._uuid+'y_axis', 
			tag=line_tag,
			label=y_key,
			)


	def update_line(self, line_tag, x_key, y_key):
		dpg.set_value(
			line_tag, 
			[self._data[self._x_key].tolist(), self._data[y_key].tolist()],
			)


	def _set_x_key(self, x_key):
		self._x_key = x_key


	def _update_x_key(self, sender, app_data, user_data):
		new_key = dpg.get_value(user_data)
		self._set_x_key(new_key)


	async def run(self):

		while True:

			try:
				data = await self._queue.get()
				data = json.loads(data)

				if self._data is None:
					self._data = pd.DataFrame(data=data, index=[0])

				else:
					self._data = pd.concat([self._data, pd.DataFrame(data=data, index=[0])])

					for y_key in self._y_keys:
						self.update_line(self._uuid+'series_tag_'+str(y_key), self._x_key, y_key)

			except Exception as e:
				print(e)


class LiveDataWindow(Consumer):

	def __init__(self):
		super().__init__()

		with dpg.window(label="Raw Data Stream", tag='data_window'):
			dpg.add_text("Hello, world", tag='data_string')


	async def run(self):

		while True:
			data = await self._queue.get()
			data = json.loads(data)
			dpg.set_value('data_string', json.dumps(data, indent=4))


class UI(Broadcaster):


	def __init__(self):
		super().__init__()

		self._schema = None
		self._tasks = []
		self._session = aiohttp.ClientSession('http://localhost:8000')

		dpg.create_context()		
		dpg.create_viewport(title='pyAcquisition', width=1200, height=800)

		self.register_window(LiveDataWindow(), subscribe=True)
		self.register_window(LivePlotWindow('time', ['time', 'field', 'signal_1']), subscribe=True)



		dpg.setup_dearpygui()
		dpg.show_viewport()



	def register_window(self, window, subscribe:bool=False):
		"""
 		"""
		if subscribe:
			window.subscribe_to(self)
		self._tasks.append(asyncio.create_task(window.run()))
		return window



	async def get(self, path):

		async with aiohttp.ClientSession('http://localhost:8000') as session:
			async with session.get(path) as resp:
				x = json.loads(await resp.text())
				return x


	async def _get_openapi_schema(self):

		async with aiohttp.ClientSession() as session:
			async with session.get('http://localhost:8000/openapi.json') as resp:
				schema = json.loads(await resp.text())
				return schema


	async def _parse_schema(self):

		schema = await self._get_openapi_schema()
		await self._parse_scribe_schema()


	def current_filename(self):
		x = asyncio.run(self.get('/scribe/current_filename'))
		print(x)


	async def _parse_scribe_schema(self):

		with dpg.viewport_menu_bar():

			with dpg.menu(label='File'):

				dpg.add_menu_item(label='Next File', callback=self.current_filename)



	async def _render(self):

		while dpg.is_dearpygui_running():
			dpg.render_dearpygui_frame()
			await asyncio.sleep(0.001)
		else:
			dpg.destroy_context()


	async def _emit(self):
		async with aiohttp.ClientSession() as session:
			async with session.ws_connect('ws://localhost:8000/stream') as ws:
				while True:
					message = await ws.receive()
					self.emit(message.data)


	async def run(self):

		self._schema = await self._get_openapi_schema()

		window = dpg.window(label='Data files', width=350, height=300, no_close=True, no_move=False)

		with window:
			dpg.add_text('---', tag='current_filename', show_label=True, label='Current Filename')
			dpg.add_separator()
			e = Endpoint(self._session, self._schema, '/scribe/next_file/{label}/{next_chapter}')
			dpg.add_separator()
			
			e = Endpoint(self._session, self._schema, '/scribe/current_filename', display=False)
			e.register_callback(e.set_fetched_value, item='current_filename')
			self._tasks.append(e.run())
			
			e = Endpoint(self._session, self._schema, '/Wave1/frequency/set/{frequency}')


		done, pending = await asyncio.wait(
			[
				asyncio.create_task(self._render()),
				asyncio.create_task(self._emit()),
				*self._tasks,
			],
			return_when=asyncio.FIRST_EXCEPTION,
		)

		for task in pending:
			task.cancel()

		dpg.destroy_context()
