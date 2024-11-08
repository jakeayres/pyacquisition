from ...instruments._instrument import SoftInstrument, query, command
import time
from datetime import datetime


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


	@query
	def datetime(self) -> datetime:
		return datetime.now()


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
		async def timestamp() -> float:
			"""Get a unix timestamp rounded to ms
			"""
			return self.timestamp_ms()


		@app.get(f'/{self._uid}/'+'time/get/', tags=[self._uid])
		async def time() -> float:
			"""Time since clock initiated
			"""
			return self.time()


		@app.get(f'/{self._uid}/'+'datetime/get/', tags=[self._uid])
		async def date_time() -> datetime:
			"""Datetime object
			"""
			return self.datetime()



