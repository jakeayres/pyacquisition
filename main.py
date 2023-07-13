import asyncio
import websockets
import random
import json

from src.experiment import Experiment

from src.instruments import Clock, WaveformGenerator, Gizmotron, SR_830

from src.coroutines import pause, sweep_gizmotron, sweep_lockin_frequency

from src.visa import resource_manager

from fastapi import FastAPI, WebSocket
import uvicorn


class SoftExperiment(Experiment):


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
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 3000)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 4000)



class MyExperiment(Experiment):

	def setup(self):
		clock = self.add_software_instrument('clock', Clock)
		self.add_measurement('time', clock.time)

		lockin = self.add_hardware_instrument(
			'lockin', 
			SR_830, 
			resource_manager(backend='prologix', com_port=3).open_resource('GPIB0::12::INSTR')
		)
		self.add_measurement('freq', lockin.get_frequency)
		self.add_measurement('x', lockin.get_x)
		self.add_measurement('y', lockin.get_y)


	async def execute(self):
		await pause(self.scribe, 10)
		await sweep_lockin_frequency(self.scribe, self.rack.lockin, 10, 50)
		await pause(self.scribe, 3)



async def main():
	exp = SoftExperiment("./data/")
	await asyncio.create_task(exp.run())


asyncio.run(main())
