import enum
from typing import Union, Tuple

from ...instruments._instrument import Instrument, query, command


class Keithley_6221(Instrument):

	name = 'Keithley_6221'



	@query
	def get_current_range() -> float:
		response = self._query('SOURCE:CURRENT:RANGE?')
		return float(response)


	@command
	def abort_wave() -> int:
		return self._command(f':SOURCE:WAVE:ABORT')


	@command
	def arm_wave() -> int:
		return self._command(f':SOURCE:WAVE:ARM')


	@command
	def initiate_wave() -> int:
		return self._command(f':SOURCE:WAVE:INIT')


	@command
	def set_wave_amplitude(amplitude: float) -> int:
		return self._command(f':SOURCE:WAVE:AMPL {amplitude:.2f}')


	@query
	def get_wave_amplitude() -> float:
		response = self._query(f':SOURCE:WAVE:AMPL?')
		return float(response)


	@command
	def set_wave_frequency(amplitude: float) -> int:
		return self._command(f':SOURCE:WAVE:FREQ {frequency:.2f}')


	@query
	def get_wave_frequency() -> float:
		response = self._query(f':SOURCE:WAVE:FREQ?')
		return float(response)
