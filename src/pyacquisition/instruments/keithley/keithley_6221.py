import enum
from typing import Union, Tuple

from ...instruments._instrument import Instrument, query, command


class Keithley_6221(Instrument):

	name: str = 'Keithley_6221'

	@query
	def get_output_state(self) -> bool:
		response = self._query('OUTPUT:STATE?')
		return bool(response)


	@command
	def set_output_state(self, state: bool) -> int:
		return self._command(f'OUTPUT:STATE {int(state)}')


	@query
	def get_current_range(self) -> float:
		response = self._query('SOURCE:CURRENT:RANGE?')
		return float(response)


	@command
	def set_source_amplitude(self, amplitude: float) -> int:
		return self._command(f'SOURCE:CURRENT {amplitude}')



	@command
	def abort_wave(self) -> int:
		return self._command(f':SOURCE:WAVE:ABORT')


	@command
	def arm_wave(self) -> int:
		return self._command(f':SOURCE:WAVE:ARM')


	@command
	def initiate_wave(self) -> int:
		return self._command(f':SOURCE:WAVE:INIT')


	@command
	def set_wave_amplitude(self, amplitude: float) -> int:
		return self._command(f':SOURCE:WAVE:AMPL {amplitude:.2f}')


	@query
	def get_wave_amplitude(self) -> float:
		response = self._query(f':SOURCE:WAVE:AMPL?')
		return float(response)


	@command
	def set_wave_frequency(self, amplitude: float) -> int:
		return self._command(f':SOURCE:WAVE:FREQ {frequency:.2f}')


	@query
	def get_wave_frequency(self) -> float:
		response = self._query(f':SOURCE:WAVE:FREQ?')
		return float(response)


	def register_endpoints(self, app):
		super().register_endpoints(app)


		@app.get(f'/{self._uid}/'+'output/state/get', tags=[self._uid])
		async def get_output_state() -> bool:
			return self.get_output_state()


		@app.get(f'/{self._uid}/'+'output/state/set', tags=[self._uid])
		async def set_output_state(state: bool) -> int:
			return self.set_output_state(state)


		@app.get(f'/{self._uid}/'+'dc_current/amplitude/set', tags=[self._uid])
		async def set_dc_amplitude(amplitude: float) -> int:
			return self.set_source_amplitude(amplitude)


		@app.get(f'/{self._uid}/'+'wave/abort', tags=[self._uid])
		async def abort_wave() -> int:
			return self.abort_wave()


		@app.get(f'/{self._uid}/'+'wave/arm', tags=[self._uid])
		async def arm_wave() -> int:
			return self.arm_wave()


		@app.get(f'/{self._uid}/'+'wave/init', tags=[self._uid])
		async def initiate_wave() -> int:
			return self.initiate_wave()


		@app.get(f'/{self._uid}/'+'wave/ampliude/set', tags=[self._uid])
		async def set_wave_amplitude(ampliude: float) -> int:
			return self.set_wave_amplitude(ampliude)


		@app.get(f'/{self._uid}/'+'wave/ampliude/get', tags=[self._uid])
		async def get_wave_amplitude() -> float:
			return self.get_wave_amplitude()

