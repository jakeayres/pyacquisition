from .consumer import Consumer
import pandas as pd



class DataFrame(Consumer):
	"""
	Wraps the pandas dataframe but consumes data from broadcasters

	Intended use:

	-  Instantiated within coroutines with a subscription to Rack object.
	-  Receives data over time
	-  Performs some analysis on the data
	-  Upon completion, is passed to Scribe object to be saved to file
	"""


	def __init__(self, columns: list[str]):
		super().__init__()

		self._dataframe = pd.DataFrame(columns=columns)


	@property
	def data(self):
		return self._dataframe


	@property
	def columns(self):
		return self._dataframe.columns


	async def _clear_queue(self):
		self._queue.clear()


	async def _get_data_from_queue(self):
		"""
		New dataframe with data from the queue

		:returns:   The data from queue.
		:rtype:     { return_type_description }
		"""

		df = pd.DataFrame(columns=self.columns)
		for i in range(self._queue.length()):
			x = await self._queue.get()
			df.loc[i] = [v for k, v in x.items()]
		return df


	async def update(self):
		"""
		Update the pandas DataFrame with data from the queue
		"""
		new_data = await self._get_data_from_queue()
		self._dataframe = pd.concat([self._dataframe, new_data])


	async def clear(self):
		await self._clear_queue()
		self._dataframe = pd.DataFrame(columns=self.columns)














