import asyncio
import json
import dearpygui.dearpygui as gui
import time
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
			pos=(10, 30),
			width=300,
			height=150,
			no_move=True,
			no_resize=True,
			no_collapse=True,
			no_close=True,
			no_bring_to_front_on_focus=True,
			):
			gui.add_text(json.dumps({}), tag='data_string')
			gui.add_text('Loop time:', tag='loop_time')


	async def run(self):
		while True:
			t0 = time.time()
			data = await self._queue.get()
			gui.set_value('data_string', json.dumps(data, indent=4))
			t1 = time.time() - t0
			gui.set_value('loop_time', f'Loop time:  {t1:.3f} s')