import asyncio
import json
import dearpygui.dearpygui as gui
import time
from ..consumer import Consumer




class LiveDataWindow(Consumer):


	def __init__(self):
		super().__init__()

		self._uuid = gui.generate_uuid()
		self.window = gui.add_window(
			label="Raw Data Stream", 
			tag=self._uuid,
			pos=(10, 30),
			width=400,
			height=250,
			no_move=True,
			no_resize=True,
			no_collapse=True,
			no_close=True,
			no_bring_to_front_on_focus=True,
			)


		self.draw(data={}, t0=time.time())



	def draw(self, data, t0):
		for k, v in data.items():
			with gui.group(horizontal=True, parent=self._uuid):
				gui.add_text(k.ljust(18), color=(154, 208, 194))
				gui.add_text(str(v), color=(255, 255, 255))

		with gui.group(horizontal=True, parent=self._uuid):
			loop_time = time.time() - t0
			gui.add_text('Loop time'.ljust(18), color=(45, 149, 150))
			gui.add_text(f'{loop_time:.3f}'.ljust(8), color=(255, 255, 255))
			gui.add_text(f'seconds', color=(150, 150, 150))


	async def run(self):
		while True:
			t0 = time.time()
			data = await self.get_from_queue()
			gui.delete_item(self._uuid, children_only=True)
			self.draw(data, t0)

			