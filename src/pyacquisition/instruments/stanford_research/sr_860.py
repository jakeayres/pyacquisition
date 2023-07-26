import enum

from ...instruments._instrument import Instrument, query, command


class State(enum.Enum):
	OFF = 0
	ON = 1


class ReferenceSource(enum.Enum):
	INTERNAL = 0
	EXTERNAL = 1
	DUAL = 2
	CHOP = 3


class ReferenceSlope(enum.Enum):
	SINE = 0
	TTL_RISING = 1
	TTL_FALLING = 2


class InputMode(enum.Enum):
	VOLTAGE = 0
	CURRENT = 1


class InputConfiguration(enum.Enum):
	A = 0
	A_B = 1


class InputGrounding(enum.Enum):
	FLOAT = 0
	GROUND = 1


class InputCoupling(enum.Enum):
	AC = 0
	DC = 1


class InputVoltageRange(enum.Enum):
	V_1 = 0
	mV_300 = 1
	mV_100 = 2
	mV_30 = 3
	mV_10 = 4


class SyncFilter(enum.Enum):
	OFF = 0
	ON = 1


class AdvancedFilter(enum.Enum):
	OFF = 0
	ON = 1


class Sensitivity(enum.Enum):
	nV_1 = 27
	nV_2 = 26
	nV_5 = 25
	nV_10 = 24
	nV_20 = 23
	nV_50 = 22
	nV_100 = 21
	nV_200 = 20
	nV_500 = 19
	uV_1 = 18
	uV_2 = 17
	uV_5 = 16
	uV_10 = 15
	uV_20 = 14
	uV_50 = 13
	uV_100 = 12
	uV_200 = 11
	uV_500 = 10
	mV_1 = 9
	mV_2 = 8
	mV_5 = 7
	mV_10 = 6
	mV_20 = 5
	mV_50 = 4
	mV_100 = 3
	mV_200 = 2
	mV_500 = 1
	V_1 = 0


class TimeConstant(enum.Enum):
	us_1 = 0
	us_3 = 1
	us_10 = 2
	us_30 = 3
	us_100 = 4
	us_300 = 5
	ms_1 = 6
	ms_3 = 7
	ms_10 = 8
	ms_30 = 9
	ms_100 = 10
	ms_300 = 11
	s_1 = 12
	s_3 = 13
	s_10 = 14
	s_30 = 15
	s_100 = 16
	s_300 = 17
	ks_1 = 18
	ks_3 = 19
	ks_10 = 20
	ks_30 = 21


class FilterSlope(enum.Enum):
	db6 = 0
	db12 = 1
	db18 = 2
	db24 = 3



class SR_860(Instrument):

	name = 'SR_860'

	""" REFERENCE AND PHASE
	"""

	@query
	def identify(self):
		return self._query('*IDN?')


	@command
	def reset(self):
		return self._command('*RST')


	@command
	def clear(self):
		return self._command('*CLS')


	@query
	def get_phase(self) -> float:
		return float(self._query("PHAS?"))


	@command
	def set_phase(self, phase: float):
		return self._command(f'PHAS {phase:.2f}')


	@query
	def get_reference_source(self) -> ReferenceSource:
		return ReferenceSource(int(self._query(f'RSRC?')))


	@command
	def set_reference_source(self, source: ReferenceSource):
		return self._command(f'RSRC {source.value}')


	@query
	def get_frequency(self) -> float:
		return float(self._query("FREQ?"))


	@command
	def set_frequency(self, frequency: float):
		return self._command(f'FREQ {frequency:.3f}')


	@query
	def get_internal_frequency(self) -> float:
		return float(self._query("FREQINT?"))


	@command
	def set_internal_frequency(self, frequency: float):
		return self._command(f'FREQINT {frequency:.3f}')


	@query
	def get_external_referece_slope(self) -> ReferenceSlope:
		return ReferenceSlope(int(self._query(f'RSLP?')))


	@command
	def set_external_reference_slope(self, slope: ReferenceSlope):
		return self._command(f'RSLP {slope.value}')


	@query
	def get_harmonic(self) -> int:
		return int(self._query(f'HARM?'))


	@command
	def set_harmonic(self, harmonic: int):
		return self._command(f'HARM {harmonic}')


	@query
	def get_reference_amplitude(self) -> float:
		return float(self._query(f'SLVL?'))


	@command
	def set_reference_amplitude(self, amplitude: float):
		return self._command(f'SLVL {amplitude:.3f}')


	@query
	def get_reference_offset(self) -> float:
		return float(self._query(f'SOFF?'))


	@command
	def set_reference_offset(self, amplitude: float):
		return self._command(f'SOFF {amplitude:.3f}')


	""" INPUT AND FILTER
	"""

	@query
	def get_input_mode(self) -> InputMode:
		return InputMode(int(self._query(f'IVMD?')))


	@command
	def set_input_mode(self, mode: InputMode):
		return self._command(f'IVMD {mode.value}')


	@query
	def get_input_configuration(self) -> InputConfiguration:
		return InputConfiguration(int(self._query(f'ISRC?')))


	@command
	def set_input_configuration(self, configuration: InputConfiguration):
		return self._command(f'ISRC {configuration.value}')


	@query
	def get_input_coupling(self) -> InputCoupling:
		return InputCoupling(int(self._query(f'ICPL?')))


	@command
	def set_input_coupling(self, coupling: InputCoupling):
		return self._command(f'ICPL {coupling.value}')


	@query
	def get_input_grounding(self) -> InputGrounding:
		return InputGrounding(int(self._query(f'IGND?')))


	@command
	def set_input_grounding(self, grounding: InputGrounding):
		return self._command(f'IGND {grounding.value}')


	@query
	def get_input_voltage_range(self) -> InputVoltageRange:
		return InputVoltageRange(int(self._query(f'IRNG?')))


	@command
	def set_input_voltage_range(self, input_range: InputVoltageRange):
		return self._command(f'IRNG {input_range.value}')


	# @query
	# def get_current_input_gain()


	# @command
	# def set_current_input_gain()


	@query
	def get_sync_filter(self) -> SyncFilter:
		return SyncFilter(int(self._query(f'SYNC?')))


	@command
	def set_sync_filter(self, configuration: SyncFilter):
		return self._command(f'SYNC {configuration.value}')


	@query
	def get_advanced_filter(self) -> AdvancedFilter:
		return AdvancedFilter(int(self._query(f'ADVFILT?')))


	@command
	def set_advanced_filter(self, configuration: AdvancedFilter):
		return self._command(f'ADVFILT {configuration.value}')


	""" GAIN AND TIME CONSTANT
	"""

	# @query
	# get_signal_strength_indicator
	

	@query
	def get_sensitivity(self) -> Sensitivity:
		return Sensitivity(int(self._query(f'SCAL?')))


	@command
	def set_sensitivity(self, sensitivity: Sensitivity):
		return self._command(f'SCAL {sensitivity.value}')


	@query 
	def get_time_constant(self) -> TimeConstant:
		return TimeConstant(int(self._query(f'OFLT?')))


	@command
	def set_time_constant(self, time_constant: TimeConstant):
		return self._command(f'OFLT {time_constant.value}')


	@query
	def get_filter_slope(self) -> FilterSlope:
		return FilterSlope(int(self._query(f'OFSL?')))


	@command
	def set_filter_slope(self, filter_slope: FilterSlope):
		return self._command(f'OFSL {filter_slope.value}')


	""" DISPLAY AND OUTPUT
	"""

	""" AUX INPUT/OUTPUT
	"""

	""" SETUP
	"""

	""" AUTOFUNCTIONS
	"""

	""" DATA STORAGE
	"""

	""" DATA TRANSFER
	"""

	@query
	def get_output(self, parameter: int) -> float:
		return float(self._query(f'OUTP? {parameter}'))


	@query
	def get_display_output(self, parameter: int) -> float:
		return float(self._query(f'OUTR? {parameter}'))


	@query
	def get_x(self) -> float:
		return float(self._query(f'OUTP? 0'))


	@query
	def get_y(self) -> float:
		return float(self._query(f'OUTP? 1'))


	@query
	def get_xy(self) -> list[float]:
		return [float(s) for s in self._query(f'SNAP? 0,1').split(',')]



	""" INTERFACE
	"""

	""" STATUS
	"""


	def register_endpoints(self, app):

		@app.get(f'/{self._uid}/'+'frequency/set/{freq}', tags=[self._uid])
		def set_frequency(freq: float) -> 0:
			self.set_frequency(freq)
			return 0

