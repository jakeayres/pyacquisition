import enum
from typing import Union, Tuple

from ...core.instrument import Instrument, mark_query, mark_command



class State(enum.Enum):
	OFF = 0
	ON = 1

class StateModel(enum.Enum):
	OFF = 'Off'
	ON = 'On'


class InputChannel(enum.Enum):
	INPUT_A = 'A'
	INPUT_B = 'B'
	INPUT_C = 'C'
	INPUT_D = 'D'

class InputChannelModel(enum.Enum):
	INPUT_A = 'Input A'
	INPUT_B = 'Input B'
	INPUT_C = 'Input C'
	INPUT_D = 'Input D'


class OutputChannel(enum.Enum):
	OUTPUT_1 = 1
	OUTPUT_2 = 2
	OUTPUT_3 = 3
	OUTPUT_4 = 4

class OutputChannelModel(enum.Enum):
	OUTPUT_1 = 'Output 1'
	OUTPUT_2 = 'Output 2'
	OUTPUT_3 = 'Output 3'
	OUTPUT_4 = 'Output 4'


class AutotuneMode(enum.Enum):
	P = 0
	PI = 1
	PID = 2

class AutotuneModeModel(enum.Enum):
	P = 'P'
	PI = 'PI'
	PID = 'PID'


class CurveFormat(enum.Enum):
	MV_K = 1
	V_K = 2
	OHM_K = 3
	LOGOHM_K = 4

class CurveFormatModel(enum.Enum):
	MV_K = 'mV / K'
	V_K = 'V / K'
	OHM_K = 'Ohm / K'
	LOGOHM_K = 'log(Ohm) / K'


class CurveCoefficient(enum.Enum):
	NEGATIVE = 1
	POSITIVE = 2

class CurveCoefficientModel(enum.Enum):
	NEGATIVE = 'Negative'
	POSITIVE = 'Positive'


class DisplayContrast(enum.Enum):
	OFF = 1
	DIM = 12
	NORMAL = 18
	BRIGHT = 26
	MAXIMUM = 32

class DisplayContrastModel(enum.Enum):
	OFF = 'Off'
	DIM = 'Dim'
	NORMAL = 'Normal'
	BRIGHT = 'Bright'
	MAXIMUM = 'Maximum'


class DisplayMode(enum.Enum):
	INPUT_A = 0
	INPUT_B = 1
	INPUT_C = 2
	INPUT_D = 3
	#CUSTOM = 4
	FOUR_LOOP = 5
	ALL_INPUTS = 6
	INPUT_D2 = 7
	INPUT_D3 = 8
	INPUT_D4 = 9
	INPUT_D5 = 10


class DisplayCustomNumber(enum.Enum):
	LARGE_2 = 0
	LARGE_4 = 1
	SMALL_8 = 2


class DisplayAllInputsSize(enum.Enum):
	SMALL = 0
	LARGE = 1



class Lakeshore_350(Instrument):

	name = 'Lakeshore_350'

	""" COMMANDS AS LISTED IN 350 MANUAL (ALPHABETICALLY)
	"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.clear()
		self.clear_event_register()
	

	@mark_query
	def identify(self):
		return self.query('*IDN?')


	@mark_command
	def reset(self):
		return self.command('*RST')


	@mark_command
	def clear(self):
		return self.command('*CLS')


	@mark_command
	def clear_event_register(self):
		return self.command('*ESR')


	@mark_query
	def get_alarm(self) -> dict:
		response = self.query(f'ALARM?').split(',')
		return {
			'state': response[0],
			'high_value': response[1],
			'low_value': response[2],
			'deadband': response[3],
			'latch': response[4],
			'audible': response[5],
			'visible': response[6]
		}


	@mark_query
	def get_analog_output(self) -> float:
		return float(self.query(f'AOUT?'))


	@mark_command
	def set_autotune_pid(
		self, 
		output: OutputChannel, 
		mode: AutotuneMode,
		):
		return self.command(f'ATUNE {output.value},{mode.value}')


	@mark_command
	def set_display_contrast(self, contrast: DisplayContrast):
		return self.command(f'BRIGT {contrast.value}')


	@mark_query
	def get_display_contrast(self) -> DisplayContrast:
		return DisplayContrast(int(self.query(f'BRIGT?')))


	@mark_command
	def set_curve_header(
		self, 
		curve_index: int, 
		name: str, 
		serial_no: str, 
		curve_format: CurveFormat,
		upper_limit: int,
		coefficient: CurveCoefficient
		):
		return self.command(f'CRVHDR {curve_index},{name},{serial_no},{curve_format.value},{upper_limit},{coefficient.value}')


	@mark_query
	def get_curve_header(self, curve_index: int) -> str:
		return self.query(f'CRVHDR? {curve_index}') 


	@mark_query
	def get_curve_point(self, curve_index: int, point_index: int) -> str:
		return self.query(f'CRVPT? {curve_index},{point_index}')


	@mark_command
	def set_curve_point(self, curve_index: int, point_index: int, sensor: float, temperature: float) -> int:
		return self.command(f'CRVPT {curve_index},{point_index},{sensor},{temperature}')


	@mark_command
	def set_display_setup(self, mode: DisplayMode):
		return self.command(f'DISPLAY {mode.value},0,0')


	@mark_command
	def set_custom_display_setup(
		self,
		number: DisplayCustomNumber,
		output_channel: OutputChannel,
		):
		return self.command(f'DISPLAY 4,{number.value},{output_channel.value}')


	@mark_query # NEED TO CAST RESULT AS TUPLE OF ENUMS?
	def get_display_setup(self) -> list[int]:
		return [int(i) for i in self.query(f'DISPLAY?').split(',')]


	@mark_command
	def set_input_filter(
		self, 
		input_channel: InputChannel,
		state: State,
		points: int, # range 2-64
		window: float, # range 1%-10%
		):
		return self.command(f'FILTER {input_channel.value},{state},{points},{window:.1f}')


	@mark_query
	def get_input_filter(
		self, 
		input_channel: InputChannel,
		) -> Tuple[InputChannel, State, int, float]:
		response = self.query(f'FILTER? {input_channel.value}').split(',')
		return (InputChannel(response[0]), FilterState(response[1]), int(response[2]), float(response[3]))


	# HEATER OUTPUT QUERY

	# HEATER SETUP COMMAND

	# HEATER SETUP QUERY

	# HEATER STATUS QUERY

	@mark_query
	def get_temperature(
		self,
		input_channel: InputChannel,
		) -> float:
		return float(self.query(f'KRDG? {input_channel.value}'))

	# FRONT PLANEL LOCK

	# FRONT PANEL QUERY

	# MANUAL OUTPUT COMMAND

	# MANUAL OUTPUT QUERY

	# OUTPUT MODE COMMAND

	# OUTPUT MODE QUERY

	# PID COMMAND

	# PID QUERY

	
	@mark_command
	def set_ramp(
		self,
		output_channel: OutputChannel,
		state: State,
		rate: float,
		):
		return self.command(f'RAMP {output_channel.value},{state.value},{rate:.3f}')
	
	
	@mark_query
	def get_ramp(
		self, 
		output_channel: OutputChannel,
		) -> float:
		response = self.query(f'RAMP? {output_channel.value}').split(',')
		return float(response[1])


	@mark_query
	def get_ramp_status(
		self,
		output_channel: OutputChannel,
		) -> State:
		return State(int(self.query(f'RAMPST? {output_channel.value}')))

	# HEATER RANGE COMMAND

	# HEATER RANGE QUERY

	# INPUT READING STATUS QUERY

	
	@mark_command
	def set_setpoint(
		self,
		output_channel: OutputChannel,
		setpoint: float,
		):
		return self.command(f'SETP {output_channel.value},{setpoint:.2f}')

	
	@mark_query
	def get_setpoint(
		self,
		output_channel: OutputChannel,
		) -> float:
		return float(self.query(f'SETP? {output_channel.value}'))


	@mark_query
	def get_resistance(
		self,
		input_channel: InputChannel,
		) -> float:
		return float(self.query(f'SRDG? {input_channel.value}'))


	# TEMPERATURE LIMIT COMMAND

	# TEMPERATURE LIMIT QUERY


	def register_endpoints(self, app):
		super().register_endpoints(app)


		@app.get(f'/{self._uid}/'+'setpoint/get/', tags=[self._uid])
		async def get_setpoint(channel: OutputChannelModel) -> float:
			return self.get_setpoint(OutputChannel[channel.name])

		@app.get(f'/{self._uid}/'+'setpoint/set/', tags=[self._uid])
		async def set_setpoint(channel: OutputChannelModel, setpoint: float) -> int:
			self.set_setpoint(OutputChannel[channel.name], setpoint)
			return 0


		@app.get(f'/{self._uid}/'+'ramp/get/{channel}', tags=[self._uid])
		async def get_ramp(channel: OutputChannelModel) -> float:
			return self.get_ramp(OutputChannel[channel.name])

		@app.get(f'/{self._uid}/'+'ramp/set/', tags=[self._uid])
		async def set_ramp(channel: OutputChannelModel, state: StateModel, rate: float) -> int:
			self.set_ramp(OutputChannel[channel.name], State[state.name], rate)
			return 0

		@app.get(f'/{self._uid}/'+'ramp_status/get/', tags=[self._uid])
		async def get_ramp_status(channel: OutputChannelModel) -> StateModel:
			return StateModel[self.get_ramp_status(OutputChannel[channel.name]).name]


		@app.get(f'/{self._uid}/'+'temperature/get/', tags=[self._uid])
		async def get_temperature(channel: InputChannelModel) -> float:
			return self.get_temperature(InputChannel[channel.name])

		@app.get(f'/{self._uid}/'+'resistance/get/', tags=[self._uid])
		async def get_resistance(channel: InputChannelModel) -> float:
			return self.get_resistance(InputChannel[channel.name])


		@app.get(f'/{self._uid}/'+'curve_header/get/', tags=[self._uid])
		async def get_curve_header(curve_index: int) -> str:
			return self.get_curve_header(curve_index)

		@app.get(f'/{self._uid}/'+'curve_header/set/', tags=[self._uid])
		async def set_curve_header(
			curve_index: int,
			curve_name: str,
			serial_no: str,
			curve_format: CurveFormatModel,
			upper_limit: int,
			curve_coefficient: CurveCoefficientModel,
			) -> int:
			self.set_curve_header(
				curve_index, 
				curve_name, 
				serial_no, 
				CurveFormat[curve_format.name], 
				upper_limit, 
				CurveCoefficient[curve_coefficient.name]
				)
			return 0

		@app.get(f'/{self._uid}/'+'curve_point/get/', tags=[self._uid])
		async def get_curve_point(curve_index: int, point_index: int) -> str:
			return self.get_curve_point(curve_index, point_index)

		@app.get(f'/{self._uid}/'+'curve_point/set/', tags=[self._uid])
		async def set_curve_point(curve_index: int, point_index: int, sensor: float, temperature: float) -> str:
			return self.set_curve_point(curve_index, point_index, sensor, temperature)
		