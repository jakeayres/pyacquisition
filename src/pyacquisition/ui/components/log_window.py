import asyncio
import json
import dearpygui.dearpygui as gui
import time
from ...consumer import Consumer



class LogEntry:
	"""A class to represent a single log entry with different colors for each part."""
	
	def __init__(self, date, time, level, message):
		self.date = date
		self.time = time
		self.level = level
		self.message = message
		

	def display(self, parent):

		with gui.group(horizontal=True, parent=parent):
			gui.add_text(self.date, color=(45, 149, 150))

			gui.add_text(self.time, color=(154, 208, 194))

			level_colors = {
				'error': (255, 0, 0),
				'info': (255, 255, 255),
				'debug': (100, 100, 100),
			}

			level_color = level_colors[self.level]
			gui.add_text(self.message, color=level_color)


class LogWindow(Consumer):


	def __init__(self):
		super().__init__()

		self._uuid = gui.generate_uuid()
		self.draw()



	def draw(self):
		with gui.window(
			label="Logs", 
			tag=self._uuid,
			pos=(10, 550),
			width=400,
			height=250,
			no_move=True,
			no_resize=True,
			no_collapse=True,
			no_close=True,
			no_bring_to_front_on_focus=True,
			):
			pass


	async def run(self):
		while True:
			t0 = time.time()
			data = await self.get_from_queue()
			#self.vstack.add_string(data['message'])

			# PYDANTIC-IFY THIS: import from LOGGER class
			entry = LogEntry(date=data['date'], time=data['time'], level=data['level'], message=data['message'])
			entry.display(self._uuid)
