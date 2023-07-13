from .broadcaster import Broadcaster
import asyncio, os, json



class Rack(Broadcaster):

	def __init__(self):
		super().__init__()

		self._instruments = {}
		self._measurements = {}


	def add_measurement(self, key, func):
		self._measurements[key] = func


	def measure(self):
		result = {k: v() for k, v in self._measurements.items()}
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
		def instruments():
			return [k for k, v in self._instruments.items()]

		@app.get('/rack/measurements', tags=['Rack'])
		def measurements():
			return [k for k, v in self._measurements.items()]


	async def run(self, period=0.5):
		while True:
			self.measure()
			await asyncio.sleep(period)


