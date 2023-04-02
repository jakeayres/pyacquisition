from ...instruments._instrument import SoftInstrument, query, command
import time


class Clock(SoftInstrument):


	name = 'Clock'


	def __init__(self):
		super().__init__()

		self._timers = {}


	@query
	def timestamp(self) -> float:
		return time.time()


	@command
	def start_timer(self, timer_name):
		self._timers[timer_name] = time.time()
		return 0


	@query
	def read_timer(self, timer_name) -> float:
		return self._timers[timer_name] - self.timestamp()
