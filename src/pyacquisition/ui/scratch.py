import asyncio
import dearpygui.dearpygui as dpg
import websockets
import aiohttp
import json

from src.broadcaster import Broadcaster
from src.consumer import Consumer


async def render_loop():

	while True:
		dpg.render_dearpygui_frame()
		await asyncio.sleep(0.001)


async def blink():

	while True:
		await asyncio.sleep(1)
		print('i')



class WS_Loop(Broadcaster):


	def __init__(self):
		super().__init__()


	async def run(self):
		async with aiohttp.ClientSession() as session:
			async with session.ws_connect('ws://localhost:8000/stream') as ws:
				while True:
					message = await ws.receive()
					self.emit(message.data)


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


async def main():


	dpg.create_context()

	ws_loop = WS_Loop()
	live_data_window = LiveDataWindow()
	live_data_window.subscribe_to(ws_loop)

	with dpg.window(label="Example Window"):
		dpg.add_text("Hello, world")
		dpg.add_button(label="Save")
		dpg.add_input_text(label="string", default_value="Quick brown fox")
		dpg.add_slider_float(label="float", default_value=0.273, max_value=1)
		dpg.add_text('DTA', tag='live_data')

	dpg.create_viewport(title='Custom Title', width=800, height=600)
	dpg.setup_dearpygui()
	dpg.show_viewport()

	# below replaces, start_dearpygui()
	while dpg.is_dearpygui_running():
		
		await asyncio.gather(
			render_loop(),
			blink(),
			ws_loop.run(),
			live_data_window.run()
			)

	dpg.destroy_context()



if __name__ == "__main__":
	asyncio.run(main())
