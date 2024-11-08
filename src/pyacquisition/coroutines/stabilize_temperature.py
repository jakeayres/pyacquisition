from ..logger import logger
from ..instruments import Lakeshore_340, Lakeshore_350
from ..instruments.lakeshore.lakeshore_340 import InputChannel as IC340
from ..instruments.lakeshore.lakeshore_350 import InputChannel as IC350
from ..instruments.lakeshore.lakeshore_340 import OutputChannel as OC340
from ..instruments.lakeshore.lakeshore_350 import OutputChannel as OC350
from ..scribe import Scribe
from .coroutine import Coroutine
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
	mean_tolerance: float = 5e-3
	maximum_drift: float = 5e-4
	stability_time: float = 60
	log_every: float = None
	wait_time: float = 1
	from_cache: bool = False
	new_file: bool = True
	new_chapter: bool = False


	def string(self):
		return f"Stabilizing temperature {self.setpoint}"


	def _add_point(self, points, temperature):
		points.append([time.time(), temperature])
		points = [point for point in points if point[0] >= time.time()-self.stability_time]
		return points


	def _acceptable_mean(self, points, log=False):
		mean = np.mean([point[1] for point in points])
		if log:
			logger.info(f"Mean: {mean}")
		return True if np.isclose(mean, self.setpoint, atol=self.mean_tolerance) else False


	def _acceptable_drift(self, points, log=False):
		if self.maximum_drift is None:
			return True
		else:
			popt, _ = curve_fit(
				lambda x, a, b, c: a + b*x, c*x*x,
				[point[0] for point in points],
				[point[1] for point in points],
				)
			if log:
				logger.info(f"Drift: {popt[1]:.4f}")

			if (abs(popt[1]) <= self.maximum_drift) and (abs(popt[2]) <= self.maximum_drift/10):
				return True
			else:
				return False



	async def run(self):

		# Start
		logger.info("Started temperature stabilization")
		await asyncio.sleep(self.wait_time)
		yield ''

		if self.new_file:
			self.scribe.next_file(f"Stabilizing {self.setpoint:.2f}K", new_chapter=self.new_chapter)

		# Ramp to setpoint
		ramp_coroutine = RampTemperature(
			self.scribe,
			self.lakeshore,
			self.setpoint,
			self.ramp_rate,
			new_file=False,
		)
		await ramp_coroutine.coroutine()
		yield ''

		# Acquire data to compute mean and drift
		logger.info(f"Waiting for {self.stability_time}s of data")
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
		logger.info(f"Checking stability. Mean:{self.mean_tolerance}. Drift{self.maximum_drift}")
		mean_ok, drift_ok = False, False
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
			try:
				mean_ok = self._acceptable_mean(points, log=_log)
				drift_ok = self._acceptable_drift(points, log=_log)
			except Exception as e:
				logger.error('mean and drift not calculated')
				print(e)
				mean_ok, drift_ok = False, False

			i+=1
			yield ''

		# Finish
		logger.info("Temperature stabilization finished")



	@classmethod
	def register_endpoints(
		cls, 
		experiment,
		lakeshore,
		input_channel,
		output_channel,
		):

		@experiment.api.get('/experiment/stabilize_temperature/', tags=['Routines'])
		async def stabilize_temperature(
			setpoint: float, 
			ramp_rate: float,
			mean_tolerance: float = 10e-3,
			maximum_drift: float = 1e-3,
			stability_time: float = 60,
			log_every: int = -1,
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
					input_channel=input_channel,
					output_channel=output_channel,
					mean_tolerance=mean_tolerance,
					maximum_drift=mean_tolerance,
					stability_time=stability_time,
					log_every=log_every,
					new_file=new_file,
					new_chapter=new_chapter,
					)
				)
			return 0


