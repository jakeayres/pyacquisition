from ...instruments._instrument import SoftInstrument, query, command
import time, enum
import numpy as np
from scipy.signal import square, sawtooth


class WaveformShape(enum.Enum):
	SINE = 0
	SQUARE = 1
	SAW = 2



class WaveformGenerator(SoftInstrument):


	name = 'Waveform_Generator'


	def __init__(self):
		super().__init__()

		self._t0 = time.time()
		self._amplitude = 1
		self._frequency = 1
		self._shape = 0

		self._function = {
			0: lambda a, f, t: a * np.sin(t * 2 * np.pi * f),
			1: lambda a, f, t: a * square(t * 2 * np.pi * f, duty=0.5),
			2: lambda a, f, t: a * sawtooth(t * 2 * np.pi * f, width=0),
		}


	@query
	def get_amplitude(self) -> float:
		return self._amplitude


	@command
	def set_amplitude(self, amplitude: float):
		self._amplitude = amplitude
		return 0


	@query
	def get_frequency(self) -> float:
		return self._frequency


	@command
	def set_frequency(self, frequency: float):
		self._frequency = frequency
		return 0


	@query
	def get_shape(self) -> WaveformShape:
		return WaveformShape(self._shape).name


	@command
	def set_shape(self, shape: WaveformShape):
		self._shape = shape.value


	@query
	def get_signal(self) -> float:
		t = time.time() - self._t0
		return float(self._function[self._shape](self._amplitude, self._frequency, t))