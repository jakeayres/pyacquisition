import asyncio
import json
import dearpygui.dearpygui as gui
from ..consumer import Consumer


class LiveDataWindow(Consumer):


	def __init__(self):
		super().__init__()

		self._uuid = gui.generate_uuid()
		self.draw()


	def draw(self):
		with gui.window(
			label="Raw Data Stream", 
			tag='data_window',
			pos=(0, 800),
			width=350,
			height=150,
			no_move=True,
			no_resize=True,
			no_collapse=True,
			no_close=True,
			):
			gui.add_text(json.dumps({}), tag='data_string')


	async def run(self):
		while True:
			data = await self._queue.get()
			gui.set_value('data_string', json.dumps(data, indent=4))