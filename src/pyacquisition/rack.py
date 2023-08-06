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
		self._call_counter -= 1
		if (self._call_counter == 0) or (self._last_result == None):
			self.call()
			self._call_counter = self._call_every
		return self._last_result





class Rack(Broadcaster):

	def __init__(self, period=0.5):
		super().__init__()

		self._instruments = {}
		self._measurements = {}
		self._last_point = {}

		self._period = 0.5


	@property
	def metadata(self):
		return {key: inst.metadata for key, inst in self._instruments.items()}


	@property
	def data(self):
		return self._last_point


	@property
	def period(self):
		return self._period


	def set_period(self, period):
		self._period = period


	def add_measurement(self, key, func, call_every=1):
		self._measurements[key] = Measurement(
			key, 
			func,
			call_every=call_every,
		)


	def measure(self):
		result = {k: v.run() for k, v in self._measurements.items()}
		self._last_points = result
		self.emit(result)


	def add_instrument(self, key, instrument_class, visa_resource, api=None):
		""" Add instrument object to dictionary of _instruments 
		"""
		inst = instrument_class(uid=key, visa_resource=visa_resource)
		self.__dict__[key] = inst
		self._instruments[key] = inst
		if api != None:
			inst.register_endpoints(app)
		return inst


	def add_software_instrument(self, key, instrument_class, api=None):
		""" Add software instrument as a property of self
		"""
		inst = instrument_class(uid=key)
		self.__dict__[key] = inst
		self._instruments[key] = inst
		if api != None:
			inst.register_endpoints(app)
		return inst


	# def _parse_dictionary(self, key, dictionary):
	# 	""" Parse dictionary entry from json config file
	# 	"""
	# 	if 'visa_resource_string' in dictionary.keys():
	# 		self.add_instrument(key, dictionary['class_name'], dictionary['visa_resource_string'])
	# 	else:
	# 		self.add_software_instrument(key, dictionary['class_name'])


	# @classmethod
	# def from_filepath(cls, filepath, **kwargs):
	# 	""" Create Rack object from filepath of json config
	# 	"""
	# 	with open(filepath) as f:
	# 		return cls.from_file(f, **kwargs)


	# @classmethod
	# def from_file(cls, file, **kwargs):
	# 	""" Create Rack object from json config file
	# 	"""
	# 	json_ = json.load(file)
	# 	return cls.from_json(json_, **kwargs)


	# @classmethod
	# def from_json(cls, json_, **kwargs):
	# 	""" Create Rack object from json config
	# 	"""
	# 	rack = cls(**kwargs)
	# 	for key, config in json_.items():
	# 		rack._parse_dictionary(key, config)
	# 	return rack


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
		while True:
			try:
				t0 = time.time()
				self.measure()
				dt = time.time() - t0
				await asyncio.sleep(max(self._period - dt, 0))
			except Exception as e:
				print(e)


