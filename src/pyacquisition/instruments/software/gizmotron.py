from ...instruments._instrument import SoftInstrument, query, command
import time, enum
import numpy as np
from typing import Union, Tuple, get_type_hints


class Direction(enum.Enum):
	UP = 0
	DOWN = 1
	LEFT = 2
	RIGHT = 3


class DirectionModel(enum.Enum):
	UP = 'Up'
	DOWN = 'Down'
	LEFT = 'Left'
	RIGHT = 'Right'


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


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self._direction = Direction(0)
		self._random_outputs = [np.random.random, np.random.random]
		self._setpoint = 0
		self._setpoint_time = time.time()
		self._value = 0


	@property
	def metadata(self):
		metadata = super().metadata
		metadata.update({
			"direction": self.get_direction(),
			"setpoint": self.get_setpoint(),
		})
		return metadata


	@query
	def get_integer() -> int:
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
	def get_setpoint(self) -> float:
		return self._setpoint


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


	@query
	def get_various_types(self) -> tuple[Direction, float, str, int]:
		return (self.get_direction(), self.get_float(), 'a string', 1)


	def register_endpoints(self, app):
		super().register_endpoints(app)


		@app.get(f'/{self._uid}/'+'setpoint/set/{value}', tags=[self._uid])
		def set_setpoint(value: float) -> float:
			self.set_setpoint(value)
			return self.get_setpoint()


		@app.get(f'/{self._uid}/'+'setpoint/get/', tags=[self._uid])
		def get_setpoint() -> float:
			return self.get_setpoint()


		@app.get(f'/{self._uid}/'+'value/get/', tags=[self._uid])
		def get_value() -> float:
			return self.get_value()


		@app.get(f'/{self._uid}/'+'two_integers/get/', tags=[self._uid])
		def get_two_integers() -> tuple[int, int]:
			return self.get_two_integers()


		@app.get(f'/{self._uid}/'+'two_floats/get/', tags=[self._uid])
		def get_two_floats() -> tuple[float, float]:
			return self.get_two_floats()


		@app.get(f'/{self._uid}/'+'various_types/get/', tags=[self._uid])
		def get_various_types() -> tuple[DirectionModel, float, str, int]:
			return (
				DirectionModel[self.get_various_types()[0].name],
				self.get_various_types()[1],
				self.get_various_types()[2],
				self.get_various_types()[3],
			)