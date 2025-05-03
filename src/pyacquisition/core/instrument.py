from functools import partial, wraps
import inspect


class QueryCommandProvider(type):
	""" Metaclass that reads through methods and registers
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


def mark_query(func):
	""" Decorator for marking method as a query """
	func._is_query = True
	return func


def mark_command(func):
	""" Decorator for marking method as a query """
	func._is_command = True
	return func


def has_cache(func):
	""" Add cache functionality (save last result only) """
	func._cached = [0]

	@wraps(func) # This passes the func metadata onto wrapper
	def wrapper(*args, from_cache=False, **kwargs):
		if from_cache:
			return func._cached[0]
		else:
			result = func(*args, **kwargs)
			func._cached[0] = result
			return result

	return wrapper



class Instrument(metaclass=QueryCommandProvider):
	""" Base instrument class to be inherited by hardware instruments.

	Wraps a provided visa resource.
	"""

	name = 'Base Instrument'


	def __init__(self, uid, visa_resource):
		self._uid = uid
		self._visa_resource = visa_resource


	@property
	def metadata(self):
		return {
			'id': self._uid,
			'class': self.name,
			'address': self._visa_resource.address(),
		}


	@property
	def queries(self):
		""" return dictionary of registered queries as externally executable partials """
		return {q.__name__: partial(q, self) for q in self._queries}


	@property
	def commands(self):
		""" return dictionary of registered commands as externally executable partials """
		return {c.__name__: partial(c, self) for c in self._commands}


	def query(self, query_string, *args, **kwargs):
		""" Send a query to visa resource """
		return self._visa_resource.query(query_string, *args, **kwargs)


	def command(self, command_String, *args, **kwargs):
		""" Send a command to visa resource """
		return self._visa_resource.write(command_String, *args, **kwargs)


	def register_endpoints(self, api_server):
		
		@api_server.app.get(f'/{self._uid}/'+'queries/', tags=[self._uid])
		def queries() -> list[str]:
			return [name for name, _ in self.queries.items()]


		@api_server.app.get(f'/{self._uid}/'+'commands/', tags=[self._uid])
		def commands() -> list[str]:
			return [name for name, _ in self.commands.items()]


		# @app.get(f'/{self._uid}/'+'ask/{query_name}', tags=[self._uid])
		# def query(query_name: str):
		# 	return self.queries[query_name]()




class SoftwareInstrument(metaclass=QueryCommandProvider):
	""" Base class for software (non-hardware) instruments. 

	Does not wrap a visa resource.
	"""

	name = 'Software Instrument'


	def __init__(self, uid):
		self._uid = uid


	@property
	def queries(self) -> dict[str, callable]:
		""" return dictionary of registered queries as externally executable partials """
		return {q.__name__: partial(q, self) for q in self._queries}


	@property
	def commands(self) -> dict[str, callable]:
		""" return dictionary of registered commands as externally executable partials """
		return {c.__name__: partial(c, self) for c in self._commands}


	@mark_query
	def identify(self):
		return self.name


	def register_endpoints(self, api_server):


		@api_server.app.get(f'/{self._uid}/'+'identify', tags=[self._uid])
		def identify() -> dict:
			""" Return the name of the instrument """
			return {
				"status": 200,
				"data": f"{self._uid} ({self.name})",
			}
		
		@api_server.app.get(f'/{self._uid}/'+'queries/', tags=[self._uid])
		def list_queries() -> dict:
			""" Return a list of available queries """
			return {
				"status": 200,
				"data": [name for name, _ in self.queries.items()],
			}

		@api_server.app.get(f'/{self._uid}/'+'commands/', tags=[self._uid])
		def list_commands() -> dict:
			""" Return a list of available commands """
			return {
				"status": 200,
				"data": [name for name, _ in self.commands.items()],
			}
   
   
		for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
			if hasattr(method, "_is_query"):
				endpoint_path = f"/{self._uid}/{name}"
				endpoint_func = api_server.create_endpoint_function(method)
				api_server.app.add_api_route(
			        endpoint_path,
			        endpoint_func,
			        methods=["GET"],
			        tags=["tasks"],
			    )

			if hasattr(method, "_is_query"):
				endpoint_path = f"/{self._uid}/{name}"
				endpoint_func = api_server.create_endpoint_function(method)
				api_server.app.add_api_route(
			        endpoint_path,
			        endpoint_func,
			        methods=["GET"],
			        tags=["tasks"],
			    )
    
			



