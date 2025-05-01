from ...core.instrument import SoftwareInstrument, mark_query, mark_command
from ...core.logging import logger

from enum import Enum


class StringEnum(Enum):
	INTERNAL = 'Internal'
	EXTERNAL = 'External'
     


class MockInstrument(SoftwareInstrument):


    def mock_method(self, *args, **kwargs):
        """
        A mock method that simulates some processing.
        
        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.
        
        Returns:
            str: A string indicating the method was called.
        """
        logger.info("Mock method called with args: {}, kwargs: {}".format(args, kwargs))
        


    def register_endpoints(self, api_server):
        super().register_endpoints(api_server)


        @api_server.app.get("/mock/float_inputs", tags=["Mock Instrument"])
        async def float_inputs(x: float, y: float):
            """
            Endpoint to get the list of float inputs.
            
            Returns:
                list[str]: List of float input names.
            """
            self.mock_method()
            return 0
        

        @api_server.app.get("/mock/string_inpnuts/", tags=["Mock Instrument"])
        async def string_inputs(x: str, y: str):
            """
            Endpoint to get the list of string inputs.
            
            Returns:
                list[str]: List of string input names.
            """
            self.mock_method()
            return 0
        

        @api_server.app.get("/mock/int_inputs/", tags=["Mock Instrument"])
        async def int_inputs(x: int, y: int):
            """
            Endpoint to get the list of int inputs.
            
            Returns:
                list[str]: List of int input names.
            """
            self.mock_method()
            return 0
        

        @api_server.app.get("/mock/enum_inputs/", tags=["Mock Instrument"])
        async def enum_inputs(x: StringEnum = StringEnum.EXTERNAL, y: StringEnum = StringEnum.INTERNAL):
            """
            Endpoint to get the list of enum inputs.
            
            Returns:
                list[str]: List of enum input names.
            """
            self.mock_method()
            return 0
        
    