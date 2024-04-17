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
		response = self._query(f'MEASURE:VOLTAGE:AC?')
		return float(response)


	@query
	def measure_dc_voltage(self) -> float:
		response = self._query(f'MEASURE:VOLTAGE:DC?')
		return float(response)


	@command
	def set_continuous_initiation(self) -> int:
		return self._command(f'INITIATE:CONTINUOUS ON')


	def register_endpoints(self, app):
		super().register_endpoints(app)


		@app.get(f'/{self._uid}/'+'query/raw', tags=[self._uid])
		async def query_raw(string: str) -> str:
			return self._query(string)


		@app.get(f'/{self._uid}/'+'read', tags=[self._uid])
		async def read_value() -> float:
			return self.read_value()


		@app.get(f'/{self._uid}/'+'configuration/set/ac_voltage', tags=[self._uid])
		async def set_configuration_ac_voltage() -> int:
			return self.set_configuration_ac_voltage()


		@app.get(f'/{self._uid}/'+'configuration/set/dc_voltage', tags=[self._uid])
		async def set_configuration_dc_voltage() -> int:
			return self.set_configuration_dc_voltage()


		@app.get(f'/{self._uid}/'+'initiate/continuous', tags=[self._uid])
		async def set_continuous_initiation() -> int:
			return self.set_continuous_initiation()
