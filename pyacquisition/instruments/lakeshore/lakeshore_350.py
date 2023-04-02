import enum
from typing import Union, Tuple

from ...instruments._instrument import Instrument, query, command


class AutotuneMode(enum.Enum):
	P = 0
	PI = 1
	PID = 2


class DisplayContrast(enum.Enum):
	OFF = 1
	DIM = 12
	NORMAL = 18
	BRIGHT = 26
	MAXIMUM = 32


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


class DisplayCustomOutput(enum.Enum):
	OUTPUT_1 = 1
	OUTPUT_2 = 2
	OUTPUT_3 = 3
	OUTPUT_4 = 4


class FilterInput(enum.Enum):
	INPUT_A = 'A'
	INPUT_B = 'B'
	INPUT_C = 'C'
	INPUT_D = 'D'


class FilterState(enum.Enum):
	OFF = 0
	ON = 1



class Lakeshore_350(Instrument):

	name = 'Lakeshore_350'

	""" COMMANDS AS LISTED IN 350 MANUAL (ALPHABETICALLY)
	"""

	@query
	def get_alarm(self) -> dict:
		response = self._query(f'ALARM?').split(',')
		return {
			'state': response[0],
			'high_value': response[1],
			'low_value': response[2],
			'deadband': response[3],
			'latch': response[4],
			'audible': response[5],
			'visible': response[6]
		}


	@query
	def get_analog_output(self) -> float:
		return float(self._query(f'AOUT?'))


	@command
	def set_autotune_pid(self, output: int, mode: AutotuneMode):
		return self._command(f'ATUNE {output},{mode.value}')


	@command
	def set_display_contrast(self, contrast: DisplayContrast):
		return self._command(f'BRIGT {contrast.value}')


	@query
	def get_display_contrast(self) -> DisplayContrast:
		return DisplayContrast(int(self._query(f'BRIGT?'))).name


	@command
	def set_display_setup(self, mode: DisplayMode):
		return self._command(f'DISPLAY {mode.value},0,0')


	@command
	def set_custom_display_setup(self,
		number: DisplayCustomNumber,
		output_source: DisplayCustomOutput,
		):
		return self._command(f'DISPLAY 4,{number.value},{output_source.value}')


	@query # NEED TO CAST RESULT AS TUPLE OF ENUMS?
	def get_display_setup(self) -> list[int]:
		return [int(i) for i in self._query(f'DISPLAY?').split(',')]


	@command
	def set_input_filter(self, 
		input_channel: FilterInput,
		state: FilterState,
		points: int, # range 2-64
		window: float, # range 1%-10%
		):
		return self._command(f'FILTER {input_channel.value},{state},{points},{window:.1f}')


	@query
	def get_input_filter(self, input_channel: FilterInput) -> Tuple[FilterInput, FilterState, int, float]:
		response = self._query(f'FILTER? {input_channel.value}').split(',')
		return (FilterInput(response[0]).name, FilterState(response[1]).name, int(response[2]), float(response[3]))


	# HEATER OUTPUT QUERY

	# HEATER SETUP COMMAND

	# HEATER SETUP QUERY

	# HEATER STATUS QUERY

	# FRONT PLANEL LOCK

	# FRONT PANEL QUERY

	# MANUAL OUTPUT COMMAND

	# MANUAL OUTPUT QUERY

	# OUTPUT MODE COMMAND

	# OUTPUT MODE QUERY

	# PID COMMAND

	# PID QUERY

	# RAMP COMMAND
	
	# RAMP QUERY

	# RAMP STATUS QUERY

	# HEATER RANGE COMMAND

	# HEATER RANGE QUERY

	# INPUT READING STATUS QUERY

	# SETPOINT COMMAND

	# SETPOINT QUERY

	# TEMPERATURE LIMIT COMMAND

	# TEMPERATURE LIMIT QUERY

	