from enum import Enum
from ...instruments._instrument import SoftInstrument, query, command
import time


class SystemStatusM(Enum):
	NORMAL = 0
	QUENCHED = 1
	OVERHEATED = 2
	WARMING_UP = 4
	FAULT = 8


class SystemStatusMModel(Enum):
	NORMAL = 'Normal'
	QUENCHED = 'Quenched'
	OVERHEATED = 'Overheaded'
	WARMING_UP = 'Warming up'
	FAULT = 'Fault'


class SystemStatusN(Enum):
	NORMAL = 0
	POSITIVE_VOLTAGE_LIMIT = 1
	NEGATIVE_VOLTAGE_LIMIT = 2
	NEGATIVE_CURRENT_LIMIT = 4
	POSITIVE_CURRENT_LIMIT = 8


class SystemStatusNModel(Enum):
	NORMAL = 'Normal'
	POSITIVE_VOLTAGE_LIMIT = 'On positive voltage limit'
	NEGATIVE_VOLTAGE_LIMIT = 'On negative voltage limit'
	NEGATIVE_CURRENT_LIMIT = 'Outside negative current limit'
	POSITIVE_CURRENT_LIMIT = 'Outside positive current limit'


class ActivityStatus(Enum):
	HOLD = 0
	TO_SETPOINT = 1
	TO_ZERO = 2
	CLAMPED = 4


class ActivityStatusModel(Enum):
	HOLD = 'Hold'
	TO_SETPOINT = 'To setpoint'
	TO_ZERO = 'To zero'
	CLAMPED = 'Clamped'


class RemoteStatus(Enum):
	LOCAL_LOCKED = 0
	REMOTE_LOCKED = 1
	LOCAL_UNLOCKED = 2
	REMOTE_UNLOCKED = 3


class RemoteStatusModel(Enum):
	LOCAL_LOCKED = 'Local and locked'
	REMOTE_LOCKED = 'Remote and locked'
	LOCAL_UNLOCKED = 'Local and unlocked'
	REMOTE_UNLOCKED = 'Remote and unlocked'


class SwitchHeaterStatus(Enum):
	OFF_AT_ZERO = 0
	ON = 1
	OFF_AT_FIELD = 2
	FAULT = 3
	NOT_FITTED = 4


class SwitchHeaterStatusModel(Enum):
	OFF_AT_ZERO = 'Off (closed) at zero field'
	ON = 'On (open)'
	OFF_AT_FIELD = 'Off (closed) at field'
	FAULT = 'Fault'
	NOT_FITTED = 'Not fitted'


class ModeStatusM(Enum):
	FAST_AMPS = 0
	FAST_TESLA = 1
	SLOW_AMPS = 4
	SLOW_TESLA = 5


class ModeStatusMModel(Enum):
	FAST_AMPS = 'Fast sweep (amps)'
	FAST_TESLA = 'Fast sweep (tesla)'
	SLOW_AMPS = 'Slow sweep (amps)'
	SLOW_TESLA = 'Slow sweep (tesla)'


class ModeStatusN(Enum):
	REST = 0
	SWEEPING = 1
	LIMITING = 2
	SWEEPING_LIMITING = 3


class ModeStatusNModel(Enum):
	REST = 'At rest (constant output)'
	SWEEPING = 'Sweeping'
	LIMITING = 'Sweep limiting'
	SWEEPING_LIMITING = 'Sweeping and sweep limiting'


class FakeMagnetPSU(SoftInstrument):


	def __init__(self, uid, **kwargs):
		self._uid = uid
		self._field = 0
		self._setpoint = 0
		self._ramp_rate = 0.5
		self._amps_per_tesla = 2
		self._persistant_field = 0

		self._system_status_m = SystemStatusM.NORMAL
		self._system_status_n = SystemStatusN.NORMAL
		self._activity_status = ActivityStatus.HOLD
		self._switch_heater_status = SwitchHeaterStatus.OFF_AT_ZERO
		self._sweep_mode_status = ModeStatusM.SLOW_TESLA
		self._sweep_status = ModeStatusN.REST
		self._remote_status = RemoteStatus.REMOTE_UNLOCKED

		self._t0 = time.time()
		self._calc_ramp_rate = 0
		self._calc_setpoint = 0



	name = 'Fake_Magnet_PSU'


	def _update_field(self):
		t = time.time() - self._t0
		d = self._setpoint - self._field

		if d >= 0:
			self._field = min([self._field + t*self._calc_ramp_rate, self._setpoint])
			self._t0 = time.time()
		else:
			self._field = max([self._field + t*self._calc_ramp_rate, self._setpoint])
			self._t0 = time.time()

		if abs(self._field - self._setpoint) <= 0.001:
			self._set_hold()



	def _set_hold(self):
		self._activity_status = ActivityStatus.HOLD 
		self._sweep_status = ModeStatusN.REST
		self._calc_ramp_rate = 0



	@query
	def identify(self) -> str:
		return self.name


	@query
	def get_output_current(self) -> float:
		return self._field * self._amps_per_tesla


	@query
	def get_supply_voltage(self) -> float:
		return 0


	@query
	def get_magnet_current(self) -> float:
		return self._current


	@query
	def get_setpoint_current(self) -> float:
		return self._setpoint * self._amps_per_tesla


	@query
	def get_current_sweep_rate(self) -> float:
		return self._ramp_rate * self._amps_per_tesla


	@query
	def get_output_field(self) -> float:
		self._update_field()
		return self._field


	@query
	def get_setpoint_field(self) -> float:
		return self._setpoint


	@query
	def get_field_sweep_rate(self) -> float:
		return self._ramp_rate


	@query
	def get_software_voltage_limit(self) -> float:
		return 0


	@query
	def get_persistent_current(self) -> float:
		return self._persistant_field * self._amps_per_tesla


	@query
	def get_trip_current(self) -> float:
		return 0


	@query
	def get_persistent_field(self) -> float:
		return self._persistant_field


	@query
	def get_trip_field(self) -> float:
		return 0


	@query
	def get_switch_heater_current(self) -> float:
		return 0


	@query
	def get_negative_current_limit(self) -> float:
		return 0


	@query
	def get_positive_current_limit(self) -> float:
		return 0


	@query
	def get_lead_resistance(self) -> float:
		return 0


	@query
	def get_magnet_inductance(self) -> float:
		return 0


	@query 
	def get_system_status(self) -> SystemStatusM:
		return self._system_status_m


	@query
	def get_limit_status(self) -> SystemStatusN:
		return self._system_status_n


	@query
	def get_activity_status(self) -> ActivityStatus:
		return self._activity_status


	@query
	def get_remote_status(self) -> RemoteStatus:
		return self._remote_status


	@query
	def get_switch_heater_status(self) -> SwitchHeaterStatus:
		return self._switch_heater_status


	@query
	def get_sweep_mode_status(self) -> ModeStatusM:
		return self._mode_status_m


	@query
	def get_sweep_status(self) -> ModeStatusN:
		return self._sweep_status


	@query
	def hold(self) -> int:
		self._update_field()
		self._activity_status = ActivityStatus.HOLD 
		self._sweep_status = ModeStatusN.REST
		self._calc_ramp_rate = 0
		return 0


	@query
	def to_setpoint(self) -> int:
		self._update_field()
		self._activity_status = ActivityStatus.TO_SETPOINT
		self._sweep_status = ModeStatusN.SWEEPING
		self._calc_ramp_rate = self._ramp_rate
		self._calc_setpoint = self._setpoint
		return 0


	@query
	def to_zero(self) -> int:
		self._update_field()
		self._activity_status = ActivityStatus.TO_ZERO
		self._setpoint = 0
		self._calc_ramp_rate = -self._ramp_rate
		self._calc_setpoint = 0
		return 0


	@query
	def clamp(self) -> int:
		return 0


	@query
	def heater_off(self) -> str:
		self._update_field()
		if self._field == 0:
			self._switch_heater_status = SwitchHeaterStatus.OFF_AT_ZERO
		else:
			self._switch_heater_status = SwitchHeaterStatus.OFF_AT_FIELD
		self._persistant_field = self._field
		return self._switch_heater_status


	@query
	def heater_on(self) -> str:
		self._switch_heater_status = SwitchHeaterStatus.ON
		return self._switch_heater_status


	@query
	def force_heater_on(self) -> int:
		self._switch_heater_status = SwitchHeaterStatus.ON
		return self._switch_heater_status


	@query
	def set_target_current(self, current: float) -> int:
		self._update_field()
		self._setpoint = current / self._amps_per_tesla
		return 0


	@query
	def set_target_field(self, field: float) -> int:
		self._update_field()
		self._setpoint = field
		return 0


	@query
	def set_current_sweep_rate(self, rate: float) -> int:
		self._update_field()
		self._ramp_rate = rate / self._amps_per_tesla
		return 0


	@query
	def set_field_sweep_rate(self, rate: float) -> int:
		self._update_field()
		self._ramp_rate = rate
		return 0



	def register_endpoints(self, app):
		super().register_endpoints(app)


		@app.get(f'/{self._uid}/identify', tags=[self._uid])
		async def identify() -> str:
			return self.identify()


		@app.get(f'/{self._uid}/get/output_current', tags=[self._uid])
		async def get_output_current() -> float:
			return self.get_output_current()


		@app.get(f'/{self._uid}/get/supply_voltage', tags=[self._uid])
		async def get_supply_voltage() -> float:
			return self.get_supply_voltage()


		@app.get(f'/{self._uid}/get/magnet_current', tags=[self._uid])
		async def get_magnet_current() -> float:
			return self.get_magnet_current()


		@app.get(f'/{self._uid}/get/setpoint_current', tags=[self._uid])
		async def get_setpoint_current() -> float:
			return self.get_setpoint_current()


		@app.get(f'/{self._uid}/get/current_sweep_rate', tags=[self._uid])
		async def get_current_sweep_rate() -> float:
			return self.get_current_sweep_rate()


		@app.get(f'/{self._uid}/get/output_field', tags=[self._uid])
		async def get_output_field() -> float:
			return self.get_output_field()


		@app.get(f'/{self._uid}/get/setpoint_field', tags=[self._uid])
		async def get_setpoint_field() -> float:
			return self.get_setpoint_field()


		@app.get(f'/{self._uid}/get/field_sweep_rate', tags=[self._uid])
		async def get_field_sweep_rate() -> float:
			return self.get_field_sweep_rate()


		@app.get(f'/{self._uid}/get/software_voltage_limit', tags=[self._uid])
		async def get_software_voltage_limit() -> float:
			return self.get_software_voltage_limit()


		@app.get(f'/{self._uid}/get/persistant_current', tags=[self._uid])
		async def get_persistant_current() -> float:
			return self.get_persistant_current()


		@app.get(f'/{self._uid}/get/trip_current', tags=[self._uid])
		async def get_trip_current() -> float:
			return self.get_trip_current()


		@app.get(f'/{self._uid}/get/persistant_field', tags=[self._uid])
		async def get_persistant_field() -> float:
			return self.get_persistant_field()


		@app.get(f'/{self._uid}/get/trip_field', tags=[self._uid])
		async def get_trip_field() -> float:
			return self.get_trip_field()


		@app.get(f'/{self._uid}/get/switch_heater_current', tags=[self._uid])
		async def get_switch_heater_current() -> float:
			return self.get_switch_heater_current()


		@app.get(f'/{self._uid}/get/negative_current_limit', tags=[self._uid])
		async def get_negative_current_limit() -> float:
			return self.get_negative_current_limit()


		@app.get(f'/{self._uid}/get/positive_current_limit', tags=[self._uid])
		async def get_positive_current_limit() -> float:
			return self.get_positive_current_limit()


		@app.get(f'/{self._uid}/get/lead_resistance', tags=[self._uid])
		async def get_lead_resistance() -> float:
			return self.get_lead_resistance()


		@app.get(f'/{self._uid}/get/magnet_inductance', tags=[self._uid])
		async def get_magnet_inductance() -> float:
			return self.get_magnet_inductance()


		@app.get(f'/{self._uid}/get/system_status', tags=[self._uid])
		async def get_system_status() -> SystemStatusMModel:
			return SystemStatusMModel[self.get_system_status().name]


		@app.get(f'/{self._uid}/get/limit_status', tags=[self._uid])
		async def get_limit_status() -> SystemStatusNModel:
			return SystemStatusNModel[self.get_limit_status().name]


		@app.get(f'/{self._uid}/get/activity_status', tags=[self._uid])
		async def get_activity_status() -> ActivityStatusModel:
			return ActivityStatusModel[self.get_activity_status().name]


		@app.get(f'/{self._uid}/get/remote_status', tags=[self._uid])
		async def get_remote_status() -> RemoteStatusModel:
			return RemoteStatusModel[self.get_remote_status().name]


		@app.get(f'/{self._uid}/get/heater_status', tags=[self._uid])
		async def get_switch_heater_status() -> SwitchHeaterStatusModel:
			return SwitchHeaterStatusModel[self.get_switch_heater_status().name]


		@app.get(f'/{self._uid}/get/sweep_mode_status', tags=[self._uid])
		async def get_sweep_mode_status() -> ModeStatusMModel:
			return ModeStatusMModel[self.get_sweep_mode_status().name]


		@app.get(f'/{self._uid}/get/sweep_status', tags=[self._uid])
		async def get_sweep_status() -> ModeStatusNModel:
			return ModeStatusNModel[self.get_sweep_status().name]



		@app.get(f'/{self._uid}/set/hold', tags=[self._uid])
		async def hold() -> int:
			self.hold()
			return 0


		@app.get(f'/{self._uid}/set/to_setpoint', tags=[self._uid])
		async def to_setpoint() -> int:
			self.to_setpoint()
			return 0


		@app.get(f'/{self._uid}/set/to_zero', tags=[self._uid])
		async def to_zero() -> int:
			self.to_zero()
			return 0


		@app.get(f'/{self._uid}/set/clamp', tags=[self._uid])
		async def clamp() -> int:
			self.clamp()
			return 0


		@app.get(f'/{self._uid}/set/heater_off', tags=[self._uid])
		async def heater_off() -> int:
			self.heater_off()
			return 0


		@app.get(f'/{self._uid}/set/heater_on', tags=[self._uid])
		async def heater_on() -> int:
			self.heater_on()
			return 0


		@app.get(f'/{self._uid}'+'/set/target_current/{current}', tags=[self._uid])
		async def set_target_current(current: float) -> int:
			self.set_target_current(current)
			return 0


		@app.get(f'/{self._uid}'+'/set/target_field/{field}', tags=[self._uid])
		async def set_target_field(field: float) -> int:
			self.set_target_field(field)
			return 0


		@app.get(f'/{self._uid}'+'/set/current_sweep_rate/{rate}', tags=[self._uid])
		async def set_current_sweep_rate(rate: float) -> int:
			self.set_current_sweep_rate(rate)
			return 0


		@app.get(f'/{self._uid}'+'/set/field_sweep_rate/{rate}', tags=[self._uid])
		async def set_field_sweep_rate(rate: float) -> int:
			self.set_field_sweep_rate(rate)
			return 0



