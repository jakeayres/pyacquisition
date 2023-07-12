from functools import partial


class QueryCommandProvider(type):
	""" Metaclass that read through methods and registers
	those that are decorated as queries """

	def __init__(cls, name, bases, attrs):

		queries = set()
		commands = set()

		for name, method in attrs.items():

			if isinstance(method, property):
				method = method.fget

			if hasattr(method, '_is_query'):
				queries.add(method)

			elif hasattr(method, '_is_command'):
				commands.add(method)

		cls._queries = queries
		cls._commands = commands



def query(f):
	""" Decorator for marking methods as queries. """

	f._is_query = True

	return f


def command(f):
	""" Decorator for marking methods as commands. """

	f._is_command = True

	return f


# def parse(returns):
# 	""" Decorator for parsing instrument responses. """

# 	def outer(f):

# 		def inner(self, *args, **kwargs):
# 			response = self._query(f(self, *args, **kwargs))
# 			return {key[0]: key[1](value) for key, valye in zip(returns, response)}

# 		return innter

# 	return outer



class Instrument(metaclass=QueryCommandProvider):
	""" Base instrument class to be inherited by hardware instruments.

	Wraps a provided visa resource.
	"""

	name = 'Base Instrument'


	def __init__(self, uid, visa_resource):
		self._uid = uid
		self._visa_resource = visa_resource


	@property
	def queries(self):
		""" return dictionary of registered queries as externally executable partials """
		return {q.__name__: partial(q, self) for q in self._queries}


	@property
	def commands(self):
		""" return dictionary of registered commands as externally executable partials """
		return {c.__name__: partial(c, self) for c in self._commands}


	def _query(self, query_string):
		""" Send a query to visa resource """
		return self._visa_resource.query(query_string)


	def _command(self, command_String):
		""" Send a command to visa resource """
		return self._visa_resource.write(command_String)


	def register_endpoints(self, app):
		
		@app.get(f'/{self._uid}/'+'queries/', tags=[self._uid])
		def queries(app) -> list[str]:
			return [name for name, _ in self.queries.items()]


		@app.get(f'/{self._uid}/'+'commands/', tags=[self._uid])
		def queries(app) -> list[str]:
			return [name for name, _ in self.commands.items()]




class SoftInstrument(metaclass=QueryCommandProvider):
	""" Base class for software (non-hardware) instruments. 

	Does not wrap a visa resource.
	"""

	name = 'Software Instrument'


	def __init__(self, uid):
		self._uid = uid


	@property
	def queries(self):
		""" return dictionary of registered queries as externally executable partials """
		return {q.__name__: partial(q, self) for q in self._queries}


	@property
	def commands(self):
		""" return dictionary of registered commands as externally executable partials """
		return {c.__name__: partial(c, self) for c in self._commands}


	@query
	def identify(self):
		return self.name


	def register_endpoints(self, app):
		
		@app.get(f'/{self._uid}/'+'queries/', tags=[self._uid])
		def queries() -> list[str]:
			return [name for name, _ in self.queries.items()]


		@app.get(f'/{self._uid}/'+'commands/', tags=[self._uid])
		def commands() -> list[str]:
			return [name for name, _ in self.commands.items()]