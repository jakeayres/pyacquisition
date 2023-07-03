from ...instruments._instrument import SoftInstrument, query, command
import time, enum
import numpy as np
from typing import Union, Tuple


class Direction(enum.Enum):
	UP = 0
	DOWN = 1
	LEFT = 2
	RIGHT = 3


class Channel(enum.Enum):
	OUTPUT_1 = 0
	OUTPUT_2 = 1


class PrimaryColor(enum.Enum):
	RED = 1
	GREEN = 2
	BLUE = 4


class Color(enum.Enum):
	RED = 2
	YELLOW = 3
	GREEN = 4
	CYAN = 6
	BLUE = 8
	MAGENTA = 5


class Gizmotron(SoftInstrument):


	def __init__(self):
		super().__init__()

		self._direction = Direction(0)
		self._random_outputs = [np.random.random, np.random.random]
		self._setpoint = 0
		self._setpoint_time = time.time()
		self._value = 0


	@query
	def get_integer(self) -> int:
		return int(np.random.random()*10)


	@query
	def get_float(self) -> float:
		return float(f'{np.random.random():.3f}')


	@query
	def get_two_integers(self) -> tuple[int, int]:
		return (int(np.random.random()*10), int(np.random.random()*10))


	@query
	def get_two_floats(self) -> tuple[float, float]:
		return (float(f'{np.random.random():.3f}'), float(f'{np.random.random():.3f}'))


	@query
	def get_direction(self) -> Direction:
		return Direction(self._direction)


	@query
	def get_random_output(self, channel: Channel) -> tuple[Channel, float]:
		return (channel, self._random_outputs[channel.value]())


	@query
	def get_color_addition(self, color_1: PrimaryColor, color_2: PrimaryColor) -> Color:
		return Color(PrimaryColor(color_1).value + PrimaryColor(color_2).value)


	@command
	def set_setpoint(self, value: float) -> None:
		self._setpoint = value
		self._setpoint_time = time.time()


	@query
	def get_value(self) -> float:
		t = time.time() - self._setpoint_time
		d = self._setpoint - self._value
		if d >= 0:
			self._value = min([self._value + t, self._setpoint])
			self._setpoint_time = time.time()
		else:
			self._value = max([self._value - t, self._setpoint])
			self._setpoint_time = time.time()
		return self._value