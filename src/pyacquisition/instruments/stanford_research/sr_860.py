from enum import Enum
from pydantic import BaseModel

from ...core.instrument import Instrument, mark_query, mark_command


class ReferenceSource(Enum):
	INTERNAL = 0
	EXTERNAL = 1
	DUAL = 2
	CHOP = 3


class ReferenceSourceModel(Enum):
	INTERNAL = 'Internal'
	EXTERNAL = 'External'
	DUAL = 'Dual'
	CHOP = 'Chopped'


class ReferenceSlope(Enum):
	SINE = 0
	TTL_RISING = 1
	TTL_FALLING = 2


class ReferenceSlopeModel(Enum):
	SINE = 'Sine'
	TTL_RISING = 'TTL Rising'
	TTL_FALLING = 'TLL Falling'


class InputMode(Enum):
	VOLTAGE = 0
	CURRENT = 1


class InputModeModel(Enum):
	VOLTAGE = 'Voltage'
	CURRENT = 'Current'


class InputConfiguration(Enum):
	A = 0
	A_B = 1


class InputConfigurationModel(Enum):
	A = 'A'
	A_B = 'A-B'


class InputGrounding(Enum):
	FLOAT = 0
	GROUND = 1


class InputGroundingModel(Enum):
	FLOAT = 'Floating'
	GROUND = 'Grounded'


class InputCoupling(Enum):
	AC = 0
	DC = 1


class InputCouplingModel(Enum):
	AC = 'AC'
	DC = 'DC'


class InputVoltageRange(Enum):
	V_1 = 0
	mV_300 = 1
	mV_100 = 2
	mV_30 = 3
	mV_10 = 4


class InputVoltageRangeModel(Enum):
	V_1 = '1 V'
	mV_300 = '300 mV'
	mV_100 = '100 mV'
	mV_30 = '30 mV'
	mV_10 = '10 mV'


class SyncFilter(Enum):
	OFF = 0
	ON = 1


class SyncFilterModel(Enum):
	OFF = 'Off'
	ON = 'On'


class AdvancedFilter(Enum):
	OFF = 0
	ON = 1


class AdvancedFilterModel(Enum):
	OFF = 'Off'
	ON = 'On'


class Sensitivity(Enum):
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


class SensitivityModel(Enum):
	nV_1 = '1 nV'
	nV_2 = '2 nV'
	nV_5 = '5 nV'
	nV_10 = '10 nV'
	nV_20 = '20 nV'
	nV_50 = '50 nV'
	nV_100 = '100 nV'
	nV_200 = '200 nV'
	nV_500 = '500 nV'
	uV_1 = '1 µV'
	uV_2 = '2 µV'
	uV_5 = '5 µV'
	uV_10 = '10 µV'
	uV_20 = '20 µV'
	uV_50 = '50 µV'
	uV_100 = '100 µV'
	uV_200 = '200 µV'
	uV_500 = '500 µV'
	mV_1 = '1 mV'
	mV_2 = '2 mV'
	mV_5 = '5 mV'
	mV_10 = '10 mV'
	mV_20 = '20 mV'
	mV_50 = '50 mV'
	mV_100 = '100 mV'
	mV_200 = '200 mV'
	mV_500 = '500 mV'
	V_1 = '1 V'


class TimeConstant(Enum):
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


class TimeConstantModel(Enum):
	us_1 = '1 us'
	us_3 = '3 us'
	us_10 = '10 us'
	us_30 = '30 us'
	us_100 = '100 us'
	us_300 = '300 us'
	ms_1 = '1 ms'
	ms_3 = '3 ms'
	ms_10 = '10 ms'
	ms_30 = '30 ms'
	ms_100 = '100 ms'
	ms_300 = '300 ms'
	s_1 = '1 s'
	s_3 = '3 s'
	s_10 = '10 s'
	s_30 = '30 s'
	s_100 = '100 s'
	s_300 = '300 s'
	ks_1 = '1 ks'
	ks_3 = '3 ks'
	ks_10 = '10 ks'
	ks_30 = '30 ks'


class FilterSlope(Enum):
	db6 = 0
	db12 = 1
	db18 = 2
	db24 = 3


class FilterSlopeModel(Enum):
	db6 = '6 db'
	db12 = '12 db'
	db18 = '18 db'
	db24 = '24 db'



class SR_860(Instrument):

	name = 'SR_860'


	""" REFERENCE AND PHASE
	"""

	@mark_query
	def identify(self):
		return self.query('*IDN?')


	@mark_command
	def reset(self):
		return self.command('*RST')


	@mark_command
	def clear(self):
		return self.command('*CLS')


	@mark_query
	def get_phase(self) -> float:
		return float(self.query("PHAS?"))


	@mark_command
	def set_phase(self, phase: float):
		return self.command(f'PHAS {phase:.2f}')


	@mark_query
	def get_reference_source(self) -> ReferenceSource:
		return ReferenceSource(int(self.query(f'RSRC?')))


	@mark_command
	def set_reference_source(self, source: ReferenceSource):
		return self.command(f'RSRC {source.value}')


	@mark_query
	def get_frequency(self) -> float:
		return float(self.query("FREQ?"))


	@mark_command
	def set_frequency(self, frequency: float):
		return self.command(f'FREQ {frequency:.3f}')


	@mark_query
	def get_internal_frequency(self) -> float:
		return float(self.query("FREQINT?"))


	@mark_command
	def set_internal_frequency(self, frequency: float):
		return self.command(f'FREQINT {frequency:.3f}')


	@mark_query
	def get_external_reference_slope(self) -> ReferenceSlope:
		return ReferenceSlope(int(self.query(f'RSLP?')))


	@mark_command
	def set_external_reference_slope(self, slope: ReferenceSlope):
		return self.command(f'RSLP {slope.value}')


	@mark_query
	def get_harmonic(self) -> int:
		return int(self.query(f'HARM?'))


	@mark_command
	def set_harmonic(self, harmonic: int):
		return self.command(f'HARM {harmonic}')


	@mark_query
	def get_reference_amplitude(self) -> float:
		return float(self.query(f'SLVL?'))


	@mark_command
	def set_reference_amplitude(self, amplitude: float):
		return self.command(f'SLVL {amplitude:.3f}')


	@mark_query
	def get_reference_offset(self) -> float:
		return float(self.query(f'SOFF?'))


	@mark_command
	def set_reference_offset(self, amplitude: float):
		return self.command(f'SOFF {amplitude:.3f}')


	""" INPUT AND FILTER
	"""

	@mark_query
	def get_input_mode(self) -> InputMode:
		return InputMode(int(self.query(f'IVMD?')))


	@mark_command
	def set_input_mode(self, mode: InputMode):
		return self.command(f'IVMD {mode.value}')


	@mark_query
	def get_input_configuration(self) -> InputConfiguration:
		return InputConfiguration(int(self.query(f'ISRC?')))


	@mark_command
	def set_input_configuration(self, configuration: InputConfiguration):
		return self.command(f'ISRC {configuration.value}')


	@mark_query
	def get_input_coupling(self) -> InputCoupling:
		return InputCoupling(int(self.query(f'ICPL?')))


	@mark_command
	def set_input_coupling(self, coupling: InputCoupling):
		return self.command(f'ICPL {coupling.value}')


	@mark_query
	def get_input_grounding(self) -> InputGrounding:
		return InputGrounding(int(self.query(f'IGND?')))


	@mark_command
	def set_input_grounding(self, grounding: InputGrounding):
		print(grounding)
		return self.command(f'IGND {grounding.value}')


	@mark_query
	def get_input_voltage_range(self) -> InputVoltageRange:
		return InputVoltageRange(int(self.query(f'IRNG?')))


	@mark_command
	def set_input_voltage_range(self, input_range: InputVoltageRange):
		return self.command(f'IRNG {input_range.value}')


	# @mark_query
	# def get_current_input_gain()


	# @mark_command
	# def set_current_input_gain()


	@mark_query
	def get_sync_filter(self) -> SyncFilter:
		return SyncFilter(int(self.query(f'SYNC?')))


	@mark_command
	def set_sync_filter(self, configuration: SyncFilter):
		return self.command(f'SYNC {configuration.value}')


	@mark_query
	def get_advanced_filter(self) -> AdvancedFilter:
		return AdvancedFilter(int(self.query(f'ADVFILT?')))


	@mark_command
	def set_advanced_filter(self, configuration: AdvancedFilter):
		return self.command(f'ADVFILT {configuration.value}')


	""" GAIN AND TIME CONSTANT
	"""

	# @mark_query
	# get_signal_strength_indicator
	

	@mark_query
	def get_sensitivity(self) -> Sensitivity:
		return Sensitivity(int(self.query(f'SCAL?')))


	@mark_command
	def set_sensitivity(self, sensitivity: Sensitivity):
		return self.command(f'SCAL {sensitivity.value}')


	@mark_query 
	def get_time_constant(self) -> TimeConstant:
		return TimeConstant(int(self.query(f'OFLT?')))


	@mark_command
	def set_time_constant(self, time_constant: TimeConstant):
		return self.command(f'OFLT {time_constant.value}')


	@mark_query
	def get_filter_slope(self) -> FilterSlope:
		return FilterSlope(int(self.query(f'OFSL?')))


	@mark_command
	def set_filter_slope(self, filter_slope: FilterSlope):
		return self.command(f'OFSL {filter_slope.value}')


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

	@mark_query
	def get_output(self, parameter: int) -> float:
		return float(self.query(f'OUTP? {parameter}'))


	@mark_query
	def get_display_output(self, parameter: int) -> float:
		return float(self.query(f'OUTR? {parameter}'))


	@mark_query
	def get_x(self) -> float:
		return float(self.query(f'OUTP? 0'))


	@mark_query
	def get_y(self) -> float:
		return float(self.query(f'OUTP? 1'))


	@mark_query
	def get_r(self) -> float:
		return float(self.query(f'OUTP? 2'))


	@mark_query
	def get_theta(self) -> float:
		return float(self.query(f'OUTP? 3'))



	@mark_query
	def get_xy(self) -> list[float]:
		return [float(s) for s in self.query(f'SNAP? 0,1').split(',')]



	""" INTERFACE
	"""

	""" STATUS
	"""


	def register_endpoints(self, api_server) -> None:
		super().register_endpoints(api_server)

		@api_server.app.get(f'/{self._uid}/'+'phase/get', tags=[self._uid])
		async def get_phase() -> float:
			return self.get_phase()
		
		@api_server.app.get(f'/{self._uid}/'+'phase/set/{phase}', tags=[self._uid])
		async def set_phase(phase: float) -> int:
			self.set_phase(phase)
			return 0
		
		@api_server.app.get(f'/{self._uid}/'+'reference_source/get', tags=[self._uid])
		async def get_reference_source() -> ReferenceSourceModel:
			return ReferenceSourceModel[self.get_reference_source().name]
		
		@api_server.app.get(f'/{self._uid}/'+'reference_source/set/', tags=[self._uid])
		async def set_reference_source(source: ReferenceSourceModel) -> int:
			self.set_reference_source(ReferenceSource[source.name])
			return 0
		
		@api_server.app.get(f'/{self._uid}/'+'frequency/get', tags=[self._uid])
		async def get_frequency() -> float:
			return self.get_frequency()
		
		@api_server.app.get(f'/{self._uid}/'+'frequency/set/', tags=[self._uid])
		async def set_frequency(frequency: float) -> int:
			self.set_frequency(frequency)
			return 0

		@api_server.app.get(f'/{self._uid}/'+'external_reference_slope/get', tags=[self._uid])
		async def get_external_reference_slope() -> ReferenceSlopeModel:
			return ReferenceSlopeModel[self.get_external_reference_slope().name]
		
		@api_server.app.get(f'/{self._uid}/'+'external_reference_slope/set/', tags=[self._uid])
		async def set_external_reference_slope(slope: ReferenceSlopeModel) -> int:
			self.set_external_reference_slope(ReferenceSlope[slope.name])
			return 0

		@api_server.app.get(f'/{self._uid}/'+'harmonic/get', tags=[self._uid])
		async def get_harmonic() -> int:
			return self.get_harmonic()
		
		@api_server.app.get(f'/{self._uid}/'+'harmonic/set/', tags=[self._uid])
		async def set_harmonic(harmonic: int) -> int:
			self.set_harmonic(harmonic)
			return 0

		@api_server.app.get(f'/{self._uid}/'+'reference_amplitude/get', tags=[self._uid])
		async def get_reference_amplitude() -> float:
			return self.get_reference_amplitude()
		
		@api_server.app.get(f'/{self._uid}/'+'reference_amplitude/set/', tags=[self._uid])
		async def set_reference_amplitude(reference_amplitude: float) -> int:
			self.set_reference_amplitude(reference_amplitude)
			return 0

		@api_server.app.get(f'/{self._uid}/'+'reference_offset/get', tags=[self._uid])
		async def get_reference_offset() -> float:
			return self.get_reference_offset()
		
		@api_server.app.get(f'/{self._uid}/'+'reference_offset/set/', tags=[self._uid])
		async def set_reference_offset(reference_offset: float) -> int:
			self.set_reference_offset(reference_offset)
			return 0

		@api_server.app.get(f'/{self._uid}/'+'input_mode/get', tags=[self._uid])
		async def get_input_mode() -> InputModeModel:
			return InputModeModel[self.get_input_mode().name]
		
		@api_server.app.get(f'/{self._uid}/'+'input_mode/set/', tags=[self._uid])
		async def set_input_mode(mode: InputModeModel) -> int:
			self.set_input_mode(InputMode[mode.name])
			return 0

		@api_server.app.get(f'/{self._uid}/'+'input_configuration/get', tags=[self._uid])
		async def get_input_configuration() -> InputConfigurationModel:
			return InputConfigurationModel[self.get_input_configuration().name]
		
		@api_server.app.get(f'/{self._uid}/'+'input_configuration/set/', tags=[self._uid])
		async def set_input_configuration(configuration: InputConfigurationModel) -> int:
			self.set_input_configuration(InputConfiguration[configuration.name])
			return 0

		@api_server.app.get(f'/{self._uid}/'+'input_coupling/get', tags=[self._uid])
		async def get_input_coupling() -> InputCouplingModel:
			return InputCouplingModel[self.get_input_coupling().name]
		
		@api_server.app.get(f'/{self._uid}/'+'input_coupling/set/', tags=[self._uid])
		async def set_input_coupling(coupling: InputCouplingModel) -> int:
			self.set_input_coupling(InputCoupling[coupling.name])
			return 0

		@api_server.app.get(f'/{self._uid}/'+'input_grounding/get', tags=[self._uid])
		async def get_input_grounding() -> InputGroundingModel:
			return InputGroundingModel[self.get_input_grounding().name]
		
		@api_server.app.get(f'/{self._uid}/'+'input_grounding/set/', tags=[self._uid])
		async def set_input_grounding(grounding: InputGroundingModel) -> int:
			self.set_input_grounding(InputGrounding[grounding.name])
			return 0

		@api_server.app.get(f'/{self._uid}/'+'input_voltage_range/get', tags=[self._uid])
		async def get_input_voltage_range() -> InputVoltageRangeModel:
			return InputVoltageRangeModel[self.get_input_voltage_range().name]
		
		@api_server.app.get(f'/{self._uid}/'+'input_voltage_range/set/', tags=[self._uid])
		async def set_input_voltage_range(voltage_range: InputVoltageRangeModel) -> int:
			self.set_input_voltage_range(InputVoltageRange[voltage_range.name])
			return 0

		@api_server.app.get(f'/{self._uid}/'+'sync_filter/get', tags=[self._uid])
		async def get_sync_filter() -> SyncFilterModel:
			return SyncFilterModel[self.get_sync_filter().name]
		
		@api_server.app.get(f'/{self._uid}/'+'sync_filter/set/', tags=[self._uid])
		async def set_sync_filter(sync_filter: SyncFilterModel) -> int:
			self.set_sync_filter(SyncFilter[sync_filter.name])
			return 0

		@api_server.app.get(f'/{self._uid}/'+'advanced_filter/get', tags=[self._uid])
		async def get_advanced_filter() -> AdvancedFilterModel:
			return AdvancedFilterModel[self.get_advanced_filter().name]
		
		@api_server.app.get(f'/{self._uid}/'+'advanced_filter/set/', tags=[self._uid])
		async def set_advanced_filter(advanced_filter: AdvancedFilterModel) -> int:
			self.set_advanced_filter(AdvancedFilter[advanced_filter.name])
			return 0

		@api_server.app.get(f'/{self._uid}/'+'sensitivity/get', tags=[self._uid])
		async def get_sensitivity() -> SensitivityModel:
			return SensitivityModel[self.get_sensitivity().name]
		
		@api_server.app.get(f'/{self._uid}/'+'sensitivity/set/', tags=[self._uid])
		async def set_sensitivity(sensitivity: SensitivityModel) -> int:
			self.set_sensitivity(Sensitivity[sensitivity.name])
			return 0

		@api_server.app.get(f'/{self._uid}/'+'time_constant/get', tags=[self._uid])
		async def get_time_constant() -> TimeConstantModel:
			return TimeConstantModel[self.get_time_constant().name]
		
		@api_server.app.get(f'/{self._uid}/'+'time_constant/set/', tags=[self._uid])
		async def set_time_constant(time_constant: TimeConstantModel) -> int:
			self.set_time_constant(TimeConstant[time_constant.name])
			return 0

		@api_server.app.get(f'/{self._uid}/'+'filter_slope/get', tags=[self._uid])
		async def get_filter_slope() -> FilterSlopeModel:
			return FilterSlopeModel[self.get_filter_slope().name]
		
		@api_server.app.get(f'/{self._uid}/'+'filter_slope/set/', tags=[self._uid])
		async def set_filter_slope(filter_slope: FilterSlopeModel) -> int:
			self.set_filter_slope(FilterSlope[filter_slope.name])
			return 0