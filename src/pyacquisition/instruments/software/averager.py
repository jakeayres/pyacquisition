from ...instruments._instrument import SoftInstrument, query, command



class Averager(SoftInstrument):


	name = 'Averager'



	def __init__(
		self, 
		func: callable, 
		N: float, 
		*args, 
		**kwargs
		):
		super().__init__(*args, **kwargs)
		self._data = []
		self._callable = func
		self._N = N


	def _call(self):
		self._data.append(self._callable())


	def _crop_data(self):
		if len(self._data) > self._N:
			self._data = self._data[-self._N:]


	def _update(self):
		self._call()
		self._crop_data()


	@query
	def simple_moving_average(self) -> float:
		self._update()
		return float(sum(self._data))/float(len(self._data))


	@command
	def clear_data(self) -> int:
		self._data = []
		return 0


	def register_endpoints(self, app):
		super().register_endpoints(app)


		@app.get(f'/{self._uid}/'+'simple_moving_average/get/', tags=[self._uid])
		async def simple_moving_average() -> float:
			"""Get moving average
			"""
			return self.simple_moving_average()


		@app.get(f'/{self._uid}/'+'clear_data/', tags=[self._uid])
		async def simple_moving_average() -> float:
			"""Clear data
			"""
			self.clear_data()
			return 0

