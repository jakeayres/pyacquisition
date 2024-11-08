from ..instruments import Mercury_IPS
from ..instruments import SR_830, SR_860

# from ..instruments import Lakeshore_340, Lakeshore_350
# from ..instruments.lakeshore.lakeshore_340 import InputChannel as IC340
# from ..instruments.lakeshore.lakeshore_350 import InputChannel as IC350
# from ..instruments.lakeshore.lakeshore_340 import OutputChannel as OC340
# from ..instruments.lakeshore.lakeshore_350 import OutputChannel as OC350

from ..logger import logger
from ..scribe import scribe
from ..dataframe import DataFrame
from .coroutine import Coroutine

# from .stabilize_temperature import StabilizeTemperature
from .sweep_magnetic_field import SweepMagneticField
from .analyse_field_sweep import AnalyseFieldSweep

import asyncio
import numpy as np
from dataclasses import dataclass


@dataclass
class SweepMagneticField(Coroutine):

	dataframe: DataFrame
	lockins: list[SR_830|SR_860]

	# lakeshore: Lakeshore_340|Lakeshore_350
	# lakeshore_input: IC340|IC350 = IC350.INPUT_A
	# lakeshore_output: OC340|OC350 = OC350.OUTPUT_1
	# temperature: float
	# temperature_ramp_rate: float
	# temperature_tolerance: float = 10e-3
	# temperature_drift: float = 5e-4
	# temperature_stability_time: float = 10

	magnet_psu: Mercury_IPS
	field: float
	field_ramp_rate: float
	new_chapter: bool = False

	time_column: str
	field_column: str
	voltage_columns: list[str]


	def string(self):
		return f'Perform field sweep at {self.temperature}K to {self.field}T'



	async def run(self):

		yield ''

		# await self.execute_another_coroutine(
		# 	StabilizeTemperature(
		# 		scribe=self.scribe,
		# 		lakeshore=self.lakeshore,
		# 		setpoint=self.temperature,
		# 		ramp_rate=self.temperature_ramp_rate,
		# 		input_channel=self.lakeshore_input,
		# 		output_channel=self.lakeshore_output,
		# 		mean_tolerance=self.temperature_tolerance,
		# 		maximum_drift=self.temperature_drift,
		# 		stability_time=self.temperature_stability_time,
		# 	)
		# )

		# yield ''

		data = await self.execute_another_coroutine(
			SweepMagneticField(
				magnet_psu=self.magnet_psu,
				setpoint=self.field,
				ramp_rate=self.field_ramp_rate,
			)
		)