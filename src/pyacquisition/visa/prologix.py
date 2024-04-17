from serial import Serial
import datetime


class PrologixResourceManager(object):

	""" A manual implementation of a ResourceManager class that
	is designed to mimic the functionality of the pyvisa.ResourceManager()
	"""

	GPIB_ADDRESS_RANGE = (1, 30)
	BUAD_RATE = 115200
	TIMEOUT = 0.2


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


	def open_resource(self, gpib_resource_string, *args, **kwargs):
		return PrologixResource(self._serial_object, gpib_resource_string, *args, **kwargs)


class PrologixResource(object):

	""" A class to mimic the returned object from pyvisa.open_resource
	function. Public methods are .write() and .query()
	"""

	def __init__(
		self, 
		serial_object, 
		gpib_resource_string,
		read_termination='\n',
		write_termination='\n',
		read_after_write=True,
		):
		self._serial_object = serial_object
		self._gpib_address = int(gpib_resource_string.split('::')[1])
		self._read_termination = read_termination
		self._write_termination = write_termination
		self._read_after_write = read_after_write

		# self._set_gpib_address()
		# self._set_read_after_write()


	def _write(self, command):
		try:
			command = command+self._write_termination
			self._serial_object.write(command.encode('utf-8'))
		except Exception as e:
			print(f'Failed to send {command}')
			print(e)
			raise(e)


	def _read(self):
		response = self._serial_object.readline()
		return response.decode('utf-8')


	def _manual_read(self):
		self._write('++read eoi')
		response = self._read()
		return response


	def _query(self, command):
		self._write(command)
		return self._read()


	def _set_gpib_address(self):
		self._write(f'++addr {self._gpib_address}')


	def _set_read_after_write(self):
		self._write(f'++auto {int(self._read_after_write)}')


	def address(self):
		return self._gpib_address()


	def write(self, command):
		try:
			self._set_gpib_address()
			if not self._read_after_write:
				self._write('++auto 0')
			self._write(command)
		except Exception as e:
			print('Exception raised')
			print(e)
		return 0


	def query(self, command):
		self._set_gpib_address()
		self._write('++auto 1')
		return self._query(command)
	

	# def query(self, command):
	# 	if self._read_after_write:
	# 		self._set_gpib_address()
	# 		return self._query(command)
	# 	else:
	# 		self._set_gpib_address()
	# 		self._set_read_after_write()
	# 		self._write(command)
	# 		return self._manual_read()