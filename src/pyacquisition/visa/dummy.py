import numpy as np


class DummyResourceManager:


	def __init__(self, output:str='random'):
		self._output = output


	def _write(self, command):
		pass


	def open_resource(self, gpib_resource_string, *args, **kwargs):
		return DummyResource(*args, output=self._output, **kwargs)



class DummyResource:


	def __init__(self, 
		read_termination=None,
		write_termination=None,
		output:str='random'
		):
		self._output = output


	def write(self, command):
		return 0


	def query(self, command):

		if self._output == 'random':
			return f'{np.random.random()*10:.3f}'
