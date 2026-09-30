"""The Lake Shore Model 340 temperature controller.

Every command in the manual's IEEE-488/serial command list (section 9.4) is here,
apart from `?`, which re-sends the last reply over the serial interface, and `*WAI`,
which the manual says the 340 doesn't support.
"""

from datetime import datetime

from ...core.instrument import BaseEnum, Instrument, mark_command, mark_query


def _number(value: float) -> str:
    """A number as the 340 takes it: up to six significant figures."""
    return f"{value:.6g}"


def _fields(reply: str) -> list[str]:
    """A reply's comma-separated fields, stripped."""
    return [field.strip() for field in reply.split(",")]


def _int(text: str) -> int:
    """A whole number from a reply, which may be written as `1` or `1.0`."""
    return int(float(text))


class State(BaseEnum):
    OFF = (0, "Off")
    ON = (1, "On")


class InputChannel(BaseEnum):
    """A sensor input. C and D are on an input option card."""

    INPUT_A = ("A", "Input A")
    INPUT_B = ("B", "Input B")
    INPUT_C = ("C", "Input C")
    INPUT_D = ("D", "Input D")


class OutputChannel(BaseEnum):
    """A control loop. Loop 1 drives the heater output, loop 2 analog output 2."""

    OUTPUT_1 = (1, "Output 1")
    OUTPUT_2 = (2, "Output 2")


class AnalogOutput(BaseEnum):
    """An analog output."""

    ANALOG_1 = (1, "Analog output 1")
    ANALOG_2 = (2, "Analog output 2")


class AutotuneMode(BaseEnum):
    """Which terms autotuning sets: its control mode's code."""

    P = (6, "P")
    PI = (5, "PI")
    PID = (4, "PID")


class ControlMode(BaseEnum):
    """How a control loop works out its output. `PID`, `ZONE` and `OPEN_LOOP` are
    named as the Lakeshore 350's are."""

    PID = (1, "Manual PID")
    ZONE = (2, "Zone")
    OPEN_LOOP = (3, "Open loop")
    AUTOTUNE_PID = (4, "AutoTune PID")
    AUTOTUNE_PI = (5, "AutoTune PI")
    AUTOTUNE_P = (6, "AutoTune P")


class Units(BaseEnum):
    """The units of a setpoint, or of the data a linear equation uses."""

    KELVIN = (1, "Kelvin")
    CELSIUS = (2, "Celsius")
    SENSOR_UNITS = (3, "Sensor units")


class InputData(BaseEnum):
    """The data of an input that an alarm, analog output or max/min uses."""

    KELVIN = (1, "Kelvin")
    CELSIUS = (2, "Celsius")
    SENSOR_UNITS = (3, "Sensor units")
    LINEAR = (4, "Linear data")


class DisplayData(BaseEnum):
    """The data of an input that a display field or a logged point shows."""

    KELVIN = (1, "Kelvin")
    CELSIUS = (2, "Celsius")
    SENSOR_UNITS = (3, "Sensor units")
    LINEAR = (4, "Linear data")
    MINIMUM = (5, "Minimum data")
    MAXIMUM = (6, "Maximum data")


class AnalogMode(BaseEnum):
    """What an analog output follows. Loop is for analog output 2 only."""

    OFF = (0, "Off")
    INPUT = (1, "Input")
    MANUAL = (2, "Manual")
    LOOP = (3, "Loop")


class HeaterRange(BaseEnum):
    """The heater's range. Each is a decade of power below the next."""

    OFF = (0, "Off")
    RANGE_1 = (1, "Range 1 (lowest)")
    RANGE_2 = (2, "Range 2")
    RANGE_3 = (3, "Range 3")
    RANGE_4 = (4, "Range 4")
    RANGE_5 = (5, "Range 5 (highest)")


class MaxCurrent(BaseEnum):
    """The most current the loop 1 heater output gives."""

    CURRENT_0_25 = (1, "0.25 A")
    CURRENT_0_5 = (2, "0.5 A")
    CURRENT_1 = (3, "1.0 A")
    CURRENT_2 = (4, "2.0 A")
    USER = (5, "User")


class LoopDisplay(BaseEnum):
    """Which control loops the display shows."""

    NONE = (0, "None")
    LOOP_1 = (1, "Loop 1")
    LOOP_2 = (2, "Loop 2")
    BOTH = (3, "Both loops")


class HeaterDisplay(BaseEnum):
    """Whether the heater output is shown as a current or a power."""

    CURRENT = (1, "Current")
    POWER = (2, "Power")


class SensorType(BaseEnum):
    """A sensor type, which sets an input's units, coefficient, excitation and range."""

    SPECIAL = (0, "Special")
    SILICON_DIODE = (1, "Silicon diode")
    GAALAS_DIODE = (2, "GaAlAs diode")
    PLATINUM_100_250 = (3, "Platinum 100 (250 Ω)")
    PLATINUM_100_500 = (4, "Platinum 100 (500 Ω)")
    PLATINUM_1000 = (5, "Platinum 1000")
    RHODIUM_IRON = (6, "Rhodium iron")
    CARBON_GLASS = (7, "Carbon-glass")
    CERNOX = (8, "Cernox")
    RUOX = (9, "RuOx")
    GERMANIUM = (10, "Germanium")
    CAPACITOR = (11, "Capacitor")
    THERMOCOUPLE = (12, "Thermocouple")


class SensorUnits(BaseEnum):
    """What an input measures."""

    VOLTS = (1, "Volts")
    OHMS = (2, "Ohms")


class Coefficient(BaseEnum):
    """Whether a sensor's reading falls or rises with temperature."""

    NEGATIVE = (1, "Negative")
    POSITIVE = (2, "Positive")


CurveCoefficient = Coefficient


class Excitation(BaseEnum):
    """An input's excitation."""

    OFF = (0, "Off")
    CURRENT_30_NA = (1, "30 nA")
    CURRENT_100_NA = (2, "100 nA")
    CURRENT_300_NA = (3, "300 nA")
    CURRENT_1_UA = (4, "1 µA")
    CURRENT_3_UA = (5, "3 µA")
    CURRENT_10_UA = (6, "10 µA")
    CURRENT_30_UA = (7, "30 µA")
    CURRENT_100_UA = (8, "100 µA")
    CURRENT_300_UA = (9, "300 µA")
    CURRENT_1_MA = (10, "1 mA")
    VOLTAGE_10_MV = (11, "10 mV")
    VOLTAGE_1_MV = (12, "1 mV")


class InputRange(BaseEnum):
    """An input's range, in volts."""

    RANGE_1_MV = (1, "1 mV")
    RANGE_2_5_MV = (2, "2.5 mV")
    RANGE_5_MV = (3, "5 mV")
    RANGE_10_MV = (4, "10 mV")
    RANGE_25_MV = (5, "25 mV")
    RANGE_50_MV = (6, "50 mV")
    RANGE_100_MV = (7, "100 mV")
    RANGE_250_MV = (8, "250 mV")
    RANGE_500_MV = (9, "500 mV")
    RANGE_1_V = (10, "1 V")
    RANGE_2_5_V = (11, "2.5 V")
    RANGE_5_V = (12, "5 V")
    RANGE_7_5_V = (13, "7.5 V")


class Compensation(BaseEnum):
    """Thermal compensation, for an NTC resistor or a special sensor."""

    OFF = (0, "Off")
    ON = (1, "On")
    PAUSE = (2, "Pause")


class CurveFormat(BaseEnum):
    """What a curve's points pair with temperature."""

    MV_K = (1, "mV/K")
    V_K = (2, "V/K")
    OHM_K = (3, "Ohm/K")
    LOGOHM_K = (4, "log(Ohm)/K")
    LOGOHM_LOGK = (5, "log(Ohm)/log(K)")


class LinearEquation(BaseEnum):
    """The form of an input's linear equation."""

    MX_PLUS_B = (1, "y = mx + b")
    M_X_PLUS_B = (2, "y = m(x + b)")


class LinearOffset(BaseEnum):
    """Where the b of an input's linear equation comes from."""

    VALUE = (1, "A value")
    PLUS_SETPOINT_1 = (2, "+Setpoint 1")
    MINUS_SETPOINT_1 = (3, "-Setpoint 1")
    PLUS_SETPOINT_2 = (4, "+Setpoint 2")
    MINUS_SETPOINT_2 = (5, "-Setpoint 2")


class MinMaxMode(BaseEnum):
    """Whether an input's max/min function runs or is paused."""

    ON = (1, "On")
    PAUSED = (2, "Paused")


class DigitalOutputMode(BaseEnum):
    """What drives the digital outputs."""

    OFF = (0, "Off")
    ALARMS = (1, "Alarms")
    SCANNER = (2, "Scanner")
    MANUAL = (3, "Manual")


class Relay(BaseEnum):
    """A relay."""

    HIGH = (1, "High")
    LOW = (2, "Low")


class RelayMode(BaseEnum):
    """What drives a relay."""

    OFF = (0, "Off")
    ALARMS = (1, "Alarms")
    MANUAL = (2, "Manual")


class RemoteMode(BaseEnum):
    """Whether the front panel or the interface is in control."""

    LOCAL = (1, "Local")
    REMOTE = (2, "Remote")
    REMOTE_LOCKOUT = (3, "Remote with local lockout")


class SerialTerminator(BaseEnum):
    """What ends a message on the serial interface."""

    CR_LF = (1, "CR LF")
    LF_CR = (2, "LF CR")
    CR = (3, "CR")
    LF = (4, "LF")


class IeeeTerminator(BaseEnum):
    """What ends a message on the IEEE-488 interface."""

    NONE = (0, "None")
    CR_LF = (1, "CR LF")
    LF_CR = (2, "LF CR")
    CR = (3, "CR")
    LF = (4, "LF")


class BaudRate(BaseEnum):
    """The serial interface's speed, in bits per second."""

    BPS_300 = (1, "300")
    BPS_1200 = (2, "1200")
    BPS_2400 = (3, "2400")
    BPS_4800 = (4, "4800")
    BPS_9600 = (5, "9600")
    BPS_19200 = (6, "19200")


class Parity(BaseEnum):
    """The serial interface's data bits, stop bits and parity."""

    SEVEN_ODD = (1, "7 data bits, 1 stop bit, odd parity")
    SEVEN_EVEN = (2, "7 data bits, 1 stop bit, even parity")
    EIGHT_NONE = (3, "8 data bits, 1 stop bit, no parity")


class ScanMode(BaseEnum):
    """How an external scanner is used."""

    OFF = (0, "Off")
    MANUAL = (1, "Manual")
    AUTOSCAN = (2, "Autoscan")
    SLAVE = (3, "Slave")


class LogType(BaseEnum):
    """Whether data logging counts readings or seconds between records."""

    READINGS = (1, "Readings")
    SECONDS = (2, "Seconds")


class LogStartMode(BaseEnum):
    """Whether starting data logging clears the log or continues it."""

    CLEAR = (0, "Clear")
    CONTINUE = (1, "Continue")


class LogPointType(BaseEnum):
    """What a logged data point records."""

    NONE = (0, "None")
    INPUT = (1, "Input")
    SETPOINT_1 = (2, "Setpoint 1")
    SETPOINT_2 = (3, "Setpoint 2")
    OUTPUT_1 = (4, "Output 1")
    OUTPUT_2 = (5, "Output 2")


class ProgramCommand(BaseEnum):
    """A command of a stored program (the manual's paragraph 8.3)."""

    END = (0, "End")
    NOP = (1, "NOP")
    REPEAT = (2, "Repeat")
    END_REPEAT = (3, "End repeat")
    WAIT = (4, "Wait")
    CALL = (5, "Call")
    RAMP_MOUT_ABSOLUTE = (6, "Ramp manual output, absolute")
    RAMP_MOUT_RELATIVE = (7, "Ramp manual output, relative")
    RAMP_SETPOINT_ABSOLUTE = (8, "Ramp setpoint, absolute")
    RAMP_SETPOINT_RELATIVE = (9, "Ramp setpoint, relative")
    PARAMETERS = (10, "Parameters")
    DIGITAL_OUTPUT = (11, "Digital output")
    RELAYS = (12, "Relays")
    SETTLE = (13, "Settle")


class Lakeshore_340(Instrument):
    """The Lake Shore Model 340 temperature controller.

    It has two control loops, `OutputChannel.OUTPUT_1` (the heater output) and
    `OUTPUT_2` (analog output 2), and inputs A and B, with C and D on an option card.

    Where it does what the Lakeshore 350 does, its methods, their arguments and
    their choices are named as the 350's are, so that code written for one works
    with the other: `set_control_mode(output, ControlMode.OPEN_LOOP)`,
    `set_heater_range`, `set_manual_output`, `get_temperature` and the rest.
    """

    # The enums that the queries and commands take, so that they can be reached
    # from the instrument, as `Lakeshore_340.InputChannel`, without importing them.
    AnalogMode = AnalogMode
    AnalogOutput = AnalogOutput
    AutotuneMode = AutotuneMode
    BaudRate = BaudRate
    Coefficient = Coefficient
    Compensation = Compensation
    ControlMode = ControlMode
    CurveFormat = CurveFormat
    DigitalOutputMode = DigitalOutputMode
    DisplayData = DisplayData
    Excitation = Excitation
    HeaterDisplay = HeaterDisplay
    HeaterRange = HeaterRange
    IeeeTerminator = IeeeTerminator
    InputChannel = InputChannel
    InputData = InputData
    InputRange = InputRange
    LinearEquation = LinearEquation
    LinearOffset = LinearOffset
    LogPointType = LogPointType
    LogStartMode = LogStartMode
    LogType = LogType
    LoopDisplay = LoopDisplay
    MaxCurrent = MaxCurrent
    MinMaxMode = MinMaxMode
    OutputChannel = OutputChannel
    Parity = Parity
    ProgramCommand = ProgramCommand
    Relay = Relay
    RelayMode = RelayMode
    RemoteMode = RemoteMode
    ScanMode = ScanMode
    SensorType = SensorType
    SensorUnits = SensorUnits
    SerialTerminator = SerialTerminator
    State = State
    Units = Units

    def __init__(self, *args, **kwargs):
        """Initializes the Lakeshore 340, and clears its status registers."""
        super().__init__(*args, **kwargs)
        self.clear()

    # ------------------------------------------------------------ common commands
    @mark_query
    def identify(self) -> str:
        """Identifies the instrument.

        Returns:
            str: The manufacturer, model, serial number and firmware date, such as
                `LSCI,MODEL340,123456,040102`.
        """
        return self.query("*IDN?")

    @mark_command
    def reset(self) -> int:
        """Sets the controller's parameters to their power-up settings (`*RST`).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*RST")

    @mark_command
    def clear(self) -> int:
        """Clears the status byte and the standard event status register, and ends
        pending operations (`*CLS`). It doesn't clear the controller's settings.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*CLS")

    @mark_command
    def clear_event_register(self) -> int:
        """Clears the standard event status register, by reading it.

        Returns:
            int: The register's value before it was cleared.
        """
        return self.get_event_status()

    @mark_command
    def set_event_enable(self, value: int) -> int:
        """Sets which events of the standard event status register are reported
        (`*ESE`).

        Args:
            value (int): The sum of the bit weights to enable, 0 to 255: 1 OPC,
                8 DDE, 16 EXE and 128 PON.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"*ESE {int(value)}")

    @mark_query
    def get_event_enable(self) -> int:
        """Queries which events of the standard event status register are reported.

        Returns:
            int: The sum of the bit weights that are enabled.
        """
        return _int(self.query("*ESE?"))

    @mark_query
    def get_event_status(self) -> int:
        """Queries the standard event status register, which clears it (`*ESR?`).

        Returns:
            int: The sum of the bit weights of the events set: 1 OPC, 4 QYE, 8 DDE,
                16 EXE, 32 CME and 128 PON.
        """
        return _int(self.query("*ESR?"))

    @mark_command
    def operation_complete(self) -> int:
        """Sets the OPC event when every pending operation is complete (`*OPC`).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*OPC")

    @mark_query
    def get_operation_complete(self) -> int:
        """Waits until every pending operation is complete (`*OPC?`).

        Returns:
            int: 1, once they are.
        """
        return _int(self.query("*OPC?"))

    @mark_command
    def set_service_request_enable(self, value: int) -> int:
        """Sets which flags of the status byte request service (`*SRE`).

        Args:
            value (int): The sum of the bit weights to enable, 0 to 255: 1 new A&B,
                8 alarm, 16 error and 64 SRQ.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"*SRE {int(value)}")

    @mark_query
    def get_service_request_enable(self) -> int:
        """Queries which flags of the status byte request service.

        Returns:
            int: The sum of the bit weights that are enabled.
        """
        return _int(self.query("*SRE?"))

    @mark_query
    def get_status_byte(self) -> int:
        """Queries the status byte, without clearing it (`*STB?`).

        Returns:
            int: The sum of the bit weights of the flags set: 1 new A&B, 2 new
                option, 4 settle, 8 alarm, 16 error, 32 ESB, 64 SRQ and 128 ramp done.
        """
        return _int(self.query("*STB?"))

    @mark_query
    def self_test(self) -> int:
        """Queries the result of the self-test the 340 runs at power-up (`*TST?`).

        Returns:
            int: 0 if no errors were found, 1 if some were.
        """
        return _int(self.query("*TST?"))

    # ---------------------------------------------------------------------- inputs
    @mark_query
    def get_temperature(self, input_channel: InputChannel) -> float:
        """Queries an input's reading in kelvin (`KRDG?`).

        Args:
            input_channel (InputChannel): The input to read.

        Returns:
            float: The temperature, in kelvin.
        """
        return float(self.query(f"KRDG? {input_channel.raw_value}"))

    @mark_query
    def get_temperature_celsius(self, input_channel: InputChannel) -> float:
        """Queries an input's reading in Celsius (`CRDG?`).

        Args:
            input_channel (InputChannel): The input to read.

        Returns:
            float: The temperature, in °C.
        """
        return float(self.query(f"CRDG? {input_channel.raw_value}"))

    @mark_query
    def get_sensor_reading(self, input_channel: InputChannel) -> float:
        """Queries an input's reading in sensor units (`SRDG?`): volts or ohms.

        Args:
            input_channel (InputChannel): The input to read.

        Returns:
            float: The reading, in the sensor's units.
        """
        return float(self.query(f"SRDG? {input_channel.raw_value}"))

    @mark_query
    def get_reading_status(self, input_channel: InputChannel) -> int:
        """Queries the status of an input's reading (`RDGST?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            int: The sum of the bit weights of the flags set: 1 invalid reading,
                2 old reading, 16 temperature underrange, 32 temperature overrange,
                64 units zero and 128 units overrange. 0 is a good reading.
        """
        return _int(self.query(f"RDGST? {input_channel.raw_value}"))

    @mark_command
    def set_alarm(
        self,
        input_channel: InputChannel,
        state: State,
        high_value: float,
        low_value: float,
        latch: State,
        source: InputData = InputData.KELVIN,
        relay: State = State.OFF,
    ) -> int:
        """Configures an input's alarm (`ALARM`). The first five arguments are the
        Lakeshore 350's, in its order.

        Args:
            input_channel (InputChannel): The input to configure.
            state (State): Whether the alarm is checked.
            high_value (float): The value above which the high alarm is active.
            low_value (float): The value below which the low alarm is active.
            latch (State): Whether the alarm stays active after the condition ends.
            source (InputData): The input's data that is checked.
            relay (State): Whether the alarm may drive the relays (see `set_relay`).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"ALARM {input_channel.raw_value},{state.raw_value},{source.raw_value},"
            f"{_number(high_value)},{_number(low_value)},{latch.raw_value},{relay.raw_value}"
        )

    @mark_query
    def get_alarm(self, input_channel: InputChannel) -> dict:
        """Queries an input's alarm configuration (`ALARM?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `state` (State), `source` (InputData), `high_value` (float),
                `low_value` (float), `latch` (State) and `relay` (State).
        """
        f = _fields(self.query(f"ALARM? {input_channel.raw_value}"))
        return {
            "state": State.from_raw_value(_int(f[0])),
            "source": InputData.from_raw_value(_int(f[1])),
            "high_value": float(f[2]),
            "low_value": float(f[3]),
            "latch": State.from_raw_value(_int(f[4])),
            "relay": State.from_raw_value(_int(f[5])),
        }

    @mark_query
    def get_alarm_status(self, input_channel: InputChannel) -> dict:
        """Queries whether an input's high and low alarms are active (`ALARMST?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `high` (State) and `low` (State).
        """
        f = _fields(self.query(f"ALARMST? {input_channel.raw_value}"))
        return {
            "high": State.from_raw_value(_int(f[0])),
            "low": State.from_raw_value(_int(f[1])),
        }

    @mark_command
    def reset_alarms(self) -> int:
        """Clears the high and low status of every alarm, latched ones included
        (`ALMRST`).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("ALMRST")

    @mark_command
    def set_filter(
        self, input_channel: InputChannel, state: State, points: int, window: int
    ) -> int:
        """Configures an input's reading filter (`FILTER`).

        Args:
            input_channel (InputChannel): The input to configure.
            state (State): Whether the filter is on.
            points (int): How many readings it averages.
            window (int): The change, in percent of full scale, that restarts it.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"FILTER {input_channel.raw_value},{state.raw_value},{int(points)},{int(window)}"
        )

    @mark_query
    def get_filter(self, input_channel: InputChannel) -> dict:
        """Queries an input's reading filter (`FILTER?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `state` (State), `points` (int) and `window` (int, percent).
        """
        f = _fields(self.query(f"FILTER? {input_channel.raw_value}"))
        return {
            "state": State.from_raw_value(_int(f[0])),
            "points": _int(f[1]),
            "window": _int(f[2]),
        }

    @mark_command
    def set_input_curve(self, input_channel: InputChannel, curve: int) -> int:
        """Sets the curve an input uses to convert its reading to temperature
        (`INCRV`).

        Args:
            input_channel (InputChannel): The input to configure.
            curve (int): 0 for none, 1 to 20 for a standard curve, 21 to 60 for a
                user curve. A curve that doesn't suit the input sets 0.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"INCRV {input_channel.raw_value},{int(curve)}")

    @mark_query
    def get_input_curve(self, input_channel: InputChannel) -> int:
        """Queries the curve an input uses (`INCRV?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            int: The curve's number: 0 for none.
        """
        return _int(self.query(f"INCRV? {input_channel.raw_value}"))

    @mark_command
    def set_input_setup(
        self, input_channel: InputChannel, enabled: State, compensation: Compensation
    ) -> int:
        """Configures an input's hardware setup (`INSET`).

        Args:
            input_channel (InputChannel): The input to configure.
            enabled (State): Whether the input is read.
            compensation (Compensation): Thermal compensation, for an NTC resistor or
                a special sensor only.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"INSET {input_channel.raw_value},{enabled.raw_value},{compensation.raw_value}"
        )

    @mark_query
    def get_input_setup(self, input_channel: InputChannel) -> dict:
        """Queries an input's hardware setup (`INSET?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `enabled` (State) and `compensation` (Compensation).
        """
        f = _fields(self.query(f"INSET? {input_channel.raw_value}"))
        return {
            "enabled": State.from_raw_value(_int(f[0])),
            "compensation": Compensation.from_raw_value(_int(f[1])),
        }

    @mark_command
    def set_input_type(
        self, input_channel: InputChannel, sensor_type: SensorType
    ) -> int:
        """Sets an input's sensor type, which sets its units, coefficient, excitation
        and range to the type's own (`INTYPE`).

        Args:
            input_channel (InputChannel): The input to configure.
            sensor_type (SensorType): The sensor.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"INTYPE {input_channel.raw_value},{sensor_type.raw_value}")

    @mark_command
    def set_input_type_special(
        self,
        input_channel: InputChannel,
        units: SensorUnits,
        coefficient: Coefficient,
        excitation: Excitation,
        input_range: InputRange,
    ) -> int:
        """Sets an input to a special sensor, with its units, coefficient, excitation
        and range given (`INTYPE`).

        Args:
            input_channel (InputChannel): The input to configure.
            units (SensorUnits): What the input measures.
            coefficient (Coefficient): Whether the reading falls or rises with
                temperature.
            excitation (Excitation): The excitation.
            input_range (InputRange): The range.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"INTYPE {input_channel.raw_value},{SensorType.SPECIAL.raw_value},"
            f"{units.raw_value},{coefficient.raw_value},{excitation.raw_value},"
            f"{input_range.raw_value}"
        )

    @mark_query
    def get_input_type(self, input_channel: InputChannel) -> dict:
        """Queries an input's sensor type and its parameters (`INTYPE?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `sensor_type` (SensorType), `units` (SensorUnits), `coefficient`
                (Coefficient), `excitation` (Excitation) and `input_range`
                (InputRange).
        """
        f = _fields(self.query(f"INTYPE? {input_channel.raw_value}"))
        return {
            "sensor_type": SensorType.from_raw_value(_int(f[0])),
            "units": SensorUnits.from_raw_value(_int(f[1])),
            "coefficient": Coefficient.from_raw_value(_int(f[2])),
            "excitation": Excitation.from_raw_value(_int(f[3])),
            "input_range": InputRange.from_raw_value(_int(f[4])),
        }

    @mark_command
    def set_linear_equation(
        self,
        input_channel: InputChannel,
        equation: LinearEquation,
        m: float,
        x_source: Units,
        b_source: LinearOffset,
        b: float,
    ) -> int:
        """Configures an input's linear equation, whose result is its linear data
        (`LINEAR`).

        Args:
            input_channel (InputChannel): The input to configure.
            equation (LinearEquation): The equation's form.
            m (float): Its m.
            x_source (Units): The input's data that is x.
            b_source (LinearOffset): Where b comes from. A setpoint needs the same
                units as `x_source`.
            b (float): Its b, when `b_source` is `LinearOffset.VALUE`.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"LINEAR {input_channel.raw_value},{equation.raw_value},{_number(m)},"
            f"{x_source.raw_value},{b_source.raw_value},{_number(b)}"
        )

    @mark_query
    def get_linear_equation(self, input_channel: InputChannel) -> dict:
        """Queries an input's linear equation (`LINEAR?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `equation` (LinearEquation), `m` (float), `x_source` (Units),
                `b_source` (LinearOffset) and `b` (float).
        """
        f = _fields(self.query(f"LINEAR? {input_channel.raw_value}"))
        return {
            "equation": LinearEquation.from_raw_value(_int(f[0])),
            "m": float(f[1]),
            "x_source": Units.from_raw_value(_int(f[2])),
            "b_source": LinearOffset.from_raw_value(_int(f[3])),
            "b": float(f[4]),
        }

    @mark_query
    def get_linear_data(self, input_channel: InputChannel) -> float:
        """Queries an input's linear equation data (`LDAT?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            float: The equation's result.
        """
        return float(self.query(f"LDAT? {input_channel.raw_value}"))

    @mark_query
    def get_linear_data_status(self, input_channel: InputChannel) -> int:
        """Queries the status of an input's linear equation data (`LDATST?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            int: The status flags, as `get_reading_status` gives them.
        """
        return _int(self.query(f"LDATST? {input_channel.raw_value}"))

    @mark_command
    def set_min_max(
        self, input_channel: InputChannel, mode: MinMaxMode, source: InputData
    ) -> int:
        """Configures an input's max/min function (`MNMX`).

        Args:
            input_channel (InputChannel): The input to configure.
            mode (MinMaxMode): Whether it runs or is paused.
            source (InputData): The input's data it follows.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"MNMX {input_channel.raw_value},{mode.raw_value},{source.raw_value}"
        )

    @mark_query
    def get_min_max(self, input_channel: InputChannel) -> dict:
        """Queries an input's max/min function (`MNMX?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `mode` (MinMaxMode) and `source` (InputData).
        """
        f = _fields(self.query(f"MNMX? {input_channel.raw_value}"))
        return {
            "mode": MinMaxMode.from_raw_value(_int(f[0])),
            "source": InputData.from_raw_value(_int(f[1])),
        }

    @mark_query
    def get_min_max_data(self, input_channel: InputChannel) -> dict:
        """Queries the least and greatest data an input has had (`MDAT?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `min` (float) and `max` (float).
        """
        f = _fields(self.query(f"MDAT? {input_channel.raw_value}"))
        return {"min": float(f[0]), "max": float(f[1])}

    @mark_query
    def get_min_max_data_status(self, input_channel: InputChannel) -> dict:
        """Queries the status of an input's max/min data (`MDATST?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `min` (int) and `max` (int), the status flags as
                `get_reading_status` gives them.
        """
        f = _fields(self.query(f"MDATST? {input_channel.raw_value}"))
        return {"min": _int(f[0]), "max": _int(f[1])}

    @mark_command
    def reset_min_max(self) -> int:
        """Resets the max/min data of every input (`MNMXRST`).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("MNMXRST")

    # ----------------------------------------------------------------------- loops
    @mark_command
    def set_control_loop(
        self,
        output_channel: OutputChannel,
        input_channel: InputChannel,
        units: Units,
        state: State,
        powerup: State,
    ) -> int:
        """Configures a control loop (`CSET`).

        Args:
            output_channel (OutputChannel): The loop to configure.
            input_channel (InputChannel): The input it controls from: A or B.
            units (Units): The setpoint's units.
            state (State): Whether the loop is on.
            powerup (State): Whether it is on after the 340 is powered up.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"CSET {output_channel.raw_value},{input_channel.raw_value},"
            f"{units.raw_value},{state.raw_value},{powerup.raw_value}"
        )

    @mark_query
    def get_control_loop(self, output_channel: OutputChannel) -> dict:
        """Queries a control loop's configuration (`CSET?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            dict: `input_channel` (InputChannel), `units` (Units), `state` (State)
                and `powerup` (State).
        """
        f = _fields(self.query(f"CSET? {output_channel.raw_value}"))
        return {
            "input_channel": InputChannel.from_raw_value(f[0]),
            "units": Units.from_raw_value(_int(f[1])),
            "state": State.from_raw_value(_int(f[2])),
            "powerup": State.from_raw_value(_int(f[3])),
        }

    @mark_command
    def set_control_input(
        self, output_channel: OutputChannel, input_channel: InputChannel
    ) -> int:
        """Sets the input a control loop controls from, leaving the rest of its
        configuration as it is (`CSET`, with the rest left out).

        Args:
            output_channel (OutputChannel): The loop to configure.
            input_channel (InputChannel): The input: A or B.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"CSET {output_channel.raw_value},{input_channel.raw_value}"
        )

    @mark_query
    def get_control_input(self, output_channel: OutputChannel) -> InputChannel:
        """Queries the input a control loop controls from (`CSET?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            InputChannel: The input.
        """
        return self.get_control_loop(output_channel)["input_channel"]

    @mark_command
    def set_control_mode(self, output_channel: OutputChannel, mode: ControlMode) -> int:
        """Sets how a control loop works out its output (`CMODE`).

        Args:
            output_channel (OutputChannel): The loop to configure.
            mode (ControlMode): PID, zone, open loop (the manual output alone), or
                an autotuning mode.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CMODE {output_channel.raw_value},{mode.raw_value}")

    @mark_query
    def get_control_mode(self, output_channel: OutputChannel) -> ControlMode:
        """Queries how a control loop works out its output (`CMODE?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            ControlMode: The loop's mode.
        """
        return ControlMode.from_raw_value(
            _int(self.query(f"CMODE? {output_channel.raw_value}"))
        )

    @mark_command
    def set_autotune_pid(self, output: OutputChannel, mode: AutotuneMode) -> int:
        """Starts autotuning a control loop (`CMODE` with an autotuning mode).

        Args:
            output (OutputChannel): The loop to tune.
            mode (AutotuneMode): Which terms are tuned: P, PI or PID.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CMODE {output.raw_value},{mode.raw_value}")

    @mark_query
    def get_tuning(self) -> bool:
        """Queries whether loop 1 is autotuning (`TUNEST?`).

        Returns:
            bool: True if it is.
        """
        return _int(self.query("TUNEST?")) == 1

    @mark_command
    def set_pid(
        self, output_channel: OutputChannel, p: float, i: float, d: float
    ) -> int:
        """Sets a control loop's PID values (`PID`).

        Args:
            output_channel (OutputChannel): The loop to configure.
            p (float): The proportional term.
            i (float): The integral term.
            d (float): The derivative term.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"PID {output_channel.raw_value},{_number(p)},{_number(i)},{_number(d)}"
        )

    @mark_query
    def get_pid(self, output_channel: OutputChannel) -> dict:
        """Queries a control loop's PID values (`PID?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            dict: `p` (float), `i` (float) and `d` (float).
        """
        f = _fields(self.query(f"PID? {output_channel.raw_value}"))
        return {"p": float(f[0]), "i": float(f[1]), "d": float(f[2])}

    @mark_command
    def set_setpoint(self, output_channel: OutputChannel, setpoint: float) -> int:
        """Sets a control loop's setpoint (`SETP`), in the loop's units.

        Args:
            output_channel (OutputChannel): The loop to configure.
            setpoint (float): The setpoint.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SETP {output_channel.raw_value},{_number(setpoint)}")

    @mark_query
    def get_setpoint(self, output_channel: OutputChannel) -> float:
        """Queries a control loop's setpoint (`SETP?`). While it ramps, this is where
        the ramp has got to.

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            float: The setpoint, in the loop's units.
        """
        return float(self.query(f"SETP? {output_channel.raw_value}"))

    @mark_command
    def set_ramp(self, output_channel: OutputChannel, state: State, rate: float) -> int:
        """Configures a control loop's setpoint ramp (`RAMP`): with it on, a new
        setpoint is ramped to at the rate.

        Args:
            output_channel (OutputChannel): The loop to configure.
            state (State): Whether ramping is on.
            rate (float): The rate, in kelvin per minute.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"RAMP {output_channel.raw_value},{state.raw_value},{rate:.3f}"
        )

    @mark_query
    def get_ramp(self, output_channel: OutputChannel) -> float:
        """Queries a control loop's ramp rate (`RAMP?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            float: The rate, in kelvin per minute.
        """
        return float(_fields(self.query(f"RAMP? {output_channel.raw_value}"))[1])

    @mark_query
    def get_ramp_state(self, output_channel: OutputChannel) -> State:
        """Queries whether a control loop's ramp is on (`RAMP?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            State: State.ON if a new setpoint is ramped to.
        """
        f = _fields(self.query(f"RAMP? {output_channel.raw_value}"))
        return State.from_raw_value(_int(f[0]))

    @mark_query
    def get_ramping(self, output_channel: OutputChannel) -> bool:
        """Queries whether a control loop's setpoint is ramping now (`RAMPST?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            bool: True while it ramps.
        """
        return _int(self.query(f"RAMPST? {output_channel.raw_value}")) == 1

    @mark_command
    def set_manual_output(self, output_channel: OutputChannel, percent: float) -> int:
        """Sets a control loop's manual output (`MOUT`), in percent. In open loop
        mode it is the output. Otherwise it is added to the PID's.

        Args:
            output_channel (OutputChannel): The loop to configure.
            percent (float): The output, in percent of the range.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"MOUT {output_channel.raw_value},{percent:.2f}")

    @mark_query
    def get_manual_output(self, output_channel: OutputChannel) -> float:
        """Queries a control loop's manual output (`MOUT?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            float: The manual output, in percent.
        """
        return float(self.query(f"MOUT? {output_channel.raw_value}"))

    def _heater(self, output_channel: OutputChannel) -> None:
        """Refuses a loop with no heater: only loop 1 drives the heater."""
        if output_channel is not OutputChannel.OUTPUT_1:
            raise ValueError(
                f"The 340's heater is on {OutputChannel.OUTPUT_1.name}: "
                f"{output_channel.name} drives analog output 2"
            )

    @mark_command
    def set_heater_range(
        self, output_channel: OutputChannel, heater_range: HeaterRange
    ) -> int:
        """Sets the heater's range (`RANGE`). `HeaterRange.OFF` turns it off.

        Args:
            output_channel (OutputChannel): The loop whose heater it is:
                `OUTPUT_1`, the only one with a heater. The 350 takes the output
                in the same place.
            heater_range (HeaterRange): The range.

        Returns:
            int: Status code indicating the success of the operation.

        Raises:
            ValueError: For loop 2, which has no heater.
        """
        self._heater(output_channel)
        return self.command(f"RANGE {heater_range.raw_value}")

    @mark_query
    def get_heater_range(self, output_channel: OutputChannel) -> HeaterRange:
        """Queries the heater's range (`RANGE?`).

        Args:
            output_channel (OutputChannel): `OUTPUT_1`, the only loop with a heater.

        Returns:
            HeaterRange: The range. `HeaterRange.OFF` if the heater is off.

        Raises:
            ValueError: For loop 2, which has no heater.
        """
        self._heater(output_channel)
        return HeaterRange.from_raw_value(_int(self.query("RANGE?")))

    @mark_query
    def get_heater_output(self, output_channel: OutputChannel) -> float:
        """Queries a loop's output, in percent: the heater's for loop 1 (`HTR?`),
        and analog output 2's for loop 2 (`AOUT? 2`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            float: The output, in percent.
        """
        if output_channel is OutputChannel.OUTPUT_2:
            return float(self.query("AOUT? 2"))
        return float(self.query("HTR?"))

    @mark_query
    def get_heater_status(self, output_channel: OutputChannel) -> int:
        """Queries the heater's error code (`HTRST?`).

        Args:
            output_channel (OutputChannel): `OUTPUT_1`, the only loop with a heater.

        Returns:
            int: 0 if there is no error. Otherwise the code, which the manual's
                paragraph 11.8 explains.

        Raises:
            ValueError: For loop 2, which has no heater.
        """
        self._heater(output_channel)
        return _int(self.query("HTRST?"))

    @mark_command
    def set_control_limits(
        self,
        output_channel: OutputChannel,
        setpoint_limit: float,
        positive_slope: float,
        negative_slope: float,
        max_current: MaxCurrent,
        max_range: HeaterRange,
    ) -> int:
        """Configures a control loop's limits (`CLIMIT`).

        Args:
            output_channel (OutputChannel): The loop to configure.
            setpoint_limit (float): The highest setpoint, and the reading at which
                the output is turned off, in the setpoint's units.
            positive_slope (float): The most the output rises in one step, in
                percent. 0 for no limit.
            negative_slope (float): The most the output falls in one step, in
                percent. 0 for no limit.
            max_current (MaxCurrent): The most current the loop 1 heater output
                gives.
            max_range (HeaterRange): The highest heater range loop 1 may use.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"CLIMIT {output_channel.raw_value},{_number(setpoint_limit)},"
            f"{_number(positive_slope)},{_number(negative_slope)},"
            f"{max_current.raw_value},{max_range.raw_value}"
        )

    @mark_query
    def get_control_limits(self, output_channel: OutputChannel) -> dict:
        """Queries a control loop's limits (`CLIMIT?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            dict: `setpoint_limit` (float), `positive_slope` (float),
                `negative_slope` (float), `max_current` (MaxCurrent) and
                `max_range` (HeaterRange).
        """
        f = _fields(self.query(f"CLIMIT? {output_channel.raw_value}"))
        return {
            "setpoint_limit": float(f[0]),
            "positive_slope": float(f[1]),
            "negative_slope": float(f[2]),
            "max_current": MaxCurrent.from_raw_value(_int(f[3])),
            "max_range": HeaterRange.from_raw_value(_int(f[4])),
        }

    @mark_command
    def set_max_user_current(self, current: float) -> int:
        """Sets the most current the loop 1 heater output gives when its maximum
        current is `MaxCurrent.USER` (`CLIMI`). Needs firmware 01.03.08 or later.

        Args:
            current (float): The current, in amps: 0.1 to 2.0.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CLIMI {current:.3f}")

    @mark_query
    def get_max_user_current(self) -> float:
        """Queries the user maximum current of the loop 1 heater output (`CLIMI?`).
        Needs firmware 01.03.08 or later.

        Returns:
            float: The current, in amps.
        """
        return float(self.query("CLIMI?"))

    @mark_command
    def set_control_filter(self, output_channel: OutputChannel, state: State) -> int:
        """Turns a control loop's filter on or off (`CFILT`). It filters as the
        loop's input does.

        Args:
            output_channel (OutputChannel): The loop to configure.
            state (State): Whether the filter is on.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CFILT {output_channel.raw_value},{state.raw_value}")

    @mark_query
    def get_control_filter(self, output_channel: OutputChannel) -> State:
        """Queries whether a control loop's filter is on (`CFILT?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            State: State.ON if it is.
        """
        return State.from_raw_value(
            _int(self.query(f"CFILT? {output_channel.raw_value}"))
        )

    @mark_command
    def set_settle(self, threshold: float, seconds: int) -> int:
        """Sets when loop 1 counts as settled, for the status byte's settle flag
        (`SETTLE`).

        Args:
            threshold (float): The band around the setpoint the reading must stay
                in: 0 to 100.
            seconds (int): How long it must stay there: 0 to 86400.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SETTLE {_number(threshold)},{int(seconds)}")

    @mark_query
    def get_settle(self) -> dict:
        """Queries when loop 1 counts as settled (`SETTLE?`).

        Returns:
            dict: `threshold` (float) and `seconds` (int).
        """
        f = _fields(self.query("SETTLE?"))
        return {"threshold": float(f[0]), "seconds": _int(f[1])}

    @mark_command
    def set_zone(
        self,
        output_channel: OutputChannel,
        zone: int,
        top: float,
        p: float,
        i: float,
        d: float,
        manual_output: float,
        heater_range: HeaterRange,
    ) -> int:
        """Configures a zone of a control loop's zone table (`ZONE`), which zone mode
        uses.

        Args:
            output_channel (OutputChannel): The loop to configure.
            zone (int): The zone: 1 to 10.
            top (float): The zone's top temperature.
            p (float): The proportional term in the zone.
            i (float): The integral term in the zone.
            d (float): The derivative term in the zone.
            manual_output (float): The manual output in the zone, in percent.
            heater_range (HeaterRange): The heater range in the zone, for loop 1.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"ZONE {output_channel.raw_value},{int(zone)},{_number(top)},"
            f"{_number(p)},{_number(i)},{_number(d)},{manual_output:.2f},"
            f"{heater_range.raw_value}"
        )

    @mark_query
    def get_zone(self, output_channel: OutputChannel, zone: int) -> dict:
        """Queries a zone of a control loop's zone table (`ZONE?`).

        Args:
            output_channel (OutputChannel): The loop to query.
            zone (int): The zone: 1 to 10.

        Returns:
            dict: `top` (float), `p` (float), `i` (float), `d` (float),
                `manual_output` (float) and `heater_range` (HeaterRange).
        """
        f = _fields(self.query(f"ZONE? {output_channel.raw_value},{int(zone)}"))
        return {
            "top": float(f[0]),
            "p": float(f[1]),
            "i": float(f[2]),
            "d": float(f[3]),
            "manual_output": float(f[4]),
            "heater_range": HeaterRange.from_raw_value(_int(f[5])),
        }

    @mark_command
    def set_control_display(
        self,
        output_channel: OutputChannel,
        loops_shown: LoopDisplay,
        resistance: int,
        heater_display: HeaterDisplay,
        large_output: State,
    ) -> int:
        """Configures the control loop part of the display (`CDISP`).

        Args:
            output_channel (OutputChannel): The loop to configure.
            loops_shown (LoopDisplay): Which loops are shown.
            resistance (int): The heater's resistance, in ohms (1 to 1000), for
                the power shown.
            heater_display (HeaterDisplay): Whether the output shows as a current or
                a power.
            large_output (State): Whether the output is shown in large numbers.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"CDISP {output_channel.raw_value},{loops_shown.raw_value},"
            f"{int(resistance)},{heater_display.raw_value},{large_output.raw_value}"
        )

    @mark_query
    def get_control_display(self, output_channel: OutputChannel) -> dict:
        """Queries the control loop part of the display (`CDISP?`).

        Args:
            output_channel (OutputChannel): The loop to query.

        Returns:
            dict: `loops_shown` (LoopDisplay), `resistance` (int),
                `heater_display` (HeaterDisplay) and `large_output` (State).
        """
        f = _fields(self.query(f"CDISP? {output_channel.raw_value}"))
        return {
            "loops_shown": LoopDisplay.from_raw_value(_int(f[0])),
            "resistance": _int(f[1]),
            "heater_display": HeaterDisplay.from_raw_value(_int(f[2])),
            "large_output": State.from_raw_value(_int(f[3])),
        }

    # -------------------------------------------------------------- analog outputs
    @mark_command
    def set_analog_output_setup(
        self,
        output: AnalogOutput,
        input_channel: InputChannel,
        source: InputData,
        high_value: float,
        low_value: float,
        bipolar: State,
        mode: AnalogMode = AnalogMode.INPUT,
        manual_value: float = 0.0,
    ) -> int:
        """Configures an analog output (`ANALOG`). The first six arguments are the
        Lakeshore 350's, in its order.

        Args:
            output (AnalogOutput): The output to configure.
            input_channel (InputChannel): The input it follows, in input mode.
            source (InputData): The input's data it follows, in input mode.
            high_value (float): The data at +100 % output, in input mode.
            low_value (float): The data at -100 % output (bipolar) or 0 %, in input
                mode.
            bipolar (State): Whether it is bipolar, or positive only.
            mode (AnalogMode): What it follows. `AnalogMode.LOOP` is for analog
                output 2 only.
            manual_value (float): The output, in percent, in manual mode.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"ANALOG {output.raw_value},{bipolar.raw_value},{mode.raw_value},"
            f"{input_channel.raw_value},{source.raw_value},{_number(high_value)},"
            f"{_number(low_value)},{manual_value:.1f}"
        )

    @mark_query
    def get_analog_output_setup(self, output: AnalogOutput) -> dict:
        """Queries an analog output's configuration (`ANALOG?`).

        Args:
            output (AnalogOutput): The output to query.

        Returns:
            dict: `bipolar` (State), `mode` (AnalogMode), `input_channel`
                (InputChannel, or None if none is set), `source` (InputData),
                `high_value` (float), `low_value` (float) and `manual_value`
                (float).
        """
        f = _fields(self.query(f"ANALOG? {output.raw_value}"))
        channel = f[2][:1]
        return {
            "bipolar": State.from_raw_value(_int(f[0])),
            "mode": AnalogMode.from_raw_value(_int(f[1])),
            "input_channel": InputChannel.from_raw_value(channel) if channel else None,
            "source": InputData.from_raw_value(_int(f[3])),
            "high_value": float(f[4]),
            "low_value": float(f[5]),
            "manual_value": float(f[6]),
        }

    @mark_query
    def get_analog_output(self, output: AnalogOutput) -> float:
        """Queries an analog output's value (`AOUT?`).

        Args:
            output (AnalogOutput): The output to query.

        Returns:
            float: The output, in percent.
        """
        return float(self.query(f"AOUT? {output.raw_value}"))

    # ---------------------------------------------------------- relays and digital
    @mark_command
    def set_relay(self, relay: Relay, mode: RelayMode, state: State) -> int:
        """Configures a relay (`RELAY`).

        Args:
            relay (Relay): The relay to configure.
            mode (RelayMode): What drives it.
            state (State): Whether it is on, in manual mode.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"RELAY {relay.raw_value},{mode.raw_value},{state.raw_value}"
        )

    @mark_query
    def get_relay(self, relay: Relay) -> dict:
        """Queries a relay's configuration (`RELAY?`).

        Args:
            relay (Relay): The relay to query.

        Returns:
            dict: `mode` (RelayMode) and `state` (State), its manual setting.
        """
        f = _fields(self.query(f"RELAY? {relay.raw_value}"))
        return {
            "mode": RelayMode.from_raw_value(_int(f[0])),
            "state": State.from_raw_value(_int(f[1])),
        }

    @mark_query
    def get_relay_status(self, relay: Relay) -> State:
        """Queries whether a relay is on now (`RELAYST?`).

        Args:
            relay (Relay): The relay to query.

        Returns:
            State: State.ON if it is.
        """
        return State.from_raw_value(_int(self.query(f"RELAYST? {relay.raw_value}")))

    @mark_command
    def set_digital_output(self, mode: DigitalOutputMode, bits: int) -> int:
        """Configures the digital outputs (`DOUT`).

        Args:
            mode (DigitalOutputMode): What drives them.
            bits (int): In manual mode, the sum of the bit weights of the outputs
                that are high: 1 for D1, 2 for D2, and so on.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"DOUT {mode.raw_value},{int(bits)}")

    @mark_query
    def get_digital_output(self) -> dict:
        """Queries the digital outputs' configuration (`DOUT?`).

        Returns:
            dict: `mode` (DigitalOutputMode) and `bits` (int).
        """
        f = _fields(self.query("DOUT?"))
        return {
            "mode": DigitalOutputMode.from_raw_value(_int(f[0])),
            "bits": _int(f[1]),
        }

    @mark_query
    def get_digital_io_status(self) -> dict:
        """Queries the digital inputs and outputs (`DIOST?`).

        Returns:
            dict: `inputs` (int) and `outputs` (int), each the sum of the bit
                weights of the lines that are high.
        """
        f = _fields(self.query("DIOST?"))
        return {"inputs": _int(f[0]), "outputs": _int(f[1])}

    # --------------------------------------------------------------------- display
    @mark_command
    def set_display(self, fields: int, contrast: int, backlight: State) -> int:
        """Configures the main display (`DISPLAY`).

        Args:
            fields (int): How many input fields are shown.
            contrast (int): The contrast, in percent.
            backlight (State): Whether the backlight is on.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"DISPLAY {int(fields)},{int(contrast)},{backlight.raw_value}"
        )

    @mark_query
    def get_display(self) -> dict:
        """Queries the main display's configuration (`DISPLAY?`).

        Returns:
            dict: `fields` (int), `contrast` (int, percent) and `backlight` (State).
        """
        f = _fields(self.query("DISPLAY?"))
        return {
            "fields": _int(f[0]),
            "contrast": _int(f[1]),
            "backlight": State.from_raw_value(_int(f[2])),
        }

    @mark_command
    def set_display_contrast(self, contrast: int) -> int:
        """Sets the display's contrast, leaving the rest of it as it is (`DISPLAY`,
        with the number of fields left blank, as the manual allows for an optional
        parameter).

        Args:
            contrast (int): The contrast, in percent.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"DISPLAY ,{int(contrast)}")

    @mark_query
    def get_display_contrast(self) -> int:
        """Queries the display's contrast (`DISPLAY?`).

        Returns:
            int: The contrast, in percent.
        """
        return self.get_display()["contrast"]

    @mark_command
    def set_display_field(
        self, field: int, input_channel: InputChannel, source: DisplayData
    ) -> int:
        """Sets what a field of the display shows (`DISPFLD`).

        The manual's input line and example spell the command `DSPFLD`, and its
        heading, index and query `DISPFLD`, which is what is sent here.

        Args:
            field (int): The field: 1 to 8.
            input_channel (InputChannel): The input it shows.
            source (DisplayData): The input's data it shows.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"DISPFLD {int(field)},{input_channel.raw_value},{source.raw_value}"
        )

    @mark_query
    def get_display_field(self, field: int) -> dict:
        """Queries what a field of the display shows (`DISPFLD?`).

        Args:
            field (int): The field: 1 to 8.

        Returns:
            dict: `input_channel` (InputChannel, or None if none is set) and
                `source` (DisplayData).
        """
        f = _fields(self.query(f"DISPFLD? {int(field)}"))
        channel = f[0][:1]
        return {
            "input_channel": InputChannel.from_raw_value(channel) if channel else None,
            "source": DisplayData.from_raw_value(_int(f[1])),
        }

    # ------------------------------------------------------ front panel and beeper
    @mark_command
    def set_beeper(self, state: State) -> int:
        """Turns the alarm beeper on or off (`BEEP`).

        Args:
            state (State): Whether an alarm sounds the beeper.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"BEEP {state.raw_value}")

    @mark_query
    def get_beeper(self) -> State:
        """Queries whether the alarm beeper is on (`BEEP?`).

        Returns:
            State: State.ON if an alarm sounds it.
        """
        return State.from_raw_value(_int(self.query("BEEP?")))

    @mark_query
    def get_beeper_status(self) -> State:
        """Queries whether the beeper is sounding now (`BEEPST?`).

        Returns:
            State: State.ON if it is.
        """
        return State.from_raw_value(_int(self.query("BEEPST?")))

    @mark_query
    def get_key_pressed(self) -> bool:
        """Queries whether a key was pressed since the last time this was asked
        (`KEYST?`). It is True after the 340 is powered up.

        Returns:
            bool: True if one was.
        """
        return _int(self.query("KEYST?")) == 1

    @mark_command
    def set_lockout(self, state: State, code: int) -> int:
        """Locks or unlocks the keypad (`LOCK`).

        Args:
            state (State): Whether the keypad is locked.
            code (int): The code that unlocks it at the front panel: 0 to 999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"LOCK {state.raw_value},{int(code):03d}")

    @mark_query
    def get_lockout(self) -> dict:
        """Queries whether the keypad is locked, and its code (`LOCK?`).

        Returns:
            dict: `state` (State) and `code` (int).
        """
        f = _fields(self.query("LOCK?"))
        return {"state": State.from_raw_value(_int(f[0])), "code": _int(f[1])}

    @mark_command
    def set_remote_mode(self, mode: RemoteMode) -> int:
        """Sets whether the front panel or the interface is in control (`MODE`).

        Args:
            mode (RemoteMode): Local, remote, or remote with the front panel locked
                out.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"MODE {mode.raw_value}")

    @mark_query
    def get_remote_mode(self) -> RemoteMode:
        """Queries whether the front panel or the interface is in control (`MODE?`).

        Returns:
            RemoteMode: The mode.
        """
        return RemoteMode.from_raw_value(_int(self.query("MODE?")))

    # ------------------------------------------------------------------ interfaces
    @mark_command
    def set_serial_interface(
        self, terminator: SerialTerminator, baud_rate: BaudRate, parity: Parity
    ) -> int:
        """Configures the serial interface (`COMM`). It takes effect after the next
        terminator, so a connection over it must change to match.

        Args:
            terminator (SerialTerminator): What ends a message.
            baud_rate (BaudRate): The speed.
            parity (Parity): The data bits, stop bits and parity.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"COMM {terminator.raw_value},{baud_rate.raw_value},{parity.raw_value}"
        )

    @mark_query
    def get_serial_interface(self) -> dict:
        """Queries the serial interface's configuration (`COMM?`).

        Returns:
            dict: `terminator` (SerialTerminator), `baud_rate` (BaudRate) and
                `parity` (Parity).
        """
        f = _fields(self.query("COMM?"))
        return {
            "terminator": SerialTerminator.from_raw_value(_int(f[0])),
            "baud_rate": BaudRate.from_raw_value(_int(f[1])),
            "parity": Parity.from_raw_value(_int(f[2])),
        }

    @mark_command
    def set_ieee_interface(
        self,
        address: int,
        terminator: IeeeTerminator = IeeeTerminator.CR_LF,
        eoi: State = State.ON,
    ) -> int:
        """Configures the IEEE-488 interface (`IEEE`). It takes effect after the next
        terminator, so a connection over it must change to match. The address comes
        first, as the Lakeshore 350 takes it alone.

        Args:
            address (int): The GPIB address.
            terminator (IeeeTerminator): What ends a message.
            eoi (State): Whether EOI is asserted.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"IEEE {terminator.raw_value},{eoi.raw_value},{int(address)}"
        )

    @mark_query
    def get_ieee_interface(self) -> dict:
        """Queries the IEEE-488 interface's configuration (`IEEE?`).

        Returns:
            dict: `terminator` (IeeeTerminator), `eoi` (State) and `address` (int).
        """
        f = _fields(self.query("IEEE?"))
        return {
            "terminator": IeeeTerminator.from_raw_value(_int(f[0])),
            "eoi": State.from_raw_value(_int(f[1])),
            "address": _int(f[2]),
        }

    @mark_command
    def set_scanner(self, mode: ScanMode, channel: int, interval: int) -> int:
        """Configures an external scanner (`XSCAN`).

        Args:
            mode (ScanMode): How the scanner is used.
            channel (int): The scanned input used in manual mode: 1 to 16.
            interval (int): The seconds between inputs in autoscan mode: 0 to 999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"XSCAN {mode.raw_value},{int(channel)},{int(interval)}")

    @mark_query
    def get_scanner(self) -> dict:
        """Queries the external scanner's configuration (`XSCAN?`).

        Returns:
            dict: `mode` (ScanMode), `channel` (int) and `interval` (int, seconds).
        """
        f = _fields(self.query("XSCAN?"))
        return {
            "mode": ScanMode.from_raw_value(_int(f[0])),
            "channel": _int(f[1]),
            "interval": _int(f[2]),
        }

    # ---------------------------------------------------------------------- system
    @mark_query
    def get_busy(self) -> bool:
        """Queries whether the 340 is busy with a long operation, such as saving
        curves or making a SoftCal curve (`BUSY?`).

        Returns:
            bool: True while it is.
        """
        return _int(self.query("BUSY?")) == 1

    @mark_command
    def set_date_time(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int,
        second: int,
        millisecond: int = 0,
    ) -> int:
        """Sets the date and time, in 24-hour form (`DATETIME`).

        Args:
            year (int): The year.
            month (int): The month: 1 to 12.
            day (int): The day: 1 to 31.
            hour (int): The hour: 0 to 23.
            minute (int): The minute: 0 to 59.
            second (int): The second: 0 to 59.
            millisecond (int): The millisecond: 0 to 999, kept to 10 ms.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"DATETIME {int(month)},{int(day)},{int(year)},{int(hour)},"
            f"{int(minute)},{int(second)},{int(millisecond)}"
        )

    @mark_query
    def get_date_time(self) -> datetime:
        """Queries the date and time (`DATETIME?`).

        Returns:
            datetime: The 340's date and time.
        """
        month, day, year, hour, minute, second, ms = (
            _int(f) for f in _fields(self.query("DATETIME?"))
        )
        return datetime(year, month, day, hour, minute, second, ms * 1000)

    @mark_query
    def get_revision(self) -> dict:
        """Queries the firmware and hardware revisions (`REV?`).

        Returns:
            dict: `master_date`, `master_revision`, `master_serial`, `switch_sw1`,
                `input_date`, `input_revision`, `option_id`, `option_date` and
                `option_revision`, each as text.
        """
        keys = (
            "master_date",
            "master_revision",
            "master_serial",
            "switch_sw1",
            "input_date",
            "input_revision",
            "option_id",
            "option_date",
            "option_revision",
        )
        return dict(zip(keys, _fields(self.query("REV?"))))

    @mark_command
    def reset_to_factory_defaults(self) -> int:
        """Sets every setting to its factory default, and resets the 340
        (`DFLT 99`). It takes a while: `get_busy` says when it is done.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("DFLT 99")

    # ---------------------------------------------------------------------- curves
    @mark_command
    def set_curve_header(
        self,
        curve_index: int,
        name: str,
        serial_no: str,
        curve_format: CurveFormat,
        upper_limit: float,
        coefficient: Coefficient,
    ) -> int:
        """Sets a user curve's header (`CRVHDR`). `save_curves` keeps it after the
        340 is powered off.

        Args:
            curve_index (int): The curve: 21 to 60.
            name (str): Its name, up to 15 characters.
            serial_no (str): Its serial number, up to 10 characters.
            curve_format (CurveFormat): What its points pair with temperature.
            upper_limit (float): Its upper temperature limit, in kelvin.
            coefficient (Coefficient): Whether its reading falls or rises with
                temperature.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"CRVHDR {int(curve_index)},{name},{serial_no},{curve_format.raw_value},"
            f"{_number(upper_limit)},{coefficient.raw_value}"
        )

    @mark_query
    def get_curve_header(self, curve_index: int) -> dict:
        """Queries a curve's header (`CRVHDR?`).

        Args:
            curve_index (int): The curve: 1 to 60.

        Returns:
            dict: `name` (str), `serial_no` (str), `curve_format` (CurveFormat),
                `upper_limit` (float) and `coefficient` (Coefficient).
        """
        f = _fields(self.query(f"CRVHDR? {int(curve_index)}"))
        return {
            "name": f[0],
            "serial_no": f[1],
            "curve_format": CurveFormat.from_raw_value(_int(f[2])),
            "upper_limit": float(f[3]),
            "coefficient": Coefficient.from_raw_value(_int(f[4])),
        }

    @mark_command
    def set_curve_point(
        self, curve_index: int, point_index: int, sensor: float, temperature: float
    ) -> int:
        """Sets a point of a user curve (`CRVPT`). `save_curves` keeps it after the
        340 is powered off.

        Args:
            curve_index (int): The curve: 21 to 60.
            point_index (int): The point: 1 to 200.
            sensor (float): The sensor reading, in its units.
            temperature (float): The temperature, in kelvin.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"CRVPT {int(curve_index)},{int(point_index)},{_number(sensor)},"
            f"{_number(temperature)}"
        )

    @mark_query
    def get_curve_point(self, curve_index: int, point_index: int) -> dict:
        """Queries a point of a curve (`CRVPT?`).

        Args:
            curve_index (int): The curve: 1 to 60.
            point_index (int): The point: 1 to 200.

        Returns:
            dict: `sensor` (float) and `temperature` (float, kelvin).
        """
        f = _fields(self.query(f"CRVPT? {int(curve_index)},{int(point_index)}"))
        return {"sensor": float(f[0]), "temperature": float(f[1])}

    @mark_command
    def delete_curve(self, curve_index: int) -> int:
        """Deletes a user curve (`CRVDEL`). `save_curves` makes it permanent.

        Args:
            curve_index (int): The curve: 21 to 60.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CRVDEL {int(curve_index)}")

    @mark_command
    def save_curves(self) -> int:
        """Saves the user curves to flash, to keep them after the 340 is powered off
        (`CRVSAV`). It takes several seconds: `get_busy` says when it is done.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("CRVSAV")

    @mark_command
    def generate_softcal(
        self,
        standard_curve: int,
        user_curve: int,
        serial_no: str,
        t1: float,
        u1: float,
        t2: float,
        u2: float,
        t3: float | None = None,
        u3: float | None = None,
    ) -> int:
        """Makes a SoftCal curve from a standard curve and two or three calibration
        points (`SCAL`). `get_busy` says when it is done, and `save_curves` keeps it.

        Args:
            standard_curve (int): The standard curve to start from: 1 to 20.
            user_curve (int): The user curve to write: 21 to 60.
            serial_no (str): The curve's serial number, up to 10 characters.
            t1 (float): The first point's temperature, in kelvin.
            u1 (float): The first point's sensor reading.
            t2 (float): The second point's temperature.
            u2 (float): The second point's sensor reading.
            t3 (float | None): The third point's temperature, if there is one.
            u3 (float | None): The third point's sensor reading, if there is one.

        Returns:
            int: Status code indicating the success of the operation.
        """
        points = [t1, u1, t2, u2] + (
            [t3, u3] if t3 is not None and u3 is not None else []
        )
        return self.command(
            f"SCAL {int(standard_curve)},{int(user_curve)},{serial_no},"
            + ",".join(_number(p) for p in points)
        )

    # -------------------------------------------------------------------- programs
    @mark_command
    def add_program_line(
        self, program: int, command: ProgramCommand, parameters: str = ""
    ) -> int:
        """Adds a line to the end of a stored program (`PGM`).

        Args:
            program (int): The program: 1 to 10.
            command (ProgramCommand): The line's command.
            parameters (str): Its parameters, comma separated, as the manual's
                paragraph 8.3 gives them for the command, such as `"2"` for a call
                to program 2.

        Returns:
            int: Status code indicating the success of the operation.
        """
        text = f"PGM {int(program)},{command.raw_value}"
        return self.command(f"{text},{parameters}" if parameters else text)

    @mark_query
    def get_program_line(self, program: int, line: int) -> str:
        """Queries a line of a stored program (`PGM?`). Past the end, the line is an
        End command.

        Args:
            program (int): The program: 1 to 10.
            line (int): The line.

        Returns:
            str: The line's command and parameters, as the 340 gives them.
        """
        return self.query(f"PGM? {int(program)},{int(line)}").strip()

    @mark_command
    def delete_program(self, program: int) -> int:
        """Erases a stored program (`PGMDEL`).

        Args:
            program (int): The program: 1 to 10.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"PGMDEL {int(program)}")

    @mark_query
    def get_program_memory(self) -> int:
        """Queries how many program lines are left in memory (`PGMMEM?`).

        Returns:
            int: The lines left.
        """
        return _int(self.query("PGMMEM?"))

    @mark_command
    def run_program(self, program: int) -> int:
        """Runs a stored program (`PGMRUN`).

        Args:
            program (int): The program: 1 to 10.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"PGMRUN {int(program)}")

    @mark_command
    def stop_program(self) -> int:
        """Stops the program that is running (`PGMRUN 0`).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("PGMRUN 0")

    @mark_query
    def get_program_status(self) -> dict:
        """Queries which program is running, and its status (`PGMRUN?`).

        Returns:
            dict: `program` (int, 0 if none is running) and `status` (int): 0 no
                errors, 1 too many Call commands, 2 too many Repeat commands, 3 too
                many End Repeat commands, 4 the control channel's setpoint isn't in
                temperature.
        """
        f = _fields(self.query("PGMRUN?"))
        return {"program": _int(f[0]), "status": _int(f[1])}

    # ---------------------------------------------------------------- data logging
    @mark_command
    def set_logging(self, state: State) -> int:
        """Starts or stops data logging to the data card (`LOG`).

        Args:
            state (State): State.ON to start, State.OFF to stop.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"LOG {state.raw_value}")

    @mark_query
    def get_logging(self) -> State:
        """Queries whether data logging is in progress (`LOG?`).

        Returns:
            State: State.ON if it is.
        """
        return State.from_raw_value(_int(self.query("LOG?")))

    @mark_query
    def get_log_count(self) -> int:
        """Queries how many records have been logged (`LOGCNT?`).

        Returns:
            int: The number of records.
        """
        return _int(self.query("LOGCNT?"))

    @mark_command
    def set_log_setup(
        self,
        log_type: LogType,
        interval: int,
        overwrite: State,
        start_mode: LogStartMode,
    ) -> int:
        """Configures data logging (`LOGSET`).

        Args:
            log_type (LogType): Whether `interval` counts readings or seconds.
            interval (int): The readings or seconds between records: 1 to 3600.
            overwrite (State): Whether the oldest records are overwritten when the
                card is full.
            start_mode (LogStartMode): Whether starting clears the log or continues
                it.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"LOGSET {log_type.raw_value},{int(interval)},{overwrite.raw_value},"
            f"{start_mode.raw_value}"
        )

    @mark_query
    def get_log_setup(self) -> dict:
        """Queries data logging's configuration (`LOGSET?`). With no data card it is
        all zeros, and `log_type` is None.

        Returns:
            dict: `log_type` (LogType or None), `interval` (int), `overwrite`
                (State) and `start_mode` (LogStartMode).
        """
        f = [_int(x) for x in _fields(self.query("LOGSET?"))]
        return {
            "log_type": LogType.from_raw_value(f[0]) if f[0] else None,
            "interval": f[1],
            "overwrite": State.from_raw_value(f[2]),
            "start_mode": LogStartMode.from_raw_value(f[3]),
        }

    @mark_command
    def set_log_point(
        self,
        point: int,
        point_type: LogPointType,
        input_channel: InputChannel,
        source: DisplayData,
    ) -> int:
        """Configures a data point that is logged (`LOGPNT`).

        Args:
            point (int): The point: 1 to 4.
            point_type (LogPointType): What it records.
            input_channel (InputChannel): The input, when it records an input.
            source (DisplayData): The input's data, when it records an input.

        Returns:
            int: Status code indicating the success of the operation.
        """
        text = f"LOGPNT {int(point)},{point_type.raw_value}"
        if point_type is LogPointType.INPUT:
            text += f",{input_channel.raw_value},{source.raw_value}"
        return self.command(text)

    @mark_query
    def get_log_point(self, point: int) -> dict:
        """Queries a data point that is logged (`LOGPNT?`).

        Args:
            point (int): The point: 1 to 4.

        Returns:
            dict: `point_type` (LogPointType), and for an input `input_channel`
                (InputChannel) and `source` (DisplayData), otherwise None.
        """
        f = _fields(self.query(f"LOGPNT? {int(point)}"))
        point_type = LogPointType.from_raw_value(_int(f[0]))
        is_input = point_type is LogPointType.INPUT and len(f) >= 3
        return {
            "point_type": point_type,
            "input_channel": InputChannel.from_raw_value(f[1][:1])
            if is_input
            else None,
            "source": DisplayData.from_raw_value(_int(f[2])) if is_input else None,
        }

    @mark_query
    def get_log_record(self, record: int, point: int) -> str:
        """Queries a point of a logged record (`LOGVIEW?`). Its form depends on the
        point's type, as the manual gives it: a date and time, then the data.

        Args:
            record (int): The record: 1 to `get_log_count()`.
            point (int): The point: 1 to 4.

        Returns:
            str: The record's point, as the 340 gives it.
        """
        return self.query(f"LOGVIEW? {int(record)},{int(point)}").strip()
