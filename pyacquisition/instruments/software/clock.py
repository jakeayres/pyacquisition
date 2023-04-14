from ...instruments._instrument import SoftInstrument, query, command
import time


class Clock(SoftInstrument):


	name = 'Clock'


	def __init__(self):
		super().__init__()

		self._named_timers = {}
		self._t0 = time.time()


	@query
	def timestamp_ms(self) -> float:
		return float(f'{time.time():.3f}')


	@query
	def time(self) -> float:
		return time.time() - self._t0


	@command
	def start_named_timer(self, timer_name: str):
		self._named_timers[timer_name] = time.time()
		return 0


	@query
	def read_named_timer(self, timer_name: str) -> float:
		return self.timestamp_ms() - self._named_timers[timer_name]
