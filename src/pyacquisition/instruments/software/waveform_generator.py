from ...instruments._instrument import SoftInstrument, query, command
import time, enum
import numpy as np
from scipy.signal import square, sawtooth


class WaveformShape(enum.Enum):
	SINE = 0
	SQUARE = 1
	SAW = 2


class WaveformShapeModel(enum.Enum):
	SINE = 'Sine'
	SQUARE = 'Square'
	SAW = 'Sawtooth'



class WaveformGenerator(SoftInstrument):


	name = 'Waveform_Generator'


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self._t0 = time.time() + np.random.random()*10
		self._amplitude = 1.5
		self._frequency = 0.1
		self._shape = WaveformShape.SINE

		self._function = {
			0: lambda a, f, t: a * np.sin(t * 2 * np.pi * f),
			1: lambda a, f, t: a * square(t * 2 * np.pi * f, duty=0.5),
			2: lambda a, f, t: a * sawtooth(t * 2 * np.pi * f, width=0),
		}


	@property
	def metadata(self):
		metadata = super().metadata()
		metadata.update({
			"frequency": self.get_frequency(),
			"shape": self.get_shape(),
		})
		return metadata


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
		return self._shape


	@command
	def set_shape(self, shape: WaveformShape):
		self._shape = shape
		return 0


	@query
	def get_signal(self) -> float:
		t = time.time() - self._t0
		return float(self._function[self._shape.value](self._amplitude, self._frequency, t))


	def register_endpoints(self, app):
		super().register_endpoints(app)

		@app.get(f'/{self._uid}/'+'amplitude/get/', tags=[self._uid])
		def get_amplitude() -> float:
			return self.get_amplitude()

		@app.get(f'/{self._uid}/'+'amplitude/set/{value}', tags=[self._uid])
		def set_amplitude(value: float) -> int:
			return self.set_amplitude(value)

		@app.get(f'/{self._uid}/'+'frequency/get/', tags=[self._uid])
		def get_frequency() -> float:
			return self.get_frequency()

		@app.get(f'/{self._uid}/'+'frequency/set/{value}', tags=[self._uid])
		def set_frequency(value: float) -> int:
			return self.set_frequency(value)

		@app.get(f'/{self._uid}/'+'shape/get/', tags=[self._uid])
		def get_shape() -> WaveformShapeModel:
			return WaveformShapeModel[self.get_shape().name]

		@app.get(f'/{self._uid}/'+'shape/set/{value}', tags=[self._uid])
		def set_shape(value: WaveformShapeModel) -> int:
			return self.set_shape(WaveformShape[value.name])