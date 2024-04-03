import asyncio
import dearpygui.dearpygui as gui
import aiohttp
import requests
import json
from functools import partial

from ..broadcaster import Broadcaster
from ..consumer import Consumer

from .openapi import Schema
from .api_client import ApiClient
from .live_data_window import LiveDataWindow
from .live_plot_window import LivePlotWindow

import pandas as pd
import numpy as np



class Endpoint(object):


	def __init__(self, session, schema, endpoint, display=True):

		self._path = endpoint
		self._params = self._make_parameter_dictionary(schema, endpoint)
		self._callbacks = []

		if display:
			gui.add_text(schema['paths'][endpoint]['get']['summary'], tag=f'{endpoint}_tooltip_parent')

			with gui.tooltip(f"{endpoint}_tooltip_parent"):
				gui.add_text(schema['paths'][endpoint]['get']['description'])

			if 'parameters' in schema['paths'][endpoint]['get']:
				for param in schema['paths'][endpoint]['get']['parameters']:
					if param['schema']['type'] == 'string':
						self._add_text_input(param)
					elif param['schema']['type'] == 'boolean':
						self._add_boolean_input(param)
					else:
						self._add_text_input(param)

			gui.add_button(label='SEND', callback=self.request)


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
		gui.add_input_text(
			tag=_id,
			label=param['name'],
			callback=self._set_parameter, 
			user_data={'key': param['name'], 'uuid': _id},
			)


	def _add_boolean_input(self, param):
		_id = self._make_parameter_uuid(param)
		gui.add_checkbox(
			tag=_id,
			label=param['name'],
			callback=self._set_parameter,
			user_data={'key': param['name'], 'uuid': _id},
			)


	def _set_parameter(self, sender, app_data, user_data):
		self._params[user_data['key']] = gui.get_value(user_data['uuid'])


	def register_callback(self, f, **kwargs):
		self._callbacks.append(partial(f, **kwargs))


	def request(self):
		endpoint = 'http://localhost:8000'+self._make_endpoint()
		value = requests.get(endpoint, timeout=1)
		value = value.content.decode('utf-8')
		return value


	async def set_fetched_value(self, item):
		value = await self.get()
		gui.set_value(item=item, value=value)


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



class UI(Broadcaster):


	def __init__(self):
		super().__init__()

		self._setup_dearpygui()


	def _setup_dearpygui(self):
		gui.create_context()		
		gui.create_viewport(title='pyAcquisition', width=1400, height=1000, x_pos=10, y_pos=10)
		gui.setup_dearpygui()


	def register_window(self, window, subscribe:bool=False):
		"""
 		"""
		if subscribe:
			window.subscribe_to(self)
		self._tasks.append(asyncio.create_task(window.run()))
		return window


	def make_popup(self, sender, app_data, user_data):

		with gui.window(label=user_data['path']):
			gui.add_text(user_data['path'])


	async def _render(self):

		while gui.is_dearpygui_running():
			gui.render_dearpygui_frame()
			await asyncio.sleep(0.001)
		else:
			gui.destroy_context()


	async def setup(self):

		self.api_client = ApiClient()
		self.live_data_window = LiveDataWindow()
		self.live_data_window.subscribe_to(self.api_client)


		data_keys = await self.api_client.get('http://localhost:8000/rack/measurements')
		self.live_plot_window = LivePlotWindow(data_keys[0], data_keys)
		self.live_plot_window.subscribe_to(self.api_client)


		schema = Schema(await self.api_client.get('http://localhost:8000/openapi.json'))
		instruments = await self.api_client.get('http://localhost:8000/rack/instruments')
		
		with gui.viewport_menu_bar():
			with gui.menu(label='Instruments'):

				for instrument in instruments:

					with gui.menu(label=instrument):

						paths = schema.paths_with_tag(instrument)
						
						for key, value in paths.items():
							gui.add_button(
								label=path,
								callback=self.make_popup,
								user_data={
									'path': key,
									'data': value,
									},
								)



	async def run(self):

		await self.setup()

		gui.show_viewport()

		# self._schema = await self._get_openapi_schema()

		# window = gui.window(label='Data files', width=350, height=300, no_close=True, no_move=False)

		# with window:
		# 	gui.add_text('---', tag='current_filename', show_label=True, label='Current Filename')
		# 	gui.add_separator()
		# 	e = Endpoint(self._session, self._schema, '/scribe/next_file/{label}/{next_chapter}')
		# 	gui.add_separator()
			
		# 	e = Endpoint(self._session, self._schema, '/scribe/current_filename', display=False)
		# 	e.register_callback(e.set_fetched_value, item='current_filename')
		# 	self._tasks.append(e.run())
			
		# 	e = Endpoint(self._session, self._schema, '/Wave1/frequency/set/{frequency}')
		await asyncio.sleep(1)

		render_task = asyncio.create_task(self._render())

		done, pending = await asyncio.wait(
			[
				render_task,
				asyncio.create_task(self.api_client.broadcast_websocket('ws://localhost:8000/stream')),
				asyncio.create_task(self.live_data_window.run()),
				asyncio.create_task(self.live_plot_window.run()),
				asyncio.create_task(self.api_client.poll_endpoint('http://localhost:8000/scribe/current_filename'))

				# *self._tasks,
			],
			return_when=asyncio.FIRST_EXCEPTION,
		)

		print(done)

		for task in pending:
			task.cancel()

		gui.destroy_context()
