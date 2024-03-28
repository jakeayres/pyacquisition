import enum
from typing import Union, Tuple

from ...instruments._instrument import Instrument, query, command


class Keithley_2000(Instrument):

	name = 'Keithley_2000'


	@command
	def set_configuration_ac_current(self) -> str:
		return self._command(f'CONF:CURR:AC')


	@command
	def set_configuration_dc_current(self) -> str:
		return self._command(f'CONF:CURR:DC')


	@command
	def set_configuration_ac_voltage(self) -> str:
		return self._command(f'CONF:VOLT:AC')


	@command
	def set_configuration_dc_voltage(self) -> str:
		return self._command(f'CONF:VOLT:DC')


	@query
	def fetch_reading(self) -> str:
		response = self._query(f'FETC?')
		return response


	@query
	def read_value(self) -> float:
		response = self._query(f'READ?')
		return float(response)


	@query
	def measure_ac_voltage(self) -> float:
		reponse = self._query(f'MEASURE:VOLTAGE:AC?')
		return float(response)


	@query
	def measure_dc_voltage(self) -> float:
		reponse = self._query(f'MEASURE:VOLTAGE:DC?')
		return float(response)


	@command
	def set_continuous_initiation(self) -> int:
		return self._command(f'INITIATE:CONTINUOUS ON')