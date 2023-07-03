from .broadcaster import Broadcaster
import asyncio, os, json



class Rack(Broadcaster):

	def __init__(self):
		super().__init__()

		# self.clock = Clock()
		# self.wave1 = WaveformGenerator()
		# self.wave2 = WaveformGenerator()
		# self.gizmo = Gizmotron()

		# self.wave2.set_amplitude(5)

		self._measurements = {}
		self._results = {}


	def add_measurement(self, key, func):
		self._measurements[key] = func


	def measure(self):
		result = {k: v() for k, v in self._measurements.items()}
		self.emit(result)


	def add_instrument(self, key, instrument_class_name, visa_resource_string):
		""" Add instrument object to dictionary of _instruments 
		"""
		from src.instruments import instruments
		res = self._visa_resource_manager.open_resource(visa_resource_string)
		inst = instruments[instrument_class_name](res)
		self.__dict__[key] = inst
		return inst


	def add_software_instrument(self, key, instrument_class_name):
		""" Add software instrument as a property of self
		"""
		from src.instruments import instruments
		inst = instruments[instrument_class_name]()
		self.__dict__[key] = inst
		return inst


	def _parse_dictionary(self, key, dictionary):
		""" Parse dictionary entry from json config file
		"""
		if 'visa_resource_string' in dictionary.keys():
			self.add_instrument(key, dictionary['class_name'], dictionary['visa_resource_string'])
		else:
			self.add_software_instrument(key, dictionary['class_name'])


	@classmethod
	def from_filepath(cls, filepath, **kwargs):
		""" Create Rack object from filepath of json config
		"""
		with open(filepath) as f:
			return cls.from_file(f, **kwargs)


	@classmethod
	def from_file(cls, file, **kwargs):
		""" Create Rack object from json config file
		"""
		json_ = json.load(file)
		return cls.from_json(json_, **kwargs)


	@classmethod
	def from_json(cls, json_, **kwargs):
		""" Create Rack object from json config
		"""
		rack = cls(**kwargs)
		for key, config in json_.items():
			print(key, config)
			rack._parse_dictionary(key, config)
		return rack


	async def run(self):
		while True:
			self.measure()
			await asyncio.sleep(0.5)


