from ...core.instrument import SoftwareInstrument, BaseEnum, mark_query, mark_command
import math


class TrigFunction(BaseEnum):
    SIN = (0, "sine")
    COS = (1, "cosine")
    TAN = (2, "tangent")


class AngleUnit(BaseEnum):
    DEGREE = (0, "degree")
    RADIAN = (1, "radian")


class InputChannel(BaseEnum):
    INPUT_A = ("A", "Input A")
    INPUT_B = ("B", "Input B")
    INPUT_C = ("C", "Input C")
    INPUT_D = ("D", "Input D")


class Calculator(SoftwareInstrument):
    """
    A mock calculator instrument that performs basic arithmetic operations.

    Mainly used as a test instrument for the pyacquisition framework.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._units = 1  # Default to radians

    @mark_query
    def get_temperature(self, input_channel: InputChannel) -> float:
        """Queries the temperature reading for a specific input channel.

        Args:
            input_channel (InputChannel): The input channel to query.

        Returns:
            float: The temperature reading.
        """
        if input_channel == InputChannel.INPUT_A:
            return 25.0
        elif input_channel == InputChannel.INPUT_B:
            return 30.0

    @mark_command
    def set_angle_unit(self, unit: AngleUnit) -> int:
        """
        Sets the angle unit for trigonometric functions.

        Args:
            unit (AngleUnit): The angle unit to set.
        """
        self._units = unit.raw_value
        return self._units

    @mark_query
    def get_angle_unit(self) -> AngleUnit:
        """
        Gets the current angle unit.

        Returns:
            AngleUnit: The current angle unit.
        """
        return AngleUnit.from_raw_value(self._units)

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
