from ..logger import logger
from ..scribe import scribe
from .coroutine import Coroutine
from ..dataframe import DataFrameManager

import asyncio
from dataclasses import dataclass



@dataclass
class StartDataFrame(Coroutine):

    dataframe_manager: DataFrameManager
    name: str


    def string(self):
        return f"Start Dataframe: {self.name}"


    async def run(self):

        yield ''

        try:
            self.dataframe_manager.add_dataframe(self.name)
            logger.info(f"Started DataFrame: {self.name}")

        except Exception as e:
            logger.error('Error starting dataframe')
            print(e)
            raise e




    @classmethod
    def register_endpoints(
        cls, 
        experiment,
        ):

        @experiment.api.get('/experiment/start_dataframe/', tags=['Routines'])
        async def start_dataframe(
            name: str,
            ) -> int:
            """ Start a new dataframe"""
            await experiment.add_task(
                cls(
                    dataframe_manager=experiment.dataframe_manager,
                    name=name,
                    )
                )
            return 0
        

@dataclass
class CloseDataFrame(Coroutine):

    dataframe_manager: DataFrameManager
    name: str


    def string(self):
        return f"Close Dataframe: {self.name}"


    async def run(self):

        yield ''

        try:
            self.dataframe_manager.remove_dataframe(self.name)
            logger.info(f"Removed DataFrame: {self.name}")

        except Exception as e:
            logger.error('Error closing dataframe')
            print(e)
            raise e




    @classmethod
    def register_endpoints(
        cls, 
        experiment,
        ):

        @experiment.api.get('/experiment/close_dataframe/', tags=['Routines'])
        async def close_dataframe(
            name: str,
            ) -> int:
            """ Close existing dataframe"""
            await experiment.add_task(
                cls(
                    dataframe_manager=experiment.dataframe_manager,
                    name=name,
                    )
                )
            return 0
        

@dataclass
class PlotDataFrame(Coroutine):

    dataframe_manager: DataFrameManager
    name: str
    x_column: str
    y_column: str
    filename: str


    def string(self):
        return f"Plot Dataframe ({self.name}): {self.y_column} vs. {self.x_column}"


    async def run(self):

        yield ''

        try:
            dataframe = self.dataframe_manager.get_dataframe(self.name)
            dataframe.plot(x=self.x_column, y=self.y_column, filename=self.filename)
            logger.info(f"Plotted DataFrame: {self.name}")

        except Exception as e:
            logger.error('Error plotting dataframe')
            print(e)
            raise e




    @classmethod
    def register_endpoints(
        cls, 
        experiment,
        ):

        @experiment.api.get('/experiment/plot_dataframe/', tags=['Routines'])
        async def plot_dataframe(
            name: str,
            x_column: str,
            y_column: str,
            filename: str,
            ) -> int:
            """ Plot existing dataframe"""
            await experiment.add_task(
                cls(
                    dataframe_manager=experiment.dataframe_manager,
                    name=name,
                    x_column=x_column,
                    y_column=y_column,  
                    filename=filename,
                    )
                )
            return 0