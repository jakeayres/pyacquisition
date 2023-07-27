import asyncio
import websockets
import random
import json

from pyacquisition.experiment import Experiment
from pyacquisition.instruments import Clock, WaveformGenerator, Gizmotron, SR_830, SR_860
from pyacquisition.coroutines import pause, sweep_gizmotron, sweep_lockin_frequency
from pyacquisition.visa import resource_manager


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

		wave3 = self.add_software_instrument('wave3', WaveformGenerator)
		self.add_measurement('signal_3', wave3.get_signal)

		wave4 = self.add_software_instrument('wave4', WaveformGenerator)
		self.add_measurement('signal_4', wave4.get_signal)

		wave5 = self.add_software_instrument('wave5', WaveformGenerator)
		self.add_measurement('signal_5', wave5.get_signal)

		wave6 = self.add_software_instrument('wave6', WaveformGenerator)
		self.add_measurement('signal_6', wave6.get_signal)

		self.add_measurement('half signal', lambda: gizmo.get_value(from_cache=True)/2)
		self.add_measurement('half wave', lambda: wave1.get_signal(from_cache=True)*gizmo.get_value(from_cache=True))

		wave6.set_amplitude(3)

	def register_endpoints(self):
		super().register_endpoints()
		
		@self.api.get("/current_file")
		def message():
			return {'message': f'{self.scribe.filename}'}


	async def execute(self):
		await pause(self.scribe, 3)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 300)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 400)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 300)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 400)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 300)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 400)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 300)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 400)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 300)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 400)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 300)
		await sweep_gizmotron(self.scribe, self.rack.gizmo, 400)



class HardExperiment(Experiment):

	def setup(self):

		clock = self.add_software_instrument('clock', Clock)
		self.add_measurement('time', clock.time)

		lockin = self.add_hardware_instrument(
			'lockin', 
			SR_860, 
			resource_manager('prologix', com_port=3).open_resource('GPIB0::4::INSTR')
		)
		self.add_measurement('freq', lockin.get_frequency)
		self.add_measurement('x', lockin.get_x)
		self.add_measurement('y', lockin.get_y)


	async def execute(self):
		await pause(self.scribe, 10)
		await sweep_lockin_frequency(self.scribe, self.rack.lockin, 10, 200)
		await pause(self.scribe, 3)



async def main():
	exp = SoftExperiment("./data/")
	await asyncio.create_task(exp.run())


asyncio.run(main())
