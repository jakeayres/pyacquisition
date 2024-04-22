from serial import Serial
import datetime
import time


class PrologixResourceManager(object):

	""" A manual implementation of a ResourceManager class that
	is designed to mimic the functionality of the pyvisa.ResourceManager()
	"""

	GPIB_ADDRESS_RANGE = (1, 30)
	BUAD_RATE = 19200
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


	def _set_gpib_address(self, gpib_address: int):
		"""
		Sets the active gpib address.
		
		:param      gpib_address:  The gpib address
		:type       gpib_address:  { type_description }
		"""
		self._write(f'++addr {gpib_address}')


	def _set_read_after_write(self, read_after_write: bool):
		"""
		Sets whether instrument is configured to alk after sending a command.
		True: (Talk) instrument configured to talk back after a write
		False: (Listen) Listen to command. Will need to read manually if a response if made.
		
		:param      read_after_write:  The read after write
		:type       read_after_write:  bool
		"""
		self._write(f'++auto {int(read_after_write)}')


	def _set_eoi_signal_enabled(self, enabled: bool):
		"""
		Sets whether the eoi signal is asserted with the last character of commands sent.
		
		:param      enabled:  Indicates if enabled
		:type       enabled:  bool
		"""
		self._write(f'++eoi {int(enabled)}')


	def _set_eos_termination_character(self, character):
		"""
		Sets the eos termination character. Non-escaped LF, CR and ESC characters sent to
		the prologix controller are removed and the set EOS character(s) is appended. Only
		applies to data sent from the controller to a GPIB device.

		0: CL+LF
		1: CR
		2: LF
		3: None
		
		:param      character:  The character
		:type       character:  { type_description }
		"""
		self._write(f'++eos {int(character)}')


	def _enable_end_of_transmission_character(self, enabled: bool):
		"""
		Enables the appending of a user-specified character to receeved output whenever
		the EOI character is detected in received data. Only applies to data received from
		a GPIB instrument by the prologix controller.
		
		:param      character:  The character
		:type       character:  { type_description }
		"""
		self._write(f'++eot_enable {int(enabled)}')


	def _set_end_of_transmission_character(self, character: int):
		"""
		Sets the ascii character (0-256) to be appended when EOI is detected and EOT is enabled.

		Ascii character:
		eg. 10 = LF
		
		:param      character:  The character
		:type       character:  { type_description }
		"""
		self._write(f'++eot_char {character}')
		

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
		eot_enabled=False,
		eot_character=10,
		decoder='utf-8',
		):
		self._serial_object = serial_object
		self._gpib_address = int(gpib_resource_string.split('::')[1])
		self._read_termination = read_termination
		self._write_termination = write_termination
		self._read_after_write = read_after_write
		self._eot_enabled = eot_enabled
		self._decoder = decoder



	def _write(self, command):
		try:
			command = command+self._write_termination
			print(f'->   {command}')
			self._serial_object.write(command.encode(self._decoder))
			time.sleep(0.005)
		except Exception as e:
			print(f'Failed to send {command}')
			print(e)
			raise(e)


	def _read(self):
		response = self._serial_object.readline()
		print(f'<-   {response}')
		return response.decode(self._decoder)


	def _read_line(self):
		"""
		Reads a line.
		
		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		response = self._serial_object.readline()
		print(f'<-   {response}')
		return response.decode(self._decoder)


	def _read_bytes(self, N):
		"""
		Read a fixed number of bytes
		
		:returns:   { description_of_the_return_value }
		:rtype:     { return_type_description }
		"""
		response = self._serial_object.read(N)
		return response.decode(self._decoder)


	def _manual_read(self):
		self._write('++read')
		response = self._read()
		return response


	def _query(self, command, n_bytes=None):
		self._write(command)
		if n_bytes is None:
			return self._read_line()
		else:
			return self._read_bytes(n_bytes)


	def _set_gpib_address(self):
		self._write(f'++addr {self._gpib_address}')


	def _set_read_after_write(self):
		self._write(f'++auto {int(self._read_after_write)}')


	def address(self):
		return self._gpib_address()



	def write(self, command):
		try:
			self._set_gpib_address()
			self._set_read_after_write()
			self._write(command)
		except Exception as e:
			print('Exception raised')
			print(e)
		return 0


	def query(self, command, n_bytes=None):
		""" 
		"""

		self._set_gpib_address()
		self._write('++auto 1')
		return self._query(command, n_bytes=n_bytes)


	

