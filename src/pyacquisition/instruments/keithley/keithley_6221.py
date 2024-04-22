from enum import Enum
from typing import Union, Tuple

from ...instruments._instrument import Instrument, query, command


class TriggerEvent(Enum):
	SOURCE = 'SOUR'
	DELAY = 'DEL'
	NONE = 'NONE'


class TriggerEventModel(Enum):
	SOURCE = 'SOURCE'
	DELAY = 'DELAY'
	NONE = 'NONE'


class Keithley_6221(Instrument):


	name: str = 'Keithley_6221'


	@query
	def get_output_state(self) -> bool:
		response = self._query(':OUTPUT:STATE?')
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


	# SOURCE:WAVE commands

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


	#SOURCE:SWEEP commands

	@command
	def abort_sweep(self) -> int:
		return self._command(f':SOUR:SWE:ABOR')


	@command
	def arm_sweep(self) -> int:
		return self._command(f':SOUR:SWE:ARM')


	@command
	def set_sweep_type(self, sweep_type: str) -> int:
		return self._command(f':SOUR:SWE:SPAC {sweep_type}')


	@query
	def get_sweep_type(self) -> str:
		return self._query(f':SOUR:SWE:SPAC?')


	@command
	def set_sweep_count(self, count: int) -> int:
		return self._command(f':SOUR:SWE:COUN {count}')


	@query
	def get_sweep_count(self) -> int:
		return int(self._query(f':SOUR:SWE:COUN?'))


	@command
	def set_sweep_current_list(self, currents: list[float]) -> int:
		list_string = ','.join([f'{c:.3g}' for c in currents])
		return self._command(f':SOUR:LIST:CURR {list_string}')


	@query
	def get_sweep_current_list(self) -> str:
		return self._query(f':SOUR:LIST:CURR?')


	@command
	def set_sweep_delay_list(self, delays: list[float]) -> int:
		list_string = ','.join([f'{d:.3g}' for d in delays])
		return self._command(f':SOUR:LIST:DEL {list_string}')


	@query
	def get_sweep_delay_list(self) -> str:
		return self._query(f':SOUR:LIST:DEL?')


	@command
	def set_sweep_compliance_list(self, compliances: list[float]) -> int:
		list_string = ','.join(compliances)
		return self._command(f':SOUR:LIST:COMP {list_string}')


	@query
	def get_sweep_compliance_list(self) -> str:
		return self._query(f':SOUR:LIST:COMP?')



	# Trigger commands

	@command
	def trigger(self) -> int:
		return self._command(f':INIT')


	@command
	def set_trigger_output_line(self, line: int) -> int:
		return self._command(f':TRIG:OLIN {line}')


	@query
	def get_trigger_output_line(self) -> int:
		return int(self._query(f':TRIG:OLIN?'))


	@command
	def set_trigger_output_event(self, event: TriggerEvent) -> int:
		return self._command(f':TRIG:OUTP {event.value}')


	@query
	def get_trigger_output_event(self, event: TriggerEvent) -> TriggerEvent:
		return TriggerEvent(self._query(f':TRIG:OUTP?'))



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


		@app.get(f'/{self._uid}/'+'wave/amplitude/set', tags=[self._uid])
		async def set_wave_amplitude(amplitude: float) -> int:
			return self.set_wave_amplitude(amplitude)


		@app.get(f'/{self._uid}/'+'wave/amplitude/get', tags=[self._uid])
		async def get_wave_amplitude() -> float:
			return self.get_wave_amplitude()


		@app.get(f'/{self._uid}/'+'wave/frequency/set', tags=[self._uid])
		async def set_wave_frequency(frequency: float) -> int:
			return self.set_wave_frequency(frequency)


		@app.get(f'/{self._uid}/'+'wave/frequency/get', tags=[self._uid])
		async def get_wave_frequency() -> float:
			return self.get_wave_frequency()


		@app.get(f'/{self._uid}/'+'trigger/output_line/set/{line}', tags=[self._uid])
		async def set_trigger_output_line(line: int) -> int:
			return self.set_trigger_output_line(line)


		@app.get(f'/{self._uid}/'+'trigger/output_line/get', tags=[self._uid])
		async def get_trigger_output_line() -> int:
			return self.get_trigger_output_line()


		@app.get(f'/{self._uid}/'+'trigger/output_event/set/{event}', tags=[self._uid])
		async def set_trigger_output_event(event: TriggerEventModel) -> int:
			return self.set_trigger_output_event(TriggerEvent[event.name])


		@app.get(f'/{self._uid}/'+'trigger/output_event/get', tags=[self._uid])
		async def get_trigger_output_event() -> TriggerEvent:
			return self.get_trigger_output_event()


