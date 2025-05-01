from ...core.instrument import SoftwareInstrument, mark_query, mark_command
from ...core.logging import logger

from enum import Enum


class StringEnum(Enum):
	INTERNAL = 'Internal'
	EXTERNAL = 'External'
     


class MockInstrument(SoftwareInstrument):
    
    
    name = "Mock Instrument"
    
    
    @mark_query
    def method_with_args(self, x: float, y: float) -> float:
        """
        A mock method that simulates some processing.
        
        Args:
            x (float): The first input value.
            y (float): The second input value.
        
        Returns:
            float: The sum of x and y.
        """
        logger.info(f"Method called with x: {x}, y: {y}")
        return x + y
    
    
    @mark_query
    def method_with_enum_args(self, x: StringEnum, y: StringEnum) -> str:
        """
        A mock method that simulates some processing with enum arguments.
        
        Args:
            x (StringEnum): The first input value.
            y (StringEnum): The second input value.
        
        Returns:
            str: A string indicating the method was called.
        """
        logger.info(f"Method called with x: {x}, y: {y}")
        ans = 0
        if x == StringEnum.INTERNAL:
            ans += 1
        if y == StringEnum.EXTERNAL:
            ans += 2
        return ans
            
    @mark_command
    def mock_method(self, *args, **kwargs):
        """
        A mock method that simulates some processing.
        
        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.
        
        Returns:
            str: A string indicating the method was called.
        """
        logger.info(f"Mock method called with args: {args}, kwargs: {kwargs}")
        


    def register_endpoints(self, api_server):
        super().register_endpoints(api_server)


        @api_server.app.get("/mock/float_inputs", tags=["Mock Instrument"])
        async def float_inputs(x: float, y: float):
            """
            Endpoint to get the list of float inputs.
            
            Returns:
                list[str]: List of float input names.
            """
            self.mock_method(x, y)
            return 0
        

        @api_server.app.get("/mock/string_inpnuts/", tags=["Mock Instrument"])
        async def string_inputs(x: str, y: str):
            """
            Endpoint to get the list of string inputs.
            
            Returns:
                list[str]: List of string input names.
            """
            self.mock_method(x, y)
            return 0
        

        @api_server.app.get("/mock/int_inputs/", tags=["Mock Instrument"])
        async def int_inputs(x: int, y: int):
            """
            Endpoint to get the list of int inputs.
            
            Returns:
                list[str]: List of int input names.
            """
            self.mock_method(x, y)
            return 0
        

        @api_server.app.get("/mock/enum_inputs/", tags=["Mock Instrument"])
        async def enum_inputs(x: StringEnum = StringEnum.EXTERNAL, y: StringEnum = StringEnum.INTERNAL):
            """
            Endpoint to get the list of enum inputs.
            
            Returns:
                list[str]: List of enum input names.
            """
            self.mock_method(x, y)
            return 0
        
    