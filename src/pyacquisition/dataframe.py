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


	async def update(self):
		"""
		Retrieve data from the queue and add it to the pandas DataFrame
		"""

		for i in range(self._queue.length()):
			x = await self._queue.get()
			print(x)
			self._dataframe = pd.concat([self._dataframe, pd.DataFrame(x)], ignore_index=True)








