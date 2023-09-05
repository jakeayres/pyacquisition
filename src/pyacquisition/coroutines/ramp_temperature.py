from ..instruments import Lakeshore_340, Lakeshore_350
from ..instruments.lakeshore.lakeshore_340 import OutputChannel as OC340
from ..instruments.lakeshore.lakeshore_350 import OutputChannel as OC350
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
	tolerance: float = 1e-3
	wait_time: float = 1
	from_cache: bool = False
	new_file: bool = True
	new_chapter: bool = False


	def string(self):
		return f'Ramping temperature {self.output_channel} to {self.setpoint} at {self.ramp_rate}K/min'


	async def run(self):

		if self.new_file:
			self.scribe.next_file(f'Temperature Sweep to {self.setpoint:.2f}K', new_chapter=self.new_chapter)

		await asyncio.sleep(self.wait_time)
		yield ''

		self.lakeshore.set_ramp(self.output_channel, State.ON, self.ramp_rate)
		self.scribe.log(f'Ramp Rate set: {self.ramp_rate}', stem='RampTemperature')
		await asyncio.sleep(self.wait_time)
		yield ''

		self.lakeshore.set_setpoint(self.output_channel, self.setpoint)
		self.scribe.log(f'Setpoint set: {self.setpoint}', stem='RampTemperature')
		await asyncio.sleep(self.wait_time)

		while not np.isclose(
			self.lakeshore.get_setpoint(
				self.output_channel,
				from_cache=self.from_cache,
				), 
			self.setpoint, 
			atol=self.tolerance):
			await asyncio.sleep(self.wait_time)
			yield ''

		self.scribe.log('Finished', stem='RampTemperature')

		yield ''


	@classmethod
	def register_endpoints(
		cls, 
		experiment,
		lakeshore,
		output_channel,
		path: str = '/experiment/ramp_temperature/',
		):

		@experiment.api.get(path, tags=['Experiment'])
		async def ramp_temperature(
			setpoint: float,
			ramp_rate: float,
			new_file: bool = True,
			new_chapter: bool = False,
			) -> int:
			""" Ramp lakeshore to setpoint at ramp rate """
			await experiment.add_task(
				cls(
					scribe=experiment.scribe, 
					lakeshore=lakeshore, 
					setpoint=setpoint, 
					ramp_rate=ramp_rate,
					output_channel=output_channel,
					new_chapter=new_chapter,
					)
				)
			return 0