from ..instruments import Lakeshore_340, Lakeshore_350
from ..instruments.lakeshore.lakeshore_340 import InputChannel as IC340
from ..instruments.lakeshore.lakeshore_350 import InputChannel as IC350
from ..instruments.lakeshore.lakeshore_340 import OutputChannel as OC340
from ..instruments.lakeshore.lakeshore_350 import OutputChannel as OC350
from ..scribe import Scribe
from ._coroutine import Coroutine
from .ramp_temperature import RampTemperature


import asyncio, time
import numpy as np
from dataclasses import dataclass
from scipy.optimize import curve_fit



@dataclass
class StabilizeTemperature(Coroutine):

	scribe: Scribe
	lakeshore: Lakeshore_340|Lakeshore_350
	setpoint: float
	ramp_rate: float
	input_channel: IC340|IC350 = IC350.INPUT_A
	output_channel: OC340|OC350 = OC350.OUTPUT_1
	mean_tolerance: float = 10e-3
	maximum_drift: float = 1e-3
	stability_time: float = 10
	log_every: float = None
	wait_time: float = 1
	from_cache: bool = False


	def string(self):
		return f"Stabilizing temperature {self.setpoint}"


	def _add_point(self, points, temperature):
		points.append([time.time(), temperature])
		points = [point for point in points if point[0] >= time.time()-self.stability_time]
		return points


	def _acceptable_mean(self, points, log=False):
		mean = np.mean([point[1] for point in points])
		if log:
			self.scribe.log(f"Mean: {mean}", stem='Stab.Temperature')
		return True if np.isclose(mean, self.setpoint, atol=self.mean_tolerance) else False


	def _acceptable_drift(self, points, log=False):
		if self.maximum_drift is None:
			return True
		else:
			popt, _ = curve_fit(
				lambda x, a, b: a + b*x,
				[point[0] for point in points],
				[point[1] for point in points],
				)
			if log:
				self.scribe.log(f"Drift: {popt[1]:.4f}", stem='Stab.Temperature')
			return True if abs(popt[1]) <= self.maximum_drift else False



	async def run(self):

		# Start
		self.scribe.log("Started", stem="Stab.Temperature")
		await asyncio.sleep(self.wait_time)
		yield ''

		# Ramp to setpoint
		ramp_coroutine = RampTemperature(
			self.scribe,
			self.lakeshore,
			self.setpoint,
			self.ramp_rate,
		)
		await ramp_coroutine.coroutine()
		yield ''

		# Acquire data to compute mean and drift
		self.scribe.log(f"Waiting for {self.stability_time}s of data", stem="Stab.Temperature")
		t0 = time.time()
		points = []
		while time.time() - t0 < self.stability_time:
			points = self._add_point(
				points, 
				self.lakeshore.get_temperature(self.input_channel, from_cache=self.from_cache)
			)
			await asyncio.sleep(self.wait_time)
			yield ''

		# Check mean and drift
		self.scribe.log(f"Checking stability. Mean:{self.mean_tolerance}. Drift{self.maximum_drift}", stem="Stab.Temperature")
		mean_ok = self._acceptable_mean(points)
		drift_ok = self._acceptable_drift(points)
		i = 1
		while False in [mean_ok, drift_ok]:
			await asyncio.sleep(self.wait_time)
			points = self._add_point(
				points, 
				self.lakeshore.get_temperature(self.input_channel, from_cache=self.from_cache)
			)
			if (self.log_every is None) or (self.log_every <= 0):
				_log = False
			else:
				if i % self.log_every == 0:
					_log = True
				else:
					_log = False
			mean_ok = self._acceptable_mean(points, log=_log)
			drift_ok = self._acceptable_drift(points, log=_log)
			i+=1
			yield ''

		# Finish
		self.scribe.log("Finished", stem="Stab.Temperature")



	@classmethod
	def register_endpoints(
		cls, 
		experiment,
		lakeshore,
		input_channel,
		output_channel,
		):

		@experiment.api.get('/experiment/stabilize_temperature/', tags=['Experiment'])
		async def stabilize_temperature(
			setpoint: float, 
			ramp_rate: float,
			mean_tolerance: float = 10e-3,
			maximum_drift: float = 1e-3,
			stability_time: float = 10,
			log_every: int = -1,
			) -> int:
			""" Ramp lakeshore to setpoint at ramp rate """
			await experiment.add_task(
				cls(
					scribe=experiment.scribe, 
					lakeshore=lakeshore,
					setpoint=setpoint,
					ramp_rate=ramp_rate,
					input_channel=input_channel,
					output_channel=output_channel,
					mean_tolerance=mean_tolerance,
					maximum_drift=mean_tolerance,
					log_every=log_every,
					)
				)
			return 0


