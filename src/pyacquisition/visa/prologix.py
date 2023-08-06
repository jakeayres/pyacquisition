from serial import Serial
import datetime


class PrologixResourceManager(object):

	""" A manual implementation of a ResourceManager class that
	is designed to mimic the functionality of the pyvisa.ResourceManager()
	"""

	GPIB_ADDRESS_RANGE = (1, 30)
	BUAD_RATE = 115200
	TIMEOUT = 0.1

	def __init__(self, com_port):
		self._serial_object = Serial(f'COM{com_port}', self.BUAD_RATE, timeout=self.TIMEOUT)
		self._resources = []


	def _write(self, command):
		command = command+'\n'
		self._serial_object.write(command.encode('utf-8'))


	def _read(self):
		response = self._serial_object.readline()
		return response.decode('utf-8')


	def _query(self, command):
		self._write(command)
		return self._read()


	def _set_gpib_address(self, gpib_address):
		self._write(f'++addr {gpib_address}')
		

	def _identify_resource(self, gpib_address):
		self._set_gpib_address(gpib_address)
		return self._query('*IDN?')


	def _find_instruments(self):
		instruments = []
		for address in range(self.GPIB_ADDRESS_RANGE[0], self.GPIB_ADDRESS_RANGE[1]):
			response = self._identify_resource(address)
			if response != '':
				instruments.append(f'GPIB0::{address}::INSTR')
		return (instruments)


	def list_resources(self):
		self._resources = self._find_instruments()
		print(self._resources)
		return self._resources


	def open_resource(self, gpib_resource_string):
		return PrologixResource(self._serial_object, gpib_resource_string)


class PrologixResource(object):

	""" A class to mimic the returned object from pyvisa.open_resource
	function. Public methods are .write() and .query()
	"""

	def __init__(self, serial_object, gpib_resource_string):
		self._serial_object = serial_object
		self._gpib_address = int(gpib_resource_string.split('::')[1])


	def _write(self, command):
		command = command+'\n'
		self._serial_object.write(command.encode('utf-8'))


	def _read(self):
		response = self._serial_object.readline();
		return response.decode('utf-8')


	def _query(self, command):
		self._write(command)
		return self._read()


	def _set_gpib_address(self):
		self._write(f'++addr {self._gpib_address}')


	def address(self):
		return self._gpib_address()


	def write(self, command):
		self._set_gpib_address()
		self._write(command)
		return 0


	def query(self, command):
		self._set_gpib_address()
		return self._query(command)