from ...instruments._instrument import SoftInstrument, query, command
import time


class Clock(SoftInstrument):


	name = 'Clock'


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

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


	def register_endpoints(self, app):
		super().register_endpoints(app)

		@app.get(f'/{self._uid}/'+'timestamp/get/', tags=[self._uid])
		def timestamp() -> float:
			return self.timestamp_ms()

		@app.get(f'/{self._uid}/'+'time/get/', tags=[self._uid])
		def time() -> float:
			return self.time()

