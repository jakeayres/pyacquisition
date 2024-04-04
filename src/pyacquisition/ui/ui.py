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
from .endpoint_popup import EndpointPopup
from .live_data_window import LiveDataWindow
from .live_plot_window import LivePlotWindow

import pandas as pd
import numpy as np




class UI(Broadcaster):


	def __init__(self):
		super().__init__()

		self._runnables = []
		self._setup_dearpygui()


	def _setup_dearpygui(self):
		gui.create_context()		
		gui.create_viewport(title='pyAcquisition', width=1400, height=1000, x_pos=10, y_pos=10)
		gui.setup_dearpygui()


	def add_live_plot(self, sender, app_data, user_data):
		"""
		"""
		window = LivePlotWindow(
			**user_data, 
			width=600, 
			height=600,
			pos=(150, 150),
			)
		window.subscribe_to(self.api_client)
		self._runnables.append(window)



	def make_endpoint_popup(self, sender, app_data, user_data):
		p = EndpointPopup(user_data['path'], user_data['data'])


	async def _render(self):
		while gui.is_dearpygui_running():
			gui.render_dearpygui_frame()
			await asyncio.sleep(0.001)
		else:
			gui.destroy_context()


	async def _run(self):
		while True:
			if len(self._runnables) > 0:
				done, pending = await asyncio.wait(
					[asyncio.create_task(r.run_once()) for r in self._runnables],
				)
			else:
				await asyncio.sleep(1)


	async def setup(self):

		self.api_client = ApiClient()
		self.live_data_window = LiveDataWindow()
		self.live_data_window.subscribe_to(self.api_client)


		data_keys = await self.api_client.get('http://localhost:8000/rack/measurements')
		self.live_plot_window = LivePlotWindow(
			data_keys[0], 
			data_keys,
			width=1050, 
			height=700,
			pos=(320, 30),
			)
		self.live_plot_window.subscribe_to(self.api_client)


		schema = Schema(await self.api_client.get('http://localhost:8000/openapi.json'))
		instruments = await self.api_client.get('http://localhost:8000/rack/instruments')
		
		with gui.viewport_menu_bar():
			with gui.menu(label='Scribe'):
				paths = schema.paths_with_tag('Scribe')
				for key, value in paths.items():
					gui.add_button(
						label=key,
						callback=self.make_endpoint_popup,
						user_data={
							'path': key,
							'data': schema,
							},
						)

			with gui.menu(label='Rack'):
				paths = schema.paths_with_tag('Rack')
				for key, value in paths.items():
					gui.add_button(
						label=key,
						callback=self.make_endpoint_popup,
						user_data={
							'path': key,
							'data': schema,
							},
						)

			with gui.menu(label='Instruments'):
				for instrument in instruments:
					with gui.menu(label=instrument):
						paths = schema.paths_with_tag(instrument)
						for key, value in paths.items():
							gui.add_button(
								label=key,
								callback=self.make_endpoint_popup,
								user_data={
									'path': key,
									'data': schema,
									},
								)

			with gui.menu(label='Tasks'):
				paths = schema.paths_with_tag('Tasks')
				for key, value in paths.items():
					gui.add_button(
						label=key,
						callback=self.make_endpoint_popup,
						user_data={
							'path': key,
							'data': schema,
							},
						)

			with gui.menu(label='Experiment'):
				paths = schema.paths_with_tag('Experiment')
				for key, value in paths.items():
					gui.add_button(
						label=key,
						callback=self.make_endpoint_popup,
						user_data={
							'path': key,
							'data': schema,
							},
						)

			with gui.menu(label='Plots'):
				gui.add_text('x-axis')
				for key in data_keys:
					gui.add_button(
						label=key,
						callback=self.add_live_plot,
						user_data={'x_key': key, 'y_keys': data_keys}
					)


		with gui.window(
			label='Task Queue',
			pos=(10, 190),
			width=300,
			height=150,
			no_move=True,
			no_resize=True,
			no_collapse=True,
			no_close=True,
			no_bring_to_front_on_focus=True,
			):
			self._current_task_uuid = gui.generate_uuid()
			gui.add_text('Current task: '+json.dumps('', indent=4), tag=self._current_task_uuid, color=(40,200,40))
			self._task_queue_uuid = gui.generate_uuid()
			gui.add_text(json.dumps([], indent=4), tag=self._task_queue_uuid)

			# Find a nice pattern for registering the callback and updating etc


	async def run(self):

		await self.setup()
		gui.show_viewport()
		await asyncio.sleep(1)


		done, pending = await asyncio.wait(
			[
				asyncio.create_task(self._render()),
				asyncio.create_task(self._run()),
				asyncio.create_task(self.api_client.broadcast_websocket('ws://localhost:8000/stream')),
				asyncio.create_task(self.live_data_window.run()),
				asyncio.create_task(self.live_plot_window.run()),
				asyncio.create_task(self.api_client.poll_endpoint('http://localhost:8000/experiment/current_task', callback=lambda x: gui.set_value(self._current_task_uuid, json.dumps(x, indent=4)))),
				asyncio.create_task(self.api_client.poll_endpoint('http://localhost:8000/experiment/queued_tasks', callback=lambda x: gui.set_value(self._task_queue_uuid, json.dumps(x, indent=4)))),
			],
			return_when=asyncio.FIRST_EXCEPTION,
		)

		print(done)

		for task in pending:
			task.cancel()

		gui.destroy_context()
