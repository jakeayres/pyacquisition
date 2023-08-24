from ..instruments import Lakeshore_340, Lakeshore_350
from ..instruments.lakeshore.lakeshore_340 import OutputChannel as OC340
from ..instruments.lakeshore.lakeshore_350 import OutputChannel as OC350
from ..instruments.lakeshore.lakeshore_340 import InputChannel as IC340
from ..instruments.lakeshore.lakeshore_350 import InputChannel as IC350
from ..instruments.lakeshore.lakeshore_350 import State
from ..scribe import Scribe
from ._coroutine import Coroutine


import asyncio
import numpy as np
from dataclasses import dataclass



@dataclass
class RampTemperature(Coroutine):

	scribe: Scribe
	lakeshore: Lakeshore_340|Lakeshore_350
	setpoint: float
	ramp_rate: float
	output_channel: OC340|OC350 = OC350.OUTPUT_1
	tolerance: float = 0.001
	wait_time: float = 1
	new_file: bool = False
	from_cache: bool = False


	def string(self):
		return f'Ramping temperature {self.output_channel} to {self.setpoint} at {self.ramp_rate}K/min'


	async def run(self):

		self.scribe.log('Started', stem='RampTemperature')
		await asyncio.sleep(self.wait_time)
		yield ''

		self.lakeshore.set_ramp(self.output_channel, State.ON, self.ramp_rate)
		self.scribe.log(f'Ramp Rate set: {self.ramp_rate}', stem='RampTemperature')
		await asyncio.sleep(self.wait_time)
		yield ''

		self.lakeshore.set_setpoint(self.output_channel, self.setpoint)
		self.scribe.log(f'Setpoint set: {self.setpoint}', stem='RampTemperature')
		await asyncio.sleep(self.wait_time)

		while not np.isclose(self.lakeshore.get_setpoint(self.output_channel), self.setpoint, atol=self.tolerance):
			await asyncio.sleep(self.wait_time)
			yield ''

		self.scribe.log('Finished', stem='RampTemperature')

		yield ''