import enum
import asyncio
from typing import Union, Tuple

from ...instruments._instrument import Instrument, query, command


class DataFormat(enum.Enum):
	ASCII = 1
	SINT = 2
	DINT = 3
	SREAL = 4
	DREAL = 5


class DataFormatModel(enum.Enum):
	ASCII = 'ASCII'
	SINT = 'SINGLE INT'
	DINT = 'DOUBLE INT'
	SREAL = 'SINGLE REAL'
	DREAL = 'DOUBLE REAL'


class State(enum.Enum):
	OFF = 0
	ON = 1


class StateModel(enum.Enum):
	OFF = 'Off'
	ON = 'On'


class MemoryMode(enum.Enum):
	OFF = 0
	LIFO = 1
	FIFO = 2
	CONT = 3


class MemoryModeModel(enum.Enum):
	OFF = 'Off'
	LIFO = 'LIFO'
	FIFO = 'FIFO'
	CONT = 'Cont.'


class TriggerArmEvent(enum.Enum):
	AUTO = 1
	EXT = 2
	SGL = 3
	HOLD = 4
	SYN = 5

class TriggerArmEventModel(enum.Enum):
	AUTO = 'Automatic'
	EXT = 'External'
	SGL = 'Signal'
	HOLD = 'Hold'
	SYN = 'SYN'

class TriggerSource(enum.Enum):
	AUTO = 1
	EXT = 2
	SGL = 3
	HOLD = 4
	SYN = 5
	LEVEL = 7
	LINE = 8


class TriggerSourceModel(enum.Enum):
	AUTO = 'Automatic'
	EXT = 'External'
	SGL = 'SGL'
	HOLD = 'Hold'
	SYN = 'SYN'
	LEVEL = 'Level'
	LINE = 'Line'




class Keysight_3458a(Instrument):


	name: str = 'Keysight_3458a'


	@command
	def set_auto_zero(self, state: State) -> int:
		return self._command(f'AZERO {state.value}')


	@command
	def set_delay_time(self, delay: float) -> int:
		return self._command(f'DELAY {delay}')


	@command
	def set_display(self, state: State) -> int:
		return self._command(f'DISP {state.value}')


	@command
	def set_memory_format(self, memory_format: DataFormat) -> int:
		return self._command(f'MFORMAT {memory_format.value}')


	@command
	def set_memory_mode(self, memory_mode: MemoryMode) -> int:
		return self._command(f'MEM {memory_mode.value}')


	@command
	def set_output_format(self, output_format: DataFormat) -> int:
		return self._command(f'OFORMAT {output_format.value}')


	@command
	def set_memory_size(self, reading_size: int, subprogram_size: int) -> int:
		return self._command(f'MSIZE {reading_size},{subprogram_size}')


	@command
	def set_integration_time(self, power_line_cycles: int) -> int:
		return self._command(f'NPLC {power_line_cycles}')


	@command
	def set_number_readings(self, N: int) -> int:
		return self._command(f'NRDGS {N}')


	@command
	def set_measurement_sweep(self, interval: float, samples: int) -> int:
		return self._command(f'SWEEP {interval},{samples}')


	@command
	def set_trigger_arm_event(self, event: TriggerArmEvent) -> int:
		return self._command(f'TARM {event.value}')


	@command
	def set_trigger_source(self, source: TriggerSource) -> int:
		return self._command(f'TRIG {source.value}')


	def register_endpoints(self, app):
		super().register_endpoints(app)


		@app.get(f'/{self._uid}/'+'query/raw', tags=[self._uid])
		async def query_raw(message: str) -> str:
			return self._query(message)


		@app.get(f'/{self._uid}/'+'command/raw', tags=[self._uid])
		async def command_raw(message: str) -> str:
			return self._command(message)


		@app.get(f'/{self._uid}/'+'auto_zero/set/{state}', tags=[self._uid])
		async def set_auto_zero(state: StateModel) -> int:
			return self.set_auto_zero(State[state.name])


		@app.get(f'/{self._uid}/'+'delay/set/{delay}', tags=[self._uid])
		async def set_delay_time(delay: float) -> int:
			return self.set_delay_time(delay)


		@app.get(f'/{self._uid}/'+'display/set/{state}', tags=[self._uid])
		async def set_display(state: StateModel) -> int:
			return self.set_display(State[state.name])


		@app.get(f'/{self._uid}/'+'memory_format/set/{memory_format}', tags=[self._uid])
		async def set_memory_format(memory_format: DataFormatModel) -> int:
			return self.set_memory_format(DataFormat[memory_format.name])


		@app.get(f'/{self._uid}/'+'memory_mode/set/{memory_mode}', tags=[self._uid])
		async def set_memory_mode(memory_mode: MemoryModeModel) -> int:
			return self.set_memory_mode(MemoryMode[memory_mode.name])


		@app.get(f'/{self._uid}/'+'output_format/set/{output_format}', tags=[self._uid])
		async def set_output_format(output_format: DataFormatModel) -> int:
			return self.set_output_format(DataFormat[output_format.name])


		@app.get(f'/{self._uid}/'+'memory_size/set', tags=[self._uid])
		async def set_memory_size(size: int) -> int:
			return self.set_memory_size(int)


		@app.get(f'/{self._uid}/'+'integration_time/set', tags=[self._uid])
		async def set_integration_time(power_line_cycles: int) -> int:
			return self.set_integration_time(power_line_cycles)


		@app.get(f'/{self._uid}/'+'number_readings/set', tags=[self._uid])
		async def set_number_readings(N: int) -> int:
			return self.set_number_readings(N)


		@app.get(f'/{self._uid}/'+'trigger_arm_event/set/{event}', tags=[self._uid])
		async def set_trigger_arm_event(event: TriggerArmEventModel) -> int:
			return self.set_trigger_arm_event(TriggerArmEvent[event.name])


		@app.get(f'/{self._uid}/'+'trigger_source/set/{source}', tags=[self._uid])
		async def set_trigger_source(source: TriggerSourceModel) -> int:
			return self.set_trigger_source(TriggerSource[source.name])


		@app.get(f'/{self._uid}/'+'measurement_sweep/set/{interval}/{samples}', tags=[self._uid])
		async def set_trigger_source(interval: float, samples: int) -> int:
			return self.set_measurement_sweep(interval, samples)


		@app.get(f'/{self._uid}/'+'configure/idle', tags=[self._uid])
		async def configure_idle(test: str) -> int:
			self.set_memory_format(DataFormat.DINT)
			await asyncio.sleep(0.1)
			self.set_output_format(DataFormat.ASCII)
			await asyncio.sleep(0.1)
			self.set_auto_zero(State.OFF)
			await asyncio.sleep(0.1)
			self.set_display(State.ON)
			await asyncio.sleep(0.1)
			self.set_memory_mode(MemoryMode.FIFO)
			await asyncio.sleep(0.1)
			self.set_delay_time(0.00)
			await asyncio.sleep(0.1)
			self.set_trigger_arm_event(TriggerArmEvent.AUTO)
			await asyncio.sleep(0.1)
			self.set_trigger_source(TriggerSource.SYN)
			return 0


		@app.get(f'/{self._uid}/'+'configure/ready', tags=[self._uid])
		async def configure_ready(test: str) -> int:
			self.set_memory_format(DataFormat.DINT)
			await asyncio.sleep(0.1)
			self.set_output_format(DataFormat.ASCII)
			await asyncio.sleep(0.1)
			self.set_auto_zero(State.OFF)
			await asyncio.sleep(0.1)
			self.set_display(State.OFF)
			await asyncio.sleep(0.1)
			self.set_memory_mode(MemoryMode.FIFO)
			await asyncio.sleep(0.1)
			self.set_delay_time(0)
			await asyncio.sleep(0.1)
			self.set_trigger_arm_event(TriggerArmEvent.SGL)
			await asyncio.sleep(0.1)
			self.set_trigger_source(TriggerSource.AUTO)
			return 0





