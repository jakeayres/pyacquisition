import asyncio
import websockets
import random
import json
from functools import partial

from pyacquisition.experiment import Experiment
from pyacquisition.instruments import Clock, WaveformGenerator, Gizmotron, SR_830, SR_860, Lakeshore_350
from pyacquisition.coroutines import WaitFor, WaitUntil, SweepGizmotron, LockinFrequencySweep
from pyacquisition.visa import resource_manager

from pyacquisition.instruments.lakeshore.lakeshore_350 import OutputChannel, InputChannel

from pyacquisition.coroutines import Coroutine


class SoftExperiment(Experiment):


	def setup(self):
		clock = self.add_software_instrument('clock', Clock)
		self.add_measurement('time', clock.time)

		gizmo = self.add_software_instrument('gizmo', Gizmotron)
		self.add_measurement('value', gizmo.get_value)
		self.add_measurement('value2', gizmo.get_value, call_every=5)

		wave1 = self.add_software_instrument('wave1', WaveformGenerator)
		self.add_measurement('signal_1', wave1.get_signal)


	def register_endpoints(self):
		super().register_endpoints()


		@self.api.get('/experiment/perform_sweep/{max_value}', tags=['Experiment'])
		async def perform_sweep(max_value: float) -> int:
			await self.add_task(SweepGizmotron(self.scribe, self.rack.gizmo, max_value))
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
			rm.open_resource('GPIB0::3::INSTR')
		)

		self.add_measurement('time', clock.time)

		self.add_measurement('x1', lockin1.get_x)
		self.add_measurement('y1', lockin1.get_y)

		self.add_measurement('x2', lockin2.get_x)
		self.add_measurement('y2', lockin2.get_y)

		self.add_measurement('setpoint', partial(lake.get_setpoint, OutputChannel.OUTPUT_1))
		self.add_measurement('resistance', partial(lake.get_resistance, InputChannel.INPUT_A))
		self.add_measurement('temperature', partial(lake.get_temperature, InputChannel.INPUT_A))


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
