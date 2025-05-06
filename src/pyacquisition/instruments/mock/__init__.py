from ...core.instrument import SoftwareInstrument, mark_query, mark_command
from ...core.logging import logger
from enum import Enum


class BaseEnum(Enum):
    def __init__(self, raw_value, label):
        self.raw_value = raw_value
        self.label = label

    @property
    def value(self):
        return self.label


class IntEnum(BaseEnum):
    SEVEN = (7, "Seven")
    NINE = (9, "Nine")


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
    def method_with_enum_args(self, x: IntEnum, y: IntEnum) -> str:
        """
        A mock method that simulates some processing with enum arguments.

        Args:
            x (IntEnum): The first input value.
            y (IntEnum): The second input value.

        Returns:
            str: A string indicating the method was called.
        """
        logger.info(f"Method called with x: {x}, y: {y}")
        ans = 0
        if x == IntEnum.SEVEN:
            ans += 7
        if y == IntEnum.NINE:
            ans += 9
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
