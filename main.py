import asyncio
import websockets
import random
import json
from functools import partial

from pyacquisition.experiment import Experiment
from pyacquisition.instruments import (
	Clock, WaveformGenerator, Gizmotron, 
	SR_830, SR_860, 
	Lakeshore_340, Lakeshore_350,
	Mercury_IPS
	)
from pyacquisition.visa import resource_manager


from pyacquisition.instruments.lakeshore.lakeshore_350 import OutputChannel, InputChannel

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

		from pyacquisition.coroutines import SweepGizmotron

		@self.api.get('/experiment/perform_sweep/{max_value}', tags=['Experiment'])
		async def perform_sweep(max_value: float) -> int:
			await self.add_task(SweepGizmotron(self.scribe, self.rack.gizmo, max_value))
			return 0


class HardExperiment(Experiment):

	def setup(self):

		rm = resource_manager('pyvisa')


		clock = self.add_software_instrument(
			'Clock', 
			Clock,
		)
		magnet = self.add_hardware_instrument(
			'Magnet', 
			Mercury_IPS, 
			rm.open_resource(
				'GPIB0::26::INSTR', 
				read_termination='\r',
				write_termination='\r',
			)
		)
		lake = self.add_hardware_instrument(
			'Lake', 
			Lakeshore_340, 
			rm.open_resource('GPIB0::2::INSTR')
		)
		lockin1 = self.add_hardware_instrument(
			'Lockin1', 
			SR_830, 
			rm.open_resource('GPIB0::7::INSTR')
		)
		lockin2 = self.add_hardware_instrument(
			'Lockin2', 
			SR_830, 
			rm.open_resource('GPIB0::8::INSTR')
		)

		self.add_measurement('time', clock.time)
		self.add_measurement('temperature', partial(lake.get_temperature, InputChannel.INPUT_A))
		self.add_measurement('field', magnet.get_output_field)
		self.add_measurement('x1', lockin1.get_x)
		self.add_measurement('y1', lockin1.get_y)
		self.add_measurement('x2', lockin2.get_x)
		self.add_measurement('y2', lockin2.get_y)


	def register_endpoints(self):
		super().register_endpoints()

		from pyacquisition.coroutines import RampTemperature
		RampTemperature.register_endpoints(self, self.rack.Lake, OutputChannel.OUTPUT_1)

		from pyacquisition.coroutines import StabilizeTemperature
		StabilizeTemperature.register_endpoints(self, self.rack.Lake, InputChannel.INPUT_A, OutputChannel.OUTPUT_1)

		from pyacquisition.coroutines import SweepMagneticField
		SweepMagneticField.register_endpoints(self, self.rack.Magnet)

		from pyacquisition.coroutines import CreateNewFile
		CreateNewFile.register_endpoints(self)


async def main():
	exp = HardExperiment("../data/")
	await asyncio.create_task(exp.run())


asyncio.run(main())
