import pandas as pd

from .consumer import Consumer



class Graph(Consumer):


    def __init__(self, columns: list[str]):
        super().__init__()

        self._dataframe = pd.DataFrame(columns=columns)


