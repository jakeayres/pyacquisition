import asyncio
import websockets
import random
import json

from pyacquisition.experiment import Experiment
from pyacquisition.instruments import Clock, WaveformGenerator, Gizmotron, SR_830, SR_860, Lakeshore_350
from pyacquisition.coroutines import pause, sweep_gizmotron, SweepGizmotron, sweep_lockin_frequency, LockinFrequencySweep
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

		@self.api.get('/experiment/perform_sweep/{max_value}', tags=['Experiment'])
		async def perform_sweep(max_value: float) -> int:
			await self.task_queue.put(SweepGizmotron(self.scribe, self.rack.gizmo, max_value))
			return 0




class HardExperiment(Experiment):

	def setup(self):

		rm = resource_manager('prologix', com_port=3)

		clock = self.add_software_instrument(
			'Clock', 
			Clock,
		)

		lockin1 = self.add_hardware_instrument(
			'Lockin1', 
			SR_860, 
			rm.open_resource('GPIB0::1::INSTR')
		)
		lockin2 = self.add_hardware_instrument(
			'Lockin2', 
			SR_860, 
			rm.open_resource('GPIB0::2::INSTR')
		)
		lake = self.add_hardware_instrument(
			'Lakeshore', 
			Lakeshore_350, 
			rm.open_resource('GPIB0::2::INSTR')
		)

		self.add_measurement('time', clock.time)

		self.add_measurement('freq1', lockin1.get_frequency)
		self.add_measurement('x1', lockin1.get_x)
		self.add_measurement('y1', lockin1.get_y)

		self.add_measurement('freq2', lockin2.get_frequency)
		self.add_measurement('x2', lockin2.get_x)
		self.add_measurement('y2', lockin2.get_y)


	def register_endpoints(self):
		super().register_endpoints()

		@self.api.get('/experiment/perform_sweep/{max_value}', tags=['Experiment'])
		async def perform_sweep(max_value: float) -> int:
			await self.task_queue.put(LockinFrequencySweep(self.scribe, self.rack.Lockin1, 1, max_value))
			return 0




async def main():
	exp = SoftExperiment("./data/")
	await asyncio.create_task(exp.run())


asyncio.run(main())
