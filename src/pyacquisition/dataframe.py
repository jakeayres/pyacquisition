from .consumer import Consumer
from .logger import logger

import pandas as pd
import asyncio



class DataFrameManager(Consumer):
	"""
	Manages the creation of dataframes from data received from broadcasters
	"""
	
	def __init__(self):
		super().__init__()
		self._dataframes = {}


	@property
	def dataframes(self):
		return self._dataframes
	

	def add_dataframe(self, name):
		self._dataframes[name] = DataFrame(name)
		logger.info(f"Added DataFrame: {name}")

	
	def remove_dataframe(self, name):
		if name in self._dataframes:
			del self._dataframes[name]
			logger.info(f"Removed DataFrame: {name}")
		else:
			logger.warning(f"DataFrame {name} does not exist.")


	def get_dataframe(self, name):
		return self._dataframes[name]
	

	def list_dataframes(self):
		return list(self._dataframes.keys())	
	

	async def run(self):
		while True:
			try:
				x = await self._queue.get()
				if x is None:
					break
				if x['message_type'] == 'data':
					# Process the data
					self.process_data(x)
			except Exception as e:
				logger.error(f"Error in DataFrameManager processing data: {e}")



	def process_data(self, data):
		# Implement your data processing logic here
		pass


	def register_endpoints(self, app):
		# Implement your endpoint registration logic here
		
		@app.get('/dataframes/add_dataframe', tags=['DataFrames'])
		async def add_dataframe(name: str):
			self.add_dataframe(name)
			return f"Added DataFrame: {name}"


		@app.get('/dataframes/remove_dataframe', tags=['DataFrames'])
		async def remove_dataframe(name: str):
			self.remove_dataframe(name)
			return f"Removed DataFrame: {name}"
		

		@app.get('/dataframes/list_dataframes', tags=['DataFrames'])
		async def list_dataframes():
			return self.list_dataframes()



class DataFrame():
	


	def __init__(self, name):
		super().__init__()
		self.name = name
		self._data = []

	def add_row(self, row):
		self._data.append(row)

	def to_dataframe(self):
		return pd.DataFrame(self._data)

	async def run(self):
		while True:
			try:
				x = await self._queue.get()
				if x is None:
					break
				if x['message_type'] == 'data':
					self.add_row(x['data'])
			except Exception as e:
				logger.error(f"Error in DataFrame processing data: {e}")








