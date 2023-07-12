import asyncio
import websockets
import random
import json

from src.experiment import Experiment

from src.instruments import Clock, WaveformGenerator, Gizmotron

from src.coroutines import pause, sweep_gizmotron

from fastapi import FastAPI, WebSocket
import uvicorn


class MyExperiment(Experiment):


	def setup(self):
		clock = self.add_software_instrument('clock', Clock)
		self.add_measurement('time', clock.time)

		gizmo = self.add_software_instrument('gizmo', Gizmotron)
		self.add_measurement('value', gizmo.get_value)

		wave1 = self.add_software_instrument('wave1', WaveformGenerator)
		self.add_measurement('signal_1', wave1.get_signal)

		wave2 = self.add_software_instrument('wave2', WaveformGenerator)
		self.add_measurement('signal_2', wave2.get_signal)


	def register_endpoints(self):
		super().register_endpoints()
		
		@self.api.get("/current_file")
		def message():
			return {'message': f'{self.scribe.filename}'}


	async def execute(self):
		await pause(self.scribe, 3)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 30)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 40)


async def main():
	exp = MyExperiment("./data/")
	await asyncio.create_task(exp.run())


asyncio.run(main())
