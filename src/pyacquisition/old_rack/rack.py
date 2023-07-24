from ..instruments import instruments
from ..visa import resource_manager
import json


class Rack(object):

	""" Instrument Rack class that manages the addition, removal
	of instrument objects.

	Wraps a visa resource manager
	"""


	def __init__(self, visa_backend='pyvisa'):

		self._visa_resource_manager = resource_manager(visa_backend)
		self._instruments = {}


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


	@property
	def instruments(self):
		return self._instruments



	def add_instrument(self, key, instrument_class_name, visa_resource_string):
		""" Add instrument object to dictionary of _instruments 
		"""
		res = self._visa_resource_manager.open_resource(visa_resource_string)
		inst = instruments[instrument_class_name](res)
		self._instruments[key] = inst
		return inst


	def add_software_instrument(self, key, instrument_class_name):
		""" Add software instrument. No VISA resource required
		"""
		inst = instruments[instrument_class_name]()
		self._instruments[key] = inst
		return inst