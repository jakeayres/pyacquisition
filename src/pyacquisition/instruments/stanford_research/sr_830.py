from enum import Enum

from ...core.instrument import Instrument, mark_query, mark_command


class SyncFilterState(Enum):
	OFF = 0
	ON = 1

class SyncFilterStateModel(Enum):
	OFF = 'Off'
	ON = 'On'


class ReferenceSource(Enum):
	INTERNAL = 0
	EXTERNAL = 1

class ReferenceSourceModel(Enum):
	INTERNAL = 'Internal'
	EXTERNAL = 'External'


class ReferenceSlope(Enum):
	SINE = 0
	TTL_RISING = 1
	TTL_FALLING = 2

class ReferenceSlopeModel(Enum):
	SINE = 'Sine'
	TTL_RISING = 'TTL Rising'
	TTL_FALLING = 'TTL Falling'


class InputConfiguration(Enum):
	A = 0
	A_B = 1
	I_10e6 = 2
	I_100e6 = 3

class InputConfigurationModel(Enum):
	A = 'A'
	A_B = 'A-B'
	I_10e6 = 'Current 10uA'
	I_100e6 = 'Curretn 100uA'


class InputGrounding(Enum):
	FLOAT = 0
	GROUND = 1

class InputGroundingModel(Enum):
	FLOAT = 'Float'
	GROUND = 'Ground'


class InputCoupling(Enum):
	AC = 0
	DC = 1

class InputCouplingModel(Enum):
	AC = 'AC'
	DC = 'DC'


class NotchFilters(Enum):
	NONE = 0
	LINE_1 = 1
	LINE_2 = 2
	BOTH = 3

class NotchFiltersModel(Enum):
	NONE = 'None'
	LINE_1 = 'Line'
	LINE_2 = 'Line x2'
	BOTH = 'Both'


class Sensitivity(Enum):
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

class SensitivityModel(Enum):
	nV_2 = '2 nV'
	nV_5 = '5 nV'
	nV_10 = '10 nV'
	nV_20 = '20 nV'
	nV_50 = '50 nV'
	nV_100 = '100 nV'
	nV_200 = '200 nV'
	nV_500 = '500 nV'
	uV_1 = '1 uV'
	uV_2 = '2 uV'
	uV_5 = '5 uV'
	uV_10 = '10 uV'
	uV_20 = '20 uV'
	uV_50 = '50 uV'
	uV_100 = '100 uV'
	uV_200 = '200 uV'
	uV_500 = '500 uV'
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
	us_10 = 0
	us_30 = 1
	us_100 = 2
	us_300 = 3
	ms_1 = 4
	ms_3 = 5
	ms_10 = 6
	ms_30 = 7
	ms_100 = 8
	ms_300 = 9
	s_1 = 10
	s_3 = 11
	s_10 = 12
	s_30 = 13
	s_100 = 14
	s_300 = 15
	ks_1 = 16
	ks_3 = 17
	ks_10 = 18
	ks_30 = 19


class TimeConstantModel(Enum):
	us_10 = '10 µs'
	us_30 = '30 µs'
	us_100 = '100 µs'
	us_300 = '300 µs'
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


class DynamicReserve(Enum):
	HIGH_RESERVE = 0
	NORMAL = 1
	LOW_NOISE = 2

class DynamicReserveModel(Enum):
	HIGH_RESERVE = 'High Reserve'
	NORMAL = 'Normal'
	LOW_NOISE = 'Low Noise'



class SR_830(Instrument):

	name = 'SR_830'

	""" REFERENCE AND PHASE
	"""


	@mark_query
	def identify(self):
		return self.query('*IDN?')


	@mark_command
	def reset(self):
		return self.command('*RST')


	@mark_command
	def reset_data_buffer(self):
		return self.command('*REST')


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
		return ReferenceSource(int(self.query(f'FMOD?')))


	@mark_command
	def set_reference_source(self, source: ReferenceSource):
		return self.command(f'FMOD {source.value}')


	@mark_query
	def get_frequency(self) -> float:
		return float(self.query("FREQ?"))


	@mark_command
	def set_frequency(self, frequency: float):
		return self.command(f'FREQ {frequency:.3f}')


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


	""" INPUT AND FILTER
	"""

	@mark_query
	def get_input_configuration(self) -> InputConfiguration:
		return InputConfiguration(int(self.query(f'ISRC?')))


	@mark_command
	def set_input_configuration(self, configuration: InputConfiguration):
		return self.command(f'ISRC {configuration.value}')


	@mark_query
	def get_input_grounding(self) -> InputGrounding:
		return InputGrounding(int(self.query(f'IGND?')))


	@mark_command
	def set_input_grounding(self, configuration: InputGrounding):
		return self.command(f'IGND {configuration.value}')


	@mark_query
	def get_input_coupling(self) -> InputCoupling:
		return InputCoupling(int(self.query(f'ICPL?')))


	@mark_command
	def set_input_coupling(self, configuration: InputCoupling):
		return self.command(f'ICPL {configuration.value}')


	@mark_query
	def get_notch_filters(self) -> NotchFilters:
		return NotchFilters(int(self.query(f'ILIN?')))


	@mark_command
	def set_notch_filters(self, configuration: NotchFilters):
		return self.command(f'ILIN {configuration.value}')

	""" GAIN AND TIME CONSTANT
	"""

	@mark_query
	def get_sensitivity(self) -> Sensitivity:
		return Sensitivity(int(self.query(f'SENS?')))


	@mark_command
	def set_sensitivity(self, sensitivity: Sensitivity):
		return self.command(f'SENS {sensitivity.value}')


	@mark_query
	def get_dynamic_reserve(self) -> DynamicReserve:
		return DynamicReserve(int(self.query(f'RMOD?')))


	@mark_command
	def set_dynamic_reserve(self, reserve: DynamicReserve):
		return self.command(f'RMOD {reserve.value}')


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


	@mark_query
	def get_sync_filter_state(self) -> SyncFilterState:
		return SyncFilterState(int(self.query(f'SYNC?')))


	@mark_command
	def set_sync_filter_state(self, state: SyncFilterState):
		return self.command(f'SYNC {state.value}')


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
		return float(self.query(f'OUTP? 1'))


	@mark_query
	def get_y(self) -> float:
		return float(self.query(f'OUTP? 2'))


	@mark_query
	def get_xy(self) -> list[float]:
		return [float(s) for s in self.query(f'SNAP? 1,2').split(',')]


	@mark_query
	def get_display_buffer_length(self) -> int:
		return int(self.query(f'SPTS?'))


	""" INTERFACE
	"""

	""" STATUS
	"""


	def register_endpoints(self, api_server):
		super().register_endpoints(api_server)

		@api_server.app.get(f'/{self._uid}/'+'phase/get', tags=[self._uid])
		async def get_phase() -> float:
			return self.get_phase()
		
		@api_server.app.get(f'/{self._uid}/'+'phase/set/', tags=[self._uid])
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


		@api_server.app.get(f'/{self._uid}/'+'dynamic_reserve/get', tags=[self._uid])
		async def get_dynamic_reserve() -> DynamicReserveModel:
			return DynamicReserveModel[self.get_dynamic_reserve().name]
		
		@api_server.app.get(f'/{self._uid}/'+'dynamic_reserve/set/', tags=[self._uid])
		async def set_dynamic_reserve(reserve: DynamicReserveModel) -> int:
			self.set_dynamic_reserve(DynamicReserve[reserve.name])
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