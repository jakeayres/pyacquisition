import enum
from typing import List

from ...core.instrument import Instrument, mark_query, mark_command


class State(enum.Enum):
    OFF = 0
    ON = 1


class StateModel(enum.Enum):
    OFF = "Off"
    ON = "On"


class InputChannel(enum.Enum):
    INPUT_A = "A"
    INPUT_B = "B"
    INPUT_C = "C"
    INPUT_D = "D"


class InputChannelModel(enum.Enum):
    INPUT_A = "Input A"
    INPUT_B = "Input B"
    INPUT_C = "Input C"
    INPUT_D = "Input D"


class OutputChannel(enum.Enum):
    OUTPUT_1 = 1
    OUTPUT_2 = 2
    OUTPUT_3 = 3
    OUTPUT_4 = 4


class OutputChannelModel(enum.Enum):
    OUTPUT_1 = "Output 1"
    OUTPUT_2 = "Output 2"
    OUTPUT_3 = "Output 3"
    OUTPUT_4 = "Output 4"


class AutotuneMode(enum.Enum):
    P = 0
    PI = 1
    PID = 2


class AutotuneModeModel(enum.Enum):
    P = "P"
    PI = "PI"
    PID = "PID"


class CurveFormat(enum.Enum):
    MV_K = 1
    V_K = 2
    OHM_K = 3
    LOGOHM_K = 4


class CurveFormatModel(enum.Enum):
    MV_K = "mV / K"
    V_K = "V / K"
    OHM_K = "Ohm / K"
    LOGOHM_K = "log(Ohm) / K"


class CurveCoefficient(enum.Enum):
    NEGATIVE = 1
    POSITIVE = 2


class CurveCoefficientModel(enum.Enum):
    NEGATIVE = "Negative"
    POSITIVE = "Positive"


class DisplayContrast(enum.Enum):
    OFF = 1
    DIM = 12
    NORMAL = 18
    BRIGHT = 26
    MAXIMUM = 32


class DisplayContrastModel(enum.Enum):
    OFF = "Off"
    DIM = "Dim"
    NORMAL = "Normal"
    BRIGHT = "Bright"
    MAXIMUM = "Maximum"


class DisplayMode(enum.Enum):
    INPUT_A = 0
    INPUT_B = 1
    INPUT_C = 2
    INPUT_D = 3
    FOUR_LOOP = 5
    ALL_INPUTS = 6
    INPUT_D2 = 7
    INPUT_D3 = 8
    INPUT_D4 = 9
    INPUT_D5 = 10


class DisplayCustomNumber(enum.Enum):
    LARGE_2 = 0
    LARGE_4 = 1
    SMALL_8 = 2


class DisplayAllInputsSize(enum.Enum):
    SMALL = 0
    LARGE = 1


class Lakeshore_350(Instrument):
    """Class for controlling the Lakeshore 350 temperature controller."""

    name = "Lakeshore_350"

    def __init__(self, *args, **kwargs):
        """Initializes the Lakeshore 350 instrument."""
        super().__init__(*args, **kwargs)
        self.clear()
        self.clear_event_register()

    @mark_query
    def identify(self) -> str:
        """Identifies the instrument.

        Returns:
            str: The identification string of the instrument.
        """
        return self.query("*IDN?")

    @mark_command
    def reset(self) -> int:
        """Resets the instrument to its default state.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*RST")

    @mark_command
    def clear(self) -> int:
        """Clears the instrument's status.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*CLS")

    @mark_command
    def clear_event_register(self) -> int:
        """Clears the event status register.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*ESR")

    @mark_query
    def get_alarm(self) -> dict:
        """Queries the alarm status of the instrument.

        Returns:
            dict: A dictionary containing alarm details:
                - state (str): The alarm state.
                - high_value (str): The high alarm value.
                - low_value (str): The low alarm value.
                - deadband (str): The deadband value.
                - latch (str): The latch state.
                - audible (str): The audible alarm state.
                - visible (str): The visible alarm state.
        """
        response = self.query("ALARM?").split(",")
        return {
            "state": response[0],
            "high_value": response[1],
            "low_value": response[2],
            "deadband": response[3],
            "latch": response[4],
            "audible": response[5],
            "visible": response[6],
        }

    @mark_query
    def get_analog_output(self) -> float:
        """Queries the analog output value.

        Returns:
            float: The analog output value.
        """
        return float(self.query("AOUT?"))

    @mark_command
    def set_autotune_pid(self, output: int, mode: int) -> int:
        """Sets the autotune PID mode for a specific output channel.

        Args:
            output (int): The output channel to configure.
            mode (int): The autotune mode to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ATUNE {output},{mode}")

    @mark_command
    def set_display_contrast(self, contrast: int) -> int:
        """Sets the display contrast level.

        Args:
            contrast (int): The desired display contrast level.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"BRIGT {contrast}")

    @mark_query
    def get_display_contrast(self) -> int:
        """Queries the current display contrast level.

        Returns:
            int: The current display contrast level.
        """
        return int(self.query("BRIGT?"))

    @mark_command
    def set_curve_header(
        self,
        curve_index: int,
        name: str,
        serial_no: str,
        curve_format: int,
        upper_limit: int,
        coefficient: int,
    ) -> int:
        """Sets the curve header information.

        Args:
            curve_index (int): The index of the curve.
            name (str): The name of the curve.
            serial_no (str): The serial number of the curve.
            curve_format (int): The format of the curve.
            upper_limit (int): The upper limit of the curve.
            coefficient (int): The coefficient of the curve.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"CRVHDR {curve_index},{name},{serial_no},{curve_format},{upper_limit},{coefficient}"
        )

    @mark_query
    def get_curve_header(self, curve_index: int) -> str:
        """Queries the curve header information.

        Args:
            curve_index (int): The index of the curve.

        Returns:
            str: The curve header information.
        """
        return self.query(f"CRVHDR? {curve_index}")

    @mark_query
    def get_curve_point(self, curve_index: int, point_index: int) -> str:
        """Queries a specific point on a curve.

        Args:
            curve_index (int): The index of the curve.
            point_index (int): The index of the point on the curve.

        Returns:
            str: The curve point information.
        """
        return self.query(f"CRVPT? {curve_index},{point_index}")

    @mark_command
    def set_curve_point(
        self, curve_index: int, point_index: int, sensor: float, temperature: float
    ) -> int:
        """Sets a specific point on a curve.

        Args:
            curve_index (int): The index of the curve.
            point_index (int): The index of the point on the curve.
            sensor (float): The sensor value.
            temperature (float): The temperature value.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CRVPT {curve_index},{point_index},{sensor},{temperature}")

    @mark_command
    def set_display_setup(self, mode: int) -> int:
        """Sets the display mode.

        Args:
            mode (int): The desired display mode.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"DISPLAY {mode},0,0")

    @mark_query
    def get_display_setup(self) -> List[int]:
        """Queries the current display setup.

        Returns:
            List[int]: A list of integers representing the display setup.
        """
        return [int(i) for i in self.query("DISPLAY?").split(",")]

    @mark_query
    def get_temperature(self, input_channel: int) -> float:
        """Queries the temperature reading for a specific input channel.

        Args:
            input_channel (int): The input channel to query.

        Returns:
            float: The temperature reading.
        """
        return float(self.query(f"KRDG? {input_channel}"))

    @mark_command
    def set_ramp(self, output_channel: int, state: int, rate: float) -> int:
        """Sets the ramp configuration for a specific output channel.

        Args:
            output_channel (int): The output channel to configure.
            state (int): The state of the ramp (ON/OFF).
            rate (float): The ramp rate.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"RAMP {output_channel},{state},{rate:.3f}")

    @mark_query
    def get_ramp(self, output_channel: int) -> float:
        """Queries the ramp rate for a specific output channel.

        Args:
            output_channel (int): The output channel to query.

        Returns:
            float: The ramp rate.
        """
        response = self.query(f"RAMP? {output_channel}").split(",")
        return float(response[1])

    @mark_query
    def get_setpoint(self, output_channel: int) -> float:
        """Queries the setpoint for a specific output channel.

        Args:
            output_channel (int): The output channel to query.

        Returns:
            float: The setpoint value.
        """
        return float(self.query(f"SETP? {output_channel}"))

    @mark_command
    def set_setpoint(self, output_channel: int, setpoint: float) -> int:
        """Sets the setpoint for a specific output channel.

        Args:
            output_channel (int): The output channel to configure.
            setpoint (float): The desired setpoint value.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SETP {output_channel},{setpoint:.2f}")
