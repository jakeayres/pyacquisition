import enum

from ...instruments._instrument import Instrument, query, command


class ReferenceSource(enum.Enum):
	INTERNAL = 0
	EXTERNAL = 1


class ReferenceSlope(enum.Enum):
	SINE = 0
	TTL_RISING = 1
	TTL_FALLING = 2


class InputConfiguration(enum.Enum):
	A = 0
	A_B = 1
	I_10e6 = 2
	I_100e6 = 3


class InputGrounding(enum.Enum):
	FLOAT = 0
	GROUND = 1


class InputCoupling(enum.Enum):
	AC = 0
	DC = 1


class NotchFilters(enum.Enum):
	NONE = 0
	LINE_1 = 1
	LINE_2 = 2
	BOTH = 3


class Sensitivity(enum.Enum):
	nV_2 = 0
	nV_5 = 1
	nV_10 = 2
	nV_20 = 3
	nV_50 = 4
	nV_100 = 5
	nV_200 = 6
	nV_500 = 7
	uV_1 = 8
	uV_2 = 9
	uV_5 = 10
	uV_10 = 11
	uV_20 = 12
	uV_50 = 13
	uV_100 = 14
	uV_200 = 15
	uV_500 = 16
	mV_1 = 17
	mV_2 = 18
	mV_5 = 19
	mV_10 = 20
	mV_20 = 21
	mV_50 = 22
	mV_100 = 23
	mV_200 = 24
	mV_500 = 25
	V_1 = 26


class DynamicReserve(enum.Enum):
	HIGH_RESERVE = 0
	NORMAL = 1
	LOW_NOISE = 2



class SR_830(Instrument):

	name = 'SR_830'

	""" REFERENCE AND PHASE
	"""

	@query
	def get_phase(self) -> float:
		return float(self._query("PHAS?"))


	@command
	def set_phase(self, phase: float):
		return self._command(f'PHAS {phase:.2f}')


	@query
	def get_reference_source(self) -> ReferenceSource:
		return ReferenceSource(int(self._query(f'FMOD?'))).name


	@command
	def set_reference_source(self, source: ReferenceSource):
		return self._command(f'FMOD {source.value}')


	@query
	def get_frequency(self) -> float:
		return float(self._query("FREQ?"))


	@command
	def set_frequency(self, frequency: float):
		return self._command(f'FREQ {frequency:.2f}')


	@query
	def get_external_referece_slope(self) -> ReferenceSlope:
		return ReferenceSlope(int(self._query(f'RSLP?'))).name


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


	""" INPUT AND FILTER
	"""

	@query
	def get_input_configuration(self) -> InputConfiguration:
		return InputConfiguration(int(self._query(f'ISRC?'))).name


	@command
	def set_input_configuration(self, configuration: InputConfiguration):
		return self._command(f'ISRC {configuration.value}')


	@query
	def get_input_grounding(self) -> InputGrounding:
		return InputGrounding(int(self._query(f'IGND?'))).name


	@command
	def set_input_grounding(self, configuration: InputGrounding):
		return self._command(f'IGND {configuration.value}')


	@query
	def get_input_coupling(self) -> InputCoupling:
		return InputCoupling(int(self._query(f'ICPL?'))).name


	@command
	def set_input_coupling(self, configuration: InputCoupling):
		return self._command(f'ICPL {configuration.value}')


	@query
	def get_notch_filters(self) -> NotchFilters:
		return NotchFilters(int(self._query(f'ILIN?')))


	@command
	def set_notch_filters(self, configuration: NotchFilters):
		return self._command(f'ILIN {configuration.value}')

	""" GAIN AND TIME CONSTANT
	"""

	@query
	def get_sensitivity(self) -> Sensitivity:
		return Sensitivity(int(self._query(f'SENS?'))).name


	@command
	def set_sensitivity(self, sensitivity: Sensitivity):
		return self._command(f'SENS {sensitivity.value}')


	@query
	def get_dynamic_reserve(self) -> DynamicReserve:
		return DynamicReserve(int(self._query(f'RMOD?'))).name


	@command
	def set_dynamic_reserve(self, reserve: DynamicReserve):
		return self._command(f'RMOD {reserve.value}')


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

	# @query
	# def get_output(self, parameter: int):
	# 	return self._query(f'OUTP? {parameter}')


	# @query
	# def get_display_output(self, parameter: int):
	# 	return self._query(f'OUTR? {parameter}')


	@query
	def get_voltage(self) -> list[float]:
		return [float(s) for s in self._query(f'SNAP? 1,2').split(',')]


	@query
	def get_display_buffer_length(self) -> int:
		return int(self._query(f'SPTS?'))


	""" INTERFACE
	"""

	""" STATUS
	"""


