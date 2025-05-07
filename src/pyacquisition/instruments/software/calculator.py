from ...core.instrument import SoftwareInstrument, BaseEnum, mark_query, mark_command
import math


class TrigFunction(BaseEnum):
    SIN = (0, "sine")
    COS = (1, "cosine")
    TAN = (2, "tangent")
    
class AngleUnit(BaseEnum):
    DEGREE = (0, "degree")
    RADIAN = (1, "radian")


class Calculator(SoftwareInstrument):
    """
    A mock calculator instrument that performs basic arithmetic operations.

    Mainly used as a test instrument for the pyacquisition framework.
    """
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._units = AngleUnit.RADIAN
        
        
    @mark_command
    def set_angle_unit(self, unit: AngleUnit) -> int:
        """
        Sets the angle unit for trigonometric functions.

        Args:
            unit (AngleUnit): The angle unit to set.
        """
        self._units = unit
        return 0
    
    
    @mark_query
    def get_angle_unit(self) -> AngleUnit:
        """
        Gets the current angle unit.

        Returns:
            AngleUnit: The current angle unit.
        """
        return self._units
        

    @mark_query
    def one(self) -> float:
        """
        Returns the number one.

        Returns:
            float: The number one.
        """
        return 1.0

    @mark_query
    def add(self, x: float, y: float) -> float:
        """
        Adds two numbers.

        Args:
            x (float): The first number.
            y (float): The second number.

        Returns:
            float: The sum of x and y.
        """
        return x + y

    @mark_query
    def trig(self, x: float, function: TrigFunction) -> float:
        """
        Applies a trigonometric function to a number.

        Args:
            x (float): The number to apply the function to.
            function (TrigFunction): The trigonometric function to apply.

        Returns:
            float: The result of applying the function to x.
        """
        if function == TrigFunction.SIN:
            return math.sin(x)
        elif function == TrigFunction.COS:
            return math.cos(x)
        elif function == TrigFunction.TAN:
            return math.tan(x)
