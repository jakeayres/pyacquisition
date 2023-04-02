import enum
from typing import Union

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
	CUSTOM = 4
	FOUR_LOOP = 5
	ALL_INPUTS = 6
	INPUT_D2 = 7
	INPUT_D3 = 8
	INPUT_D4 = 9
	INPUT_D5 = 10


class DisplayCustomNumber(enum.Enum):
	_IGNORE = ''
	LARGE_2 = 0
	LARGE_4 = 1
	SMALL_8 = 2


class DisplayAllInputsSize(enum.Enum):
	_IGNORE = ''
	SMALL = 0
	LARGE = 1


class DisplayCustomOutput(enum.Enum):
	_IGNORE = ''
	OUTPUT_1 = 1
	OUTPUT_2 = 2
	OUTPUT_3 = 3
	OUTPUT_4 = 4



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
	def set_display_setup(self, 
		mode: DisplayMode, 
		number: Union[DisplayCustomNumber,DisplayAllInputsSize] = DisplayCustomNumber._IGNORE,
		output_source: DisplayCustomOutput = DisplayCustomNumber._IGNORE,
		):
		return self._command(f'DISPLAY {mode.value},{number.value},{output_source.value}')




