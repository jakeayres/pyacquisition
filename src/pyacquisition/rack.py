from .broadcaster import Broadcaster
import asyncio, os, json, time



class Measurement:

	def __init__(self, name, func, call_every=1):

		self._name = name
		self._func = func
		self._call_every = call_every
		self._call_counter = call_every
		self._last_result = None


	@property
	def name(self):
		return self._name


	@property
	def func(self):
		return self._func


	def call(self):
		self._last_result = self.func()


	def run(self):
		try:
			self._call_counter -= 1
			if (self._call_counter == 0) or (self._last_result == None):
				self.call()
				self._call_counter = self._call_every
			return self._last_result
			
		except Exception as e:
			print(f'Failed to run measurement func:\t{self._name}')
			print(f'Returning last result:\t {self._last_result}')
			print(e)
			return self._last_result






class Rack(Broadcaster):

	def __init__(self, period: float = 0.5):
		super().__init__()

		self._instruments = {}
		self._measurements = {}
		self._last_datapoint = {}

		self._period = 1.0


	@property
	def metadata(self):
		return {key: inst.metadata for key, inst in self._instruments.items()}


	@property
	def data(self):
		return self._last_point


	@property
	def period(self):
		return self._period


	def set_period(self, period: float):
		"""
		Set the measurement period

		:param      period:  Measurement period
		:type       period:  float
		"""
		self._period = period


	def add_measurement(self, key: str, func: callable, call_every: int=1):
		"""
		Add a measurement to the dictionary of measurements

		:param      key:         dictionary key
		:type       key:         str
		:param      func:        The callable function
		:type       func:        callable
		:param      call_every:  Call every nth period
		:type       call_every:  int
		"""
		self._measurements[key] = Measurement(
			key, 
			func,
			call_every=call_every,
		)


	def measure(self):
		"""
		Call all of the Measurement objects and emit a dict of their results
		"""
		result = {k: v.run() for k, v in self._measurements.items()}
		self._last_datapoint = result
		self.emit(self._last_point)


	def add_instrument(self, key, instrument_class, visa_resource, api=None):
		""" 
		Add instrument object to dictionary of _instruments 
		"""
		inst = instrument_class(uid=key, visa_resource=visa_resource)
		self.__dict__[key] = inst
		self._instruments[key] = inst
		if api != None:
			inst.register_endpoints(app)
		return inst


	def add_software_instrument(self, key, instrument_class, api=None):
		""" 
		Add software instrument as a property of self
		"""
		inst = instrument_class(uid=key)
		self.__dict__[key] = inst
		self._instruments[key] = inst
		if api != None:
			inst.register_endpoints(app)
		return inst



	def register_endpoints(self, app):

		@app.get('/rack/instruments', tags=['Rack'])
		def instruments() -> list[str]:
			return [k for k, v in self._instruments.items()]

		@app.get('/rack/measurements', tags=['Rack'])
		def measurements() -> list[str]:
			return [k for k, v in self._measurements.items()]


		@app.get('/rack/period/get', tags=['Rack'])
		def get_period() -> float:
			return self._period


		@app.get('/rack/period/set/{period}', tags=['Rack'])
		def set_period(period: float) -> int:
			self.set_period(period)
			return 0


	async def run(self):
		"""
		Main entry point to run the rack object
		"""

		while True:
			try:
				t0 = time.time()
				self.measure()
				dt = time.time() - t0
				await asyncio.sleep(max(self._period - dt, 0))
			except Exception as e:
				print(e)


