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
		"""Identifies the instrument.

		Returns:
			str: The identification string of the instrument.
		"""
		return self.query('*IDN?')


	@mark_command
	def reset(self):
		"""Resets the instrument to its default state.

		Returns:
			int: The result of the reset command.
		"""
		return self.command('*RST')


	@mark_command
	def clear(self):
		"""Clears the instrument's status.

		Returns:
			int: The result of the clear command.
		"""
		return self.command('*CLS')


	@mark_command
	def clear_event_register(self):
		"""Clears the event status register.

		Returns:
			int: The result of the clear event register command.
		"""
		return self.command('*ESR')


	@mark_query
	def get_alarm(self) -> dict:
		"""Queries the alarm status of the instrument.

		Returns:
			dict: A dictionary containing alarm details:
				- state (str): The alarm state.
				- high_value (str): The high alarm value.
				- low_value (str): The low alarm value.
				- deadband (str): The deadband value.
				- latch (str): The latch state.
				- audible (str): The audible alarm state.
				- visible (str): The visible alarm state.
		"""
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
		"""Queries the analog output value.

		Returns:
			float: The analog output value.
		"""
		return float(self.query(f'AOUT?'))


	@mark_command
	def set_autotune_pid(
		self, 
		output: OutputChannel, 
		mode: AutotuneMode,
		):
		"""Sets the autotune PID mode for a specific output channel.

		Args:
			output (OutputChannel): The output channel to configure.
			mode (AutotuneMode): The autotune mode to set.

		Returns:
			int: The result of the autotune PID command.
		"""
		return self.command(f'ATUNE {output.value},{mode.value}')


	@mark_command
	def set_display_contrast(self, contrast: DisplayContrast):
		"""Sets the display contrast level.

		Args:
			contrast (DisplayContrast): The desired display contrast level.

		Returns:
			int: The result of the display contrast command.
		"""
		return self.command(f'BRIGT {contrast.value}')


	@mark_query
	def get_display_contrast(self) -> DisplayContrast:
		"""Queries the current display contrast level.

		Returns:
			DisplayContrast: The current display contrast level.
		"""
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
		"""Sets the curve header information.

		Args:
			curve_index (int): The index of the curve.
			name (str): The name of the curve.
			serial_no (str): The serial number of the curve.
			curve_format (CurveFormat): The format of the curve.
			upper_limit (int): The upper limit of the curve.
			coefficient (CurveCoefficient): The coefficient of the curve.

		Returns:
			int: The result of the curve header command.
		"""
		return self.command(f'CRVHDR {curve_index},{name},{serial_no},{curve_format.value},{upper_limit},{coefficient.value}')


	@mark_query
	def get_curve_header(self, curve_index: int) -> str:
		"""Queries the curve header information.

		Args:
			curve_index (int): The index of the curve.

		Returns:
			str: The curve header information.
		"""
		return self.query(f'CRVHDR? {curve_index}') 


	@mark_query
	def get_curve_point(self, curve_index: int, point_index: int) -> str:
		"""Queries a specific point on a curve.

		Args:
			curve_index (int): The index of the curve.
			point_index (int): The index of the point on the curve.

		Returns:
			str: The curve point information.
		"""
		return self.query(f'CRVPT? {curve_index},{point_index}')


	@mark_command
	def set_curve_point(self, curve_index: int, point_index: int, sensor: float, temperature: float) -> int:
		"""Sets a specific point on a curve.

		Args:
			curve_index (int): The index of the curve.
			point_index (int): The index of the point on the curve.
			sensor (float): The sensor value.
			temperature (float): The temperature value.

		Returns:
			int: The result of the curve point command.
		"""
		return self.command(f'CRVPT {curve_index},{point_index},{sensor},{temperature}')


	@mark_command
	def set_display_setup(self, mode: DisplayMode):
		"""Sets the display mode.

		Args:
			mode (DisplayMode): The desired display mode.

		Returns:
			int: The result of the display setup command.
		"""
		return self.command(f'DISPLAY {mode.value},0,0')


	@mark_command
	def set_custom_display_setup(
		self,
		number: DisplayCustomNumber,
		output_channel: OutputChannel,
		):
		"""Sets a custom display setup.

		Args:
			number (DisplayCustomNumber): The custom display number.
			output_channel (OutputChannel): The output channel to display.

		Returns:
			int: The result of the custom display setup command.
		"""
		return self.command(f'DISPLAY 4,{number.value},{output_channel.value}')


	@mark_query
	def get_display_setup(self) -> list[int]:
		"""Queries the current display setup.

		Returns:
			list[int]: A list of integers representing the display setup.
		"""
		return [int(i) for i in self.query(f'DISPLAY?').split(',')]


	@mark_command
	def set_input_filter(
		self, 
		input_channel: InputChannel,
		state: State,
		points: int, # range 2-64
		window: float, # range 1%-10%
		):
		"""Sets the input filter configuration.

		Args:
			input_channel (InputChannel): The input channel to configure.
			state (State): The state of the filter (ON/OFF).
			points (int): The number of points for the filter (2-64).
			window (float): The filter window percentage (1%-10%).

		Returns:
			int: The result of the input filter command.
		"""
		return self.command(f'FILTER {input_channel.value},{state},{points},{window:.1f}')


	@mark_query
	def get_input_filter(
		self, 
		input_channel: InputChannel,
		) -> Tuple[InputChannel, State, int, float]:
		"""Queries the input filter configuration.

		Args:
			input_channel (InputChannel): The input channel to query.

		Returns:
			Tuple[InputChannel, State, int, float]: A tuple containing:
				- InputChannel: The input channel.
				- State: The state of the filter (ON/OFF).
				- int: The number of points for the filter.
				- float: The filter window percentage.
		"""
		response = self.query(f'FILTER? {input_channel.value}').split(',')
		return (InputChannel(response[0]), FilterState(response[1]), int(response[2]), float(response[3]))


	@mark_query
	def get_temperature(
		self,
		input_channel: InputChannel,
		) -> float:
		"""Queries the temperature reading for a specific input channel.

		Args:
			input_channel (InputChannel): The input channel to query.

		Returns:
			float: The temperature reading.
		"""
		return float(self.query(f'KRDG? {input_channel.value}'))


	@mark_command
	def set_ramp(
		self,
		output_channel: OutputChannel,
		state: State,
		rate: float,
		):
		"""Sets the ramp configuration for a specific output channel.

		Args:
			output_channel (OutputChannel): The output channel to configure.
			state (State): The state of the ramp (ON/OFF).
			rate (float): The ramp rate.

		Returns:
			int: The result of the ramp command.
		"""
		return self.command(f'RAMP {output_channel.value},{state.value},{rate:.3f}')
	
	
	@mark_query
	def get_ramp(
		self, 
		output_channel: OutputChannel,
		) -> float:
		"""Queries the ramp rate for a specific output channel.

		Args:
			output_channel (OutputChannel): The output channel to query.

		Returns:
			float: The ramp rate.
		"""
		response = self.query(f'RAMP? {output_channel.value}').split(',')
		return float(response[1])


	@mark_query
	def get_ramp_status(
		self,
		output_channel: OutputChannel,
		) -> State:
		"""Queries the ramp status for a specific output channel.

		Args:
			output_channel (OutputChannel): The output channel to query.

		Returns:
			State: The ramp status (ON/OFF).
		"""
		return State(int(self.query(f'RAMPST? {output_channel.value}')))


	@mark_command
	def set_setpoint(
		self,
		output_channel: OutputChannel,
		setpoint: float,
		):
		"""Sets the setpoint for a specific output channel.

		Args:
			output_channel (OutputChannel): The output channel to configure.
			setpoint (float): The desired setpoint value.

		Returns:
			int: The result of the setpoint command.
		"""
		return self.command(f'SETP {output_channel.value},{setpoint:.2f}')

	
	@mark_query
	def get_setpoint(
		self,
		output_channel: OutputChannel,
		) -> float:
		"""Queries the setpoint for a specific output channel.

		Args:
			output_channel (OutputChannel): The output channel to query.

		Returns:
			float: The setpoint value.
		"""
		return float(self.query(f'SETP? {output_channel.value}'))


	@mark_query
	def get_resistance(
		self,
		input_channel: InputChannel,
		) -> float:
		"""Queries the resistance reading for a specific input channel.

		Args:
			input_channel (InputChannel): The input channel to query.

		Returns:
			float: The resistance reading.
		"""
		return float(self.query(f'SRDG? {input_channel.value}'))


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
