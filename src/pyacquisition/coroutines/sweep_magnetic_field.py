from ..instruments import Mercury_IPS
from ..instruments.oxford_instruments.mercury_ips import (
	ActivityStatus, SystemStatusM, SwitchHeaterStatus, ModeStatusN
	)

from ..scribe import scribe
from ..dataframe import DataFrame
from .coroutine import Coroutine


import asyncio
import numpy as np
from dataclasses import dataclass


@dataclass
class SweepMagneticField(Coroutine):

	magnet_psu: Mercury_IPS
	setpoint: float
	ramp_rate: float
	wait_time: float = 1
	from_cache: bool = False
	new_chapter: bool = False


	def string(self):
		return f"Sweeping field to {self.setpoint} T at {self.ramp_rate} T/min"


	async def check_system_normal(self):

		system_status, activity_status = None, None

		try:
			system_status = self.magnet_psu.get_system_status()
			await asyncio.sleep(self.wait_time)
			logger.info(f'Checking magnet system status: {system_status.name}')
			await asyncio.sleep(self.wait_time)
		except Exception as e:
			logger.error('Magnet system status was not retrieved')
			print(e)
			raise e

		if system_status != SystemStatusM.NORMAL:
			raise ValueError(f'Magnet system status {system_status}. Expected {SystemStatusM.NORMAL}')



	async def check_is_holding(self):

		try:
			activity_status = self.magnet_psu.get_activity_status()
			await asyncio.sleep(self.wait_time)
			logger.info(f'Checking magnet activity status: {activity_status.name}')
			await asyncio.sleep(self.wait_time)
		except Exception as e:
			logger.error('Magnet activity status was not retrieved')
			print(e)
			raise e

		if activity_status != ActivityStatus.HOLD:
			raise ValueError(f'Magnet activity status {activity_status}. Expected {ActivityStatus.HOLD}')


	async def check_is_to_setpoint(self):

		try:
			activity_status = self.magnet_psu.get_activity_status()
			await asyncio.sleep(self.wait_time)
			logger.info(f'Checking magnet activity status: {activity_status.name}')
			await asyncio.sleep(self.wait_time)
		except Exception as e:
			logger.error('Magnet activity status was not retrieved')
			print(e)
			raise e

		if activity_status != ActivityStatus.TO_SETPOINT:
			raise ValueError(f'Magnet activity status {activity_status}. Expected {ActivityStatus.TO_SETPOINT}')


	async def check_is_to_zero(self):

		try:
			activity_status = self.magnet_psu.get_activity_status()
			await asyncio.sleep(self.wait_time)
			logger.info(f'Checking magnet activity status: {activity_status.name}')
			await asyncio.sleep(self.wait_time)
		except Exception as e:
			logger.error('Magnet activity status was not retrieved')
			print(e)
			raise e

		if activity_status != ActivityStatus.TO_ZERO:
			raise ValueError(f'Magnet activity status {activity_status}. Expected {ActivityStatus.TO_ZERO}')



	async def set_ramp_rate(self, ramp_rate):

		# Set ramp rate
		try:
			ans = self.magnet_psu.set_field_sweep_rate(self.ramp_rate)
			await asyncio.sleep(self.wait_time)
		except Exception as e:
			logger.error('Error setting ramp rate')
			raise e

		# Check ramp rate is set to desired value
		try:
			rate = self.magnet_psu.get_field_sweep_rate()
			await asyncio.sleep(self.wait_time)
			logger.info(f'Ramp rate set to {ramp_rate} T/min OK')
		except Exception as e:
			logger.error('Error getting ramp rate')
			raise e

		if rate != self.ramp_rate:
			raise ValueError(f'Retrieved ramp rate not equal to set value. Set: {self.ramp_rate}. Got: {rate}')


	async def set_setpoint(self, setpoint):

		try:
			ans = self.magnet_psu.set_target_field(setpoint)
			await asyncio.sleep(self.wait_time)
		except Exception as e:
			logger.error('Error setting target field')
			print(e)

		try:
			retrieved_setpoint = self.magnet_psu.get_setpoint_field()
			await asyncio.sleep(self.wait_time)
			logger.info(f'Setpoint set to {setpoint} T')
		except Exception as e:
			logger.error('Error setting field setpoint')
			raise e

		if retrieved_setpoint != setpoint:
			raise ValueError(f'Retrieved setpoint not equal to set value. Set: {setpoint}. Got: {retrieved_setpoint}')


	async def switch_heater_on(self):

		try:
			logger.info('Switching switch heater on')
			self.magnet_psu.heater_on()
			await asyncio.sleep(15)
		except Exception as e:
			logger.error('magnet_psu.heater_on() failed')
			print(e)
			raise e

		heater_status = None

		try:
			heater_status = self.magnet_psu.get_switch_heater_status()
			await asyncio.sleep(self.wait_time)
			logger.info('Switch heater switched on OK.')
		except Exception as e:
			logger.error('Switch heater status not retrieved')
			print(e)
			raise e


	async def switch_heater_off(self):

		try:
			logger.info('Switching switch heater off')
			self.magnet_psu.heater_off()
			await asyncio.sleep(15)
		except Exception as e:
			logger.error('magnet_psu.heater_off() failed')
			print(e)
			raise e

		try:
			heater_status = self.magnet_psu.get_switch_heater_status()
			await asyncio.sleep(self.wait_time)
			logger.info('Switch heater switch off OK.')
		except Exception as e:
			logger.error('Switch heater status not retrieved')
			print(e)
			raise e


	async def sweep_to_setpoint(self, setpoint):

		try:
			await self.set_setpoint(setpoint)
			await asyncio.sleep(self.wait_time)
			self.magnet_psu.to_setpoint()
			await asyncio.sleep(self.wait_time)
			await self.check_is_to_setpoint()
			await asyncio.sleep(self.wait_time)
			logger.info(f'Sweeping field to {setpoint}')
			while self.magnet_psu.get_sweep_status() != ModeStatusN.REST:
				await asyncio.sleep(self.wait_time)
			logger.info(f'Reached setpoint field of {setpoint} T')
		except Exception as e:
			logger.error(f'Error sweeping up to setpoint field')
			raise e


	async def sweep_to_zero(self):

		try:
			self.magnet_psu.to_zero()
			await asyncio.sleep(self.wait_time)
			await self.check_is_to_zero()
			await asyncio.sleep(self.wait_time)
			logger.info(f'Sweeping field to 0 T')
			while self.magnet_psu.get_sweep_status() != ModeStatusN.REST:
				await asyncio.sleep(self.wait_time)
			logger.info(f'Reached zero field')
		except Exception as e:
			logger.error(f'Error sweeping down to zero field')
			raise e



	async def run(self):

		await asyncio.sleep(self.wait_time)
		yield None

		try:

			scribe.next_file(f'Field Sweep to {"p" if self.setpoint>=0 else "n"}{abs(self.setpoint):.1f}T', new_chapter=self.new_chapter)

			# Check system status
			await self.check_system_normal()
			yield None

			# Check activity status
			await self.check_is_holding()
			yield None

			# Turn on switch heater
			await self.switch_heater_on()
			yield None

			# Set ramp rate
			await self.set_ramp_rate(self.ramp_rate)
			yield None

			# Go to setpoint
			await self.sweep_to_setpoint(self.setpoint)
			yield None

			scribe.next_file(f'Field Sweep to 0T', new_chapter=False)

			# Go to zero
			await self.sweep_to_zero()
			yield None

			self.process_dataframe()
			yield None

			# Turn off switch heater
			await self.switch_heater_off()
			

		except Exception as e:
			logger.error('Error during field sweep')
			print(e)
			raise e

		finally:
			# Raise exception if magnet status isn't normal (eg quenched, fault)
			await self.check_system_normal()
			yield None


		



	@classmethod
	def register_endpoints(
		cls, 
		experiment,
		magnet_psu,
		):

		@experiment.api.get('/experiment/sweep_magnetic_field/one_polarity/', tags=['Routines'])
		async def sweep_field_one_polarity(
			setpoint: float,
			ramp_rate: float,
			new_chapter: bool = False,
			) -> int:
			""" Field sweep at ramp_rate to setpoint and back to zero"""
			await experiment.add_task(
				cls(
					magnet_psu=magnet_psu, 
					setpoint=setpoint, 
					ramp_rate=ramp_rate,
					)
				)
			return 0


		@experiment.api.get('/experiment/sweep_magnetic_field/both_polarities/', tags=['Routines'])
		async def sweep_field_both_polarities(
			setpoint: float,
			ramp_rate: float,
			new_chapter: bool = False,
			) -> int:
			""" Field sweep at ramp_rate to setpoint and back to zero in both polarities"""
			await experiment.add_task(
				cls(
					magnet_psu=magnet_psu, 
					setpoint=setpoint, 
					ramp_rate=ramp_rate,
					new_chapter=new_chapter,
					)
				)
			await experiment.add_task(
				cls(
					magnet_psu=magnet_psu, 
					setpoint=-setpoint, 
					ramp_rate=ramp_rate,
					new_chapter=False,
					)
				)
			return 0