from ..dataframe import DataFrame
from .coroutine import Coroutine
from ..scribe import Scribe
import asyncio
import numpy as np
from dataclasses import dataclass
import seaborn as sns
import matplotlib.pyplot as plt

from ..analysis.core.binning import bin_data



@dataclass
class AnalyseFieldSweep(Coroutine):

	scribe: Scribe
	dataframe: DataFrame
	time_column: str
	field_column: str
	voltage_columns: list[str]
	minimum_field: float
	maximum_field: float
	bin_width: float


	def string(self):
		return f"Analyse Field Sweep"


	async def run(self):

		dataframe.clear()

		yield ''
		data = bin_data(
			data=self.dataframe.data,
			column=self.field_column,
			minimum=self.minimum_field,
			maximum=self.maximum_field,
			width=self.bin_width,
			centers=True,
		)

		yield ''
		fig, ax = plt.subplots()

		