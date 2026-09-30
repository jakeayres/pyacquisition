"""The Lake Shore Model 350 temperature controller.

Every command in the manual's command summary (table 6-6) is here. The inputs D2
to D5 of the 3062 option card aren't offered as `InputChannel` members yet.

Where the 350 and the 340 do the same thing, the two drivers have the same method,
the same arguments and the same enum member names, so that code written for one
works with the other: `get_temperature`, `set_setpoint`, `set_ramp`, `set_pid`,
`set_manual_output`, `set_heater_range`, `get_heater_output`, `set_control_mode`
(`ControlMode.PID`, `ZONE`, `OPEN_LOOP`), `set_control_input`, the curves, the
alarms, the filter and the rest.
"""

from ...core.instrument import BaseEnum, Instrument, mark_command, mark_query


def _number(value: float) -> str:
    """A number as the 350 takes it: up to six significant figures."""
    return f"{value:.6g}"


def _fields(reply: str) -> list[str]:
    """A reply's comma-separated fields, stripped of spaces and quotes."""
    return [field.strip().strip('"').strip() for field in reply.split(",")]


def _int(text: str) -> int:
    """A whole number from a reply, which may be written as `1` or `1.0`."""
    return int(float(text))


def _quoted(text: str) -> str:
    """Text in quotes, so that the 350 takes its spaces and commas as part of it."""
    return '"' + text.replace('"', "") + '"'


class State(BaseEnum):
    OFF = (0, "Off")
    ON = (1, "On")


class InputChannel(BaseEnum):
    """A sensor input."""

    INPUT_A = ("A", "Input A")
    INPUT_B = ("B", "Input B")
    INPUT_C = ("C", "Input C")
    INPUT_D = ("D", "Input D")


# Some commands number the inputs, rather than letter them: 0 is none.
_INPUT_NUMBERS = {channel: number for number, channel in enumerate(InputChannel, 1)}


def _input_number(input_channel: InputChannel | None) -> int:
    return 0 if input_channel is None else _INPUT_NUMBERS[input_channel]


def _input_from_number(text: str) -> InputChannel | None:
    number = _int(text)
    if number == 0:
        return None
    for channel, n in _INPUT_NUMBERS.items():
        if n == number:
            return channel
    raise ValueError(f"Input {number} is one of the 3062 card's, D2 to D5")


class OutputChannel(BaseEnum):
    """An output, and its control loop. Outputs 1 and 2 are heaters, 3 and 4
    analog outputs."""

    OUTPUT_1 = (1, "Output 1")
    OUTPUT_2 = (2, "Output 2")
    OUTPUT_3 = (3, "Output 3")
    OUTPUT_4 = (4, "Output 4")


class AnalogOutput(BaseEnum):
    """An unpowered analog output."""

    OUTPUT_3 = (3, "Output 3")
    OUTPUT_4 = (4, "Output 4")


class AutotuneMode(BaseEnum):
    """Which terms autotuning sets."""

    P = (0, "P")
    PI = (1, "PI")
    PID = (2, "PID")


class ControlMode(BaseEnum):
    """What an output does. `PID`, `ZONE` and `OPEN_LOOP` are named as the
    Lakeshore 340's are. Monitor out and warmup supply are for outputs 3 and 4."""

    OFF = (0, "Off")
    PID = (1, "Closed loop PID")
    ZONE = (2, "Zone")
    OPEN_LOOP = (3, "Open loop")
    MONITOR_OUT = (4, "Monitor out")
    WARMUP_SUPPLY = (5, "Warmup supply")


class Units(BaseEnum):
    """Units of a reading, a setpoint or an analog output's data."""

    KELVIN = (1, "Kelvin")
    CELSIUS = (2, "Celsius")
    SENSOR_UNITS = (3, "Sensor units")


class DisplayData(BaseEnum):
    """What a field of the custom display shows of an input."""

    KELVIN = (1, "Kelvin")
    CELSIUS = (2, "Celsius")
    SENSOR_UNITS = (3, "Sensor units")
    MINIMUM = (4, "Minimum data")
    MAXIMUM = (5, "Maximum data")


class HeaterRange(BaseEnum):
    """An output's range. For outputs 3 and 4, `RANGE_1` is on."""

    OFF = (0, "Off")
    RANGE_1 = (1, "Range 1 (lowest, or on for outputs 3 and 4)")
    RANGE_2 = (2, "Range 2")
    RANGE_3 = (3, "Range 3")
    RANGE_4 = (4, "Range 4")
    RANGE_5 = (5, "Range 5 (highest)")


class HeaterResistance(BaseEnum):
    """Output 1's heater resistance setting."""

    OHM_25 = (1, "25 Ω")
    OHM_50 = (2, "50 Ω")


class MaxCurrent(BaseEnum):
    """Output 1's most current, as the manual lists it."""

    USER = (0, "User")
    CURRENT_0_707 = (1, "0.707 A")
    CURRENT_1 = (2, "1 A")
    CURRENT_1_141 = (3, "1.141 A")
    CURRENT_2 = (4, "2 A")


class HeaterDisplay(BaseEnum):
    """Whether a heater output is shown as a current or a power."""

    CURRENT = (1, "Current")
    POWER = (2, "Power")


class SensorType(BaseEnum):
    """An input's sensor type. Diode, thermocouple and capacitance need an option
    card."""

    DISABLED = (0, "Disabled")
    DIODE = (1, "Diode")
    PLATINUM_RTD = (2, "Platinum RTD")
    NTC_RTD = (3, "NTC RTD")
    THERMOCOUPLE = (4, "Thermocouple")
    CAPACITANCE = (5, "Capacitance")


class Excitation(BaseEnum):
    """The excitation voltage an NTC RTD input keeps."""

    VOLTAGE_1_MV = (0, "1 mV")
    VOLTAGE_10_MV = (1, "10 mV")


class DiodeCurrent(BaseEnum):
    """The excitation current of a diode input of the 3062 card."""

    CURRENT_10_UA = (0, "10 µA")
    CURRENT_1_MA = (1, "1 mA")


class Coefficient(BaseEnum):
    """Whether a sensor's reading falls or rises with temperature."""

    NEGATIVE = (1, "Negative")
    POSITIVE = (2, "Positive")


CurveCoefficient = Coefficient


class CurveFormat(BaseEnum):
    """What a curve's points pair with temperature."""

    MV_K = (1, "mV/K")
    V_K = (2, "V/K")
    OHM_K = (3, "Ohm/K")
    LOGOHM_K = (4, "log(Ohm)/K")


class DisplayMode(BaseEnum):
    """What the display shows."""

    INPUT_A = (0, "Input A")
    INPUT_B = (1, "Input B")
    INPUT_C = (2, "Input C")
    INPUT_D = (3, "Input D")
    CUSTOM = (4, "Custom")
    FOUR_LOOP = (5, "Four loop")
    ALL_INPUTS = (6, "All inputs")
    INPUT_D2 = (7, "Input D2")
    INPUT_D3 = (8, "Input D3")
    INPUT_D4 = (9, "Input D4")
    INPUT_D5 = (10, "Input D5")


class Relay(BaseEnum):
    """A relay."""

    RELAY_1 = (1, "Relay 1")
    RELAY_2 = (2, "Relay 2")


class RelayMode(BaseEnum):
    """What a relay does."""

    OFF = (0, "Off")
    ON = (1, "On")
    ALARMS = (2, "Alarms")


class AlarmType(BaseEnum):
    """Which of an input's alarms work a relay."""

    LOW = (0, "Low alarm")
    HIGH = (1, "High alarm")
    BOTH = (2, "Both alarms")


class RemoteMode(BaseEnum):
    """Whether the front panel or the interface is in control."""

    LOCAL = (0, "Local")
    REMOTE = (1, "Remote")
    REMOTE_LOCKOUT = (2, "Remote with local lockout")


class Interface(BaseEnum):
    """The remote interface that is enabled."""

    USB = (0, "USB")
    ETHERNET = (1, "Ethernet")
    IEEE_488 = (2, "IEEE-488")


class WarmupControl(BaseEnum):
    """How a warmup supply is controlled."""

    AUTO_OFF = (0, "Auto off")
    CONTINUOUS = (1, "Continuous")


class LanStatus(BaseEnum):
    """The state of the Ethernet connection."""

    STATIC_IP = (0, "Connected using static IP")
    DHCP = (1, "Connected using DHCP")
    AUTO_IP = (2, "Connected using Auto IP")
    ADDRESS_NOT_ACQUIRED = (3, "Address not acquired error")
    DUPLICATE_INITIAL_IP = (4, "Duplicate initial IP address error")
    DUPLICATE_ONGOING_IP = (5, "Duplicate ongoing IP address error")
    CABLE_UNPLUGGED = (6, "Cable unplugged")
    MODULE_ERROR = (7, "Module error")
    ACQUIRING_ADDRESS = (8, "Acquiring address")
    DISABLED = (9, "Ethernet disabled")


class Lakeshore_350(Instrument):
    """The Lake Shore Model 350 temperature controller.

    It has four inputs, A to D, and four outputs: heaters 1 and 2, and analog
    outputs 3 and 4. Each output has its own control loop, which takes its setpoint,
    PID, ramp and range.

    Where it does what the Lakeshore 340 does, its methods, their arguments and
    their choices are named as the 340's are, so that code written for one works
    with the other: `set_control_mode(output, ControlMode.OPEN_LOOP)`,
    `set_heater_range`, `set_manual_output`, `get_temperature` and the rest.
    """

    # The enums that the queries and commands take, so that they can be reached
    # from the instrument, as `Lakeshore_350.InputChannel`, without importing them.
    AlarmType = AlarmType
    AnalogOutput = AnalogOutput
    AutotuneMode = AutotuneMode
    Coefficient = Coefficient
    ControlMode = ControlMode
    CurveFormat = CurveFormat
    DiodeCurrent = DiodeCurrent
    DisplayData = DisplayData
    DisplayMode = DisplayMode
    Excitation = Excitation
    HeaterDisplay = HeaterDisplay
    HeaterRange = HeaterRange
    HeaterResistance = HeaterResistance
    InputChannel = InputChannel
    Interface = Interface
    LanStatus = LanStatus
    MaxCurrent = MaxCurrent
    OutputChannel = OutputChannel
    Relay = Relay
    RelayMode = RelayMode
    RemoteMode = RemoteMode
    SensorType = SensorType
    State = State
    Units = Units
    WarmupControl = WarmupControl

    def __init__(self, *args, **kwargs):
        """Initializes the Lakeshore 350, and clears its status registers."""
        super().__init__(*args, **kwargs)
        self.clear()

    # ------------------------------------------------------------ common commands
    @mark_query
    def identify(self) -> str:
        """Identifies the instrument.

        Returns:
            str: The manufacturer, model, serial numbers and firmware version, such
                as `LSCI,MODEL350,1234567/1234567,1.0`.
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
        """Clears the status byte, the standard event status register and the
        operational event register, and ends pending operations (`*CLS`). It
        doesn't clear the controller's settings.

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
                4 QXE, 16 EXE, 32 CME and 128 PON.

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
        """Queries the standard event status register (`*ESR?`).

        Returns:
            int: The sum of the bit weights of the events set.
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
    def wait_to_continue(self) -> int:
        """Holds the IEEE-488 interface off until every pending operation is
        complete, without setting the OPC event (`*WAI`).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*WAI")

    @mark_command
    def set_service_request_enable(self, value: int) -> int:
        """Sets which flags of the status byte request service (`*SRE`).

        Args:
            value (int): The sum of the bit weights to enable, 0 to 255: 16 MAV,
                32 ESB and 128 OSB.

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
            int: The sum of the bit weights of the flags set.
        """
        return _int(self.query("*STB?"))

    @mark_query
    def self_test(self) -> int:
        """Queries the result of the self-test the 350 runs at power-up (`*TST?`).

        Returns:
            int: 0 if no errors were found, 1 if some were.
        """
        return _int(self.query("*TST?"))

    @mark_query
    def get_operational_status(self) -> int:
        """Queries the operational status bits as they are now (`OPST?`).

        Returns:
            int: The sum of the bit weights of the bits set (the manual's section
                6.2.5.2 lists them).
        """
        return _int(self.query("OPST?"))

    @mark_query
    def get_operational_status_register(self) -> int:
        """Queries the operational status bits latched since it was last read, which
        clears it (`OPSTR?`).

        Returns:
            int: The sum of the bit weights of the bits set.
        """
        return _int(self.query("OPSTR?"))

    @mark_command
    def set_operational_status_enable(self, value: int) -> int:
        """Sets which operational status bits set the status byte's summary bit
        (`OPSTE`).

        Args:
            value (int): The sum of the bit weights to enable, 0 to 255.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"OPSTE {int(value)}")

    @mark_query
    def get_operational_status_enable(self) -> int:
        """Queries which operational status bits set the status byte's summary bit
        (`OPSTE?`).

        Returns:
            int: The sum of the bit weights that are enabled.
        """
        return _int(self.query("OPSTE?"))

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
    def get_all_temperatures(self) -> dict:
        """Queries every input's reading in kelvin at once (`KRDG? 0`).

        Returns:
            dict: The temperature of each input, in kelvin, by its name:
                `INPUT_A`, `INPUT_B`, `INPUT_C` and `INPUT_D`.
        """
        values = _fields(self.query("KRDG? 0"))
        return {channel.name: float(v) for channel, v in zip(InputChannel, values)}

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
        """Queries an input's reading in sensor units (`SRDG?`).

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
                16 temperature underrange, 32 temperature overrange, 64 sensor units
                zero and 128 sensor units overrange. 0 is a good reading.
        """
        return _int(self.query(f"RDGST? {input_channel.raw_value}"))

    @mark_query
    def get_junction_temperature(self) -> float:
        """Queries the temperature of the thermocouple card's junction block, which
        room temperature compensation uses (`TEMP?`).

        Returns:
            float: The temperature, in kelvin.
        """
        return float(self.query("TEMP?"))

    @mark_command
    def set_alarm(
        self,
        input_channel: InputChannel,
        state: State,
        high_value: float,
        low_value: float,
        latch: State,
        deadband: float = 0.0,
        audible: State = State.ON,
        visible: State = State.ON,
    ) -> int:
        """Configures an input's alarm (`ALARM`). The first five arguments are the
        Lakeshore 340's, in its order.

        Args:
            input_channel (InputChannel): The input to configure.
            state (State): Whether the alarm is checked.
            high_value (float): The value above which the high alarm is active.
            low_value (float): The value below which the low alarm is active.
            latch (State): Whether the alarm stays active after the condition ends.
            deadband (float): How far the reading must come back to end an alarm
                that isn't latched.
            audible (State): Whether the alarm beeps.
            visible (State): Whether the front panel's Alarm LED blinks.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"ALARM {input_channel.raw_value},{state.raw_value},{_number(high_value)},"
            f"{_number(low_value)},{_number(deadband)},{latch.raw_value},"
            f"{audible.raw_value},{visible.raw_value}"
        )

    @mark_query
    def get_alarm(self, input_channel: InputChannel) -> dict:
        """Queries an input's alarm configuration (`ALARM?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `state` (State), `high_value` (float), `low_value` (float),
                `deadband` (float), `latch` (State), `audible` (State) and
                `visible` (State).
        """
        f = _fields(self.query(f"ALARM? {input_channel.raw_value}"))
        return {
            "state": State.from_raw_value(_int(f[0])),
            "high_value": float(f[1]),
            "low_value": float(f[2]),
            "deadband": float(f[3]),
            "latch": State.from_raw_value(_int(f[4])),
            "audible": State.from_raw_value(_int(f[5])),
            "visible": State.from_raw_value(_int(f[6])),
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
            points (int): How many readings it averages: 2 to 64.
            window (int): The change, in percent of full scale (1 to 10), that
                restarts it.

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
            curve (int): 0 for none, 1 to 20 for a standard curve, 21 to 59 for a
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
    def set_input_type(
        self,
        input_channel: InputChannel,
        sensor_type: SensorType,
        autorange: State,
        input_range: int,
        compensation: State,
        units: Units,
        excitation: Excitation,
    ) -> int:
        """Configures an input's sensor (`INTYPE`). Every parameter is sent, and those
        that don't apply to the sensor type are ignored.

        Args:
            input_channel (InputChannel): The input to configure.
            sensor_type (SensorType): The sensor.
            autorange (State): Whether the range is chosen automatically, for an
                RTD.
            input_range (int): The range, with autorange off: for a diode 0 = 2.5 V,
                1 = 10 V; for an RTD 0 = 10 Ω, 1 = 30 Ω, 2 = 100 Ω, 3 = 300 Ω,
                4 = 1 kΩ, 5 = 3 kΩ, 6 = 10 kΩ, and for an NTC RTD also 7 = 30 kΩ,
                8 = 100 kΩ, 9 = 300 kΩ; for a capacitor 0 = 15 nF, 1 = 150 nF.
            compensation (State): Thermal EMF compensation for a resistor, room
                compensation for a thermocouple. For a capacitor, State.ON is a
                positive coefficient.
            units (Units): The preferred units, of the readings and the setpoint.
            excitation (Excitation): The excitation, for an NTC RTD.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"INTYPE {input_channel.raw_value},{sensor_type.raw_value},"
            f"{autorange.raw_value},{int(input_range)},{compensation.raw_value},"
            f"{units.raw_value},{excitation.raw_value}"
        )

    @mark_query
    def get_input_type(self, input_channel: InputChannel) -> dict:
        """Queries an input's sensor configuration (`INTYPE?`). With autorange on,
        the range is the one chosen now.

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            dict: `sensor_type` (SensorType), `autorange` (State), `input_range`
                (int), `compensation` (State), `units` (Units) and `excitation`
                (Excitation).
        """
        f = _fields(self.query(f"INTYPE? {input_channel.raw_value}"))
        return {
            "sensor_type": SensorType.from_raw_value(_int(f[0])),
            "autorange": State.from_raw_value(_int(f[1])),
            "input_range": _int(f[2]),
            "compensation": State.from_raw_value(_int(f[3])),
            "units": Units.from_raw_value(_int(f[4])),
            "excitation": Excitation.from_raw_value(_int(f[5])),
        }

    @mark_command
    def set_input_name(self, input_channel: InputChannel, name: str) -> int:
        """Names an input, for the front panel (`INNAME`).

        Args:
            input_channel (InputChannel): The input to name.
            name (str): Its name, up to 15 characters. Commas and semicolons are
                best left out, since replies use them to separate values.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"INNAME {input_channel.raw_value},{_quoted(name)}")

    @mark_query
    def get_input_name(self, input_channel: InputChannel) -> str:
        """Queries an input's name (`INNAME?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            str: Its name.
        """
        return (
            self.query(f"INNAME? {input_channel.raw_value}").strip().strip('"').strip()
        )

    @mark_command
    def set_diode_current(
        self, input_channel: InputChannel, current: DiodeCurrent
    ) -> int:
        """Sets a diode input's excitation current (`DIOCUR`). For the 3062 card's
        inputs, with the input's type set to diode first; otherwise it is ignored.

        Args:
            input_channel (InputChannel): The input to configure.
            current (DiodeCurrent): The current. 10 µA is the calibrated one.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"DIOCUR {input_channel.raw_value},{current.raw_value}")

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

    @mark_command
    def reset_min_max(self) -> int:
        """Resets the max/min data of every input (`MNMXRST`).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("MNMXRST")

    @mark_command
    def set_temperature_limit(self, input_channel: InputChannel, limit: float) -> int:
        """Sets the temperature above which every control output is shut down
        (`TLIMIT`).

        Args:
            input_channel (InputChannel): The input it watches.
            limit (float): The limit, in kelvin. 0 turns it off.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TLIMIT {input_channel.raw_value},{_number(limit)}")

    @mark_query
    def get_temperature_limit(self, input_channel: InputChannel) -> float:
        """Queries an input's temperature limit (`TLIMIT?`).

        Args:
            input_channel (InputChannel): The input to query.

        Returns:
            float: The limit, in kelvin. 0 if it is off.
        """
        return float(self.query(f"TLIMIT? {input_channel.raw_value}"))

    # ---------------------------------------------------------------------- loops
    @mark_command
    def set_output_mode(
        self,
        output_channel: OutputChannel,
        mode: ControlMode,
        input_channel: InputChannel,
        powerup: State,
    ) -> int:
        """Configures what an output does, and the input it controls from
        (`OUTMODE`).

        Args:
            output_channel (OutputChannel): The output to configure.
            mode (ControlMode): What it does.
            input_channel (InputChannel): The input it controls from.
            powerup (State): Whether it stays on after the 350 is powered up.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"OUTMODE {output_channel.raw_value},{mode.raw_value},"
            f"{_input_number(input_channel)},{powerup.raw_value}"
        )

    @mark_query
    def get_output_mode(self, output_channel: OutputChannel) -> dict:
        """Queries what an output does, and the input it controls from
        (`OUTMODE?`).

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            dict: `mode` (ControlMode), `input_channel` (InputChannel, or None if
                none is set) and `powerup` (State).
        """
        f = _fields(self.query(f"OUTMODE? {output_channel.raw_value}"))
        return {
            "mode": ControlMode.from_raw_value(_int(f[0])),
            "input_channel": _input_from_number(f[1]),
            "powerup": State.from_raw_value(_int(f[2])),
        }

    @mark_command
    def set_control_mode(self, output_channel: OutputChannel, mode: ControlMode) -> int:
        """Sets what an output does, keeping its input and power-up setting
        (`OUTMODE?`, then `OUTMODE`).

        Args:
            output_channel (OutputChannel): The output to configure.
            mode (ControlMode): What it does: PID, zone, open loop (the manual
                output alone), off, or for outputs 3 and 4 monitor out or warmup
                supply.

        Returns:
            int: Status code indicating the success of the operation.
        """
        now = self.get_output_mode(output_channel)
        return self.set_output_mode(
            output_channel, mode, now["input_channel"], now["powerup"]
        )

    @mark_query
    def get_control_mode(self, output_channel: OutputChannel) -> ControlMode:
        """Queries what an output does (`OUTMODE?`).

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            ControlMode: Its mode.
        """
        return self.get_output_mode(output_channel)["mode"]

    @mark_command
    def set_control_input(
        self, output_channel: OutputChannel, input_channel: InputChannel
    ) -> int:
        """Sets the input an output controls from, keeping its mode and power-up
        setting (`OUTMODE?`, then `OUTMODE`).

        Args:
            output_channel (OutputChannel): The output to configure.
            input_channel (InputChannel): The input.

        Returns:
            int: Status code indicating the success of the operation.
        """
        now = self.get_output_mode(output_channel)
        return self.set_output_mode(
            output_channel, now["mode"], input_channel, now["powerup"]
        )

    @mark_query
    def get_control_input(self, output_channel: OutputChannel) -> InputChannel | None:
        """Queries the input an output controls from (`OUTMODE?`).

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            InputChannel | None: The input, or None if none is set.
        """
        return self.get_output_mode(output_channel)["input_channel"]

    @mark_command
    def set_autotune_pid(self, output: OutputChannel, mode: AutotuneMode) -> int:
        """Starts autotuning an output's control loop (`ATUNE`). `get_tuning_status`
        says whether it could start.

        Args:
            output (OutputChannel): The output to tune.
            mode (AutotuneMode): Which terms are tuned: P, PI or PID.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ATUNE {output.raw_value},{mode.raw_value}")

    @mark_query
    def get_tuning(self) -> bool:
        """Queries whether a loop is autotuning (`TUNEST?`).

        Returns:
            bool: True if one is.
        """
        return self.get_tuning_status()["tuning"]

    @mark_query
    def get_tuning_status(self) -> dict:
        """Queries autotuning's status (`TUNEST?`).

        Returns:
            dict: `tuning` (bool), `output_channel` (OutputChannel being tuned, or
                None), `error` (bool) and `stage` (int: the stage it is at, or that
                failed).
        """
        f = _fields(self.query("TUNEST?"))
        output = _int(f[1]) if len(f) > 1 else 0
        return {
            "tuning": _int(f[0]) == 1,
            "output_channel": OutputChannel.from_raw_value(output) if output else None,
            "error": len(f) > 2 and _int(f[2]) == 1,
            "stage": _int(f[3]) if len(f) > 3 else 0,
        }

    @mark_command
    def set_pid(
        self, output_channel: OutputChannel, p: float, i: float, d: float
    ) -> int:
        """Sets an output's PID values (`PID`).

        Args:
            output_channel (OutputChannel): The output to configure.
            p (float): The proportional term (gain): 0.1 to 1000.
            i (float): The integral term (reset): 0.1 to 1000.
            d (float): The derivative term (rate), in percent: 0 to 200.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"PID {output_channel.raw_value},{_number(p)},{_number(i)},{_number(d)}"
        )

    @mark_query
    def get_pid(self, output_channel: OutputChannel) -> dict:
        """Queries an output's PID values (`PID?`).

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            dict: `p` (float), `i` (float) and `d` (float).
        """
        f = _fields(self.query(f"PID? {output_channel.raw_value}"))
        return {"p": float(f[0]), "i": float(f[1]), "d": float(f[2])}

    @mark_command
    def set_setpoint(self, output_channel: OutputChannel, setpoint: float) -> int:
        """Sets an output's setpoint (`SETP`), in the preferred units of its
        control input. For outputs 3 and 4, it only applies in warmup mode.

        Args:
            output_channel (OutputChannel): The output to configure.
            setpoint (float): The setpoint.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SETP {output_channel.raw_value},{_number(setpoint)}")

    @mark_query
    def get_setpoint(self, output_channel: OutputChannel) -> float:
        """Queries an output's setpoint (`SETP?`). While it ramps, this is where the
        ramp has got to.

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            float: The setpoint.
        """
        return float(self.query(f"SETP? {output_channel.raw_value}"))

    @mark_command
    def set_ramp(self, output_channel: OutputChannel, state: State, rate: float) -> int:
        """Configures an output's setpoint ramp (`RAMP`): with it on, a new setpoint
        is ramped to at the rate.

        Args:
            output_channel (OutputChannel): The output to configure.
            state (State): Whether ramping is on.
            rate (float): The rate, in kelvin per minute: 0.001 to 100. 0 is as
                fast as it can.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"RAMP {output_channel.raw_value},{state.raw_value},{rate:.3f}"
        )

    @mark_query
    def get_ramp(self, output_channel: OutputChannel) -> float:
        """Queries an output's ramp rate (`RAMP?`).

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            float: The rate, in kelvin per minute.
        """
        return float(_fields(self.query(f"RAMP? {output_channel.raw_value}"))[1])

    @mark_query
    def get_ramp_state(self, output_channel: OutputChannel) -> State:
        """Queries whether an output's ramp is on (`RAMP?`).

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            State: State.ON if a new setpoint is ramped to.
        """
        f = _fields(self.query(f"RAMP? {output_channel.raw_value}"))
        return State.from_raw_value(_int(f[0]))

    @mark_query
    def get_ramping(self, output_channel: OutputChannel) -> bool:
        """Queries whether an output's setpoint is ramping now (`RAMPST?`).

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            bool: True while it ramps.
        """
        return _int(self.query(f"RAMPST? {output_channel.raw_value}")) == 1

    @mark_command
    def set_manual_output(self, output_channel: OutputChannel, percent: float) -> int:
        """Sets an output's manual output (`MOUT`), in percent. In open loop mode it
        is the output. In PID and zone modes it is added to the PID's.

        Args:
            output_channel (OutputChannel): The output to configure.
            percent (float): The output, in percent of the range.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"MOUT {output_channel.raw_value},{percent:.2f}")

    @mark_query
    def get_manual_output(self, output_channel: OutputChannel) -> float:
        """Queries an output's manual output (`MOUT?`).

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            float: The manual output, in percent.
        """
        return float(self.query(f"MOUT? {output_channel.raw_value}"))

    @mark_command
    def set_heater_range(
        self, output_channel: OutputChannel, heater_range: HeaterRange
    ) -> int:
        """Sets an output's range (`RANGE`). `HeaterRange.OFF` turns it off. For
        outputs 3 and 4, `RANGE_1` turns it on.

        Args:
            output_channel (OutputChannel): The output to configure.
            heater_range (HeaterRange): The range.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"RANGE {output_channel.raw_value},{heater_range.raw_value}"
        )

    @mark_query
    def get_heater_range(self, output_channel: OutputChannel) -> HeaterRange:
        """Queries an output's range (`RANGE?`).

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            HeaterRange: The range. `HeaterRange.OFF` if it is off.
        """
        return HeaterRange.from_raw_value(
            _int(self.query(f"RANGE? {output_channel.raw_value}"))
        )

    @mark_query
    def get_heater_output(self, output_channel: OutputChannel) -> float:
        """Queries an output's output, in percent: a heater's (`HTR?`), or for
        outputs 3 and 4 the analog output's (`AOUT?`).

        Args:
            output_channel (OutputChannel): The output to query.

        Returns:
            float: The output, in percent.
        """
        command = "HTR?" if output_channel.raw_value <= 2 else "AOUT?"
        return float(self.query(f"{command} {output_channel.raw_value}"))

    @mark_query
    def get_heater_status(self, output_channel: OutputChannel) -> int:
        """Queries a heater's error code, which clears it (`HTRST?`).

        Args:
            output_channel (OutputChannel): The heater: output 1 or 2.

        Returns:
            int: 0 no error, 1 the heater is open, 2 a short on output 1, or
                compliance on output 2.

        Raises:
            ValueError: For output 3 or 4, which aren't heaters.
        """
        if output_channel.raw_value > 2:
            raise ValueError(
                f"{output_channel.name} isn't a heater: outputs 1 and 2 are"
            )
        return _int(self.query(f"HTRST? {output_channel.raw_value}"))

    @mark_command
    def set_heater_setup(
        self,
        output_channel: OutputChannel,
        resistance: HeaterResistance,
        max_current: MaxCurrent,
        max_user_current: float,
        heater_display: HeaterDisplay,
    ) -> int:
        """Configures a heater output (`HTRSET`).

        Args:
            output_channel (OutputChannel): The heater: output 1 or 2.
            resistance (HeaterResistance): The heater's resistance, for output 1.
            max_current (MaxCurrent): The most current, for output 1.
            max_user_current (float): The most current, in amps, when
                `max_current` is `MaxCurrent.USER`, for output 1.
            heater_display (HeaterDisplay): Whether the output is shown as a
                current or a power.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"HTRSET {output_channel.raw_value},{resistance.raw_value},"
            f"{max_current.raw_value},{max_user_current:.3f},{heater_display.raw_value}"
        )

    @mark_query
    def get_heater_setup(self, output_channel: OutputChannel) -> dict:
        """Queries a heater output's configuration (`HTRSET?`).

        Args:
            output_channel (OutputChannel): The heater: output 1 or 2.

        Returns:
            dict: `resistance` (HeaterResistance), `max_current` (MaxCurrent),
                `max_user_current` (float, amps) and `heater_display`
                (HeaterDisplay).
        """
        f = _fields(self.query(f"HTRSET? {output_channel.raw_value}"))
        return {
            "resistance": HeaterResistance.from_raw_value(_int(f[0])),
            "max_current": MaxCurrent.from_raw_value(_int(f[1])),
            "max_user_current": float(f[2]),
            "heater_display": HeaterDisplay.from_raw_value(_int(f[3])),
        }

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
        input_channel: InputChannel | None = None,
        rate: float = 0.0,
    ) -> int:
        """Configures a zone of an output's zone table (`ZONE`), which zone mode
        uses. The arguments the 340 takes come first, in its order.

        Args:
            output_channel (OutputChannel): The output to configure.
            zone (int): The zone: 1 to 10.
            top (float): The zone's upper setpoint, in kelvin.
            p (float): The proportional term in the zone.
            i (float): The integral term in the zone.
            d (float): The derivative term in the zone, in percent.
            manual_output (float): The manual output in the zone, in percent.
            heater_range (HeaterRange): The range in the zone.
            input_channel (InputChannel | None): The input in the zone. None keeps
                the one the output has.
            rate (float): The ramp rate in the zone, in kelvin per minute.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"ZONE {output_channel.raw_value},{int(zone)},{_number(top)},"
            f"{_number(p)},{_number(i)},{_number(d)},{manual_output:.2f},"
            f"{heater_range.raw_value},{_input_number(input_channel)},{_number(rate)}"
        )

    @mark_query
    def get_zone(self, output_channel: OutputChannel, zone: int) -> dict:
        """Queries a zone of an output's zone table (`ZONE?`).

        Args:
            output_channel (OutputChannel): The output to query.
            zone (int): The zone: 1 to 10.

        Returns:
            dict: `top` (float), `p` (float), `i` (float), `d` (float),
                `manual_output` (float), `heater_range` (HeaterRange),
                `input_channel` (InputChannel, or None for the output's own) and
                `rate` (float).
        """
        f = _fields(self.query(f"ZONE? {output_channel.raw_value},{int(zone)}"))
        return {
            "top": float(f[0]),
            "p": float(f[1]),
            "i": float(f[2]),
            "d": float(f[3]),
            "manual_output": float(f[4]),
            "heater_range": HeaterRange.from_raw_value(_int(f[5])),
            "input_channel": _input_from_number(f[6]),
            "rate": float(f[7]),
        }

    # -------------------------------------------------------------- analog outputs
    @mark_command
    def set_analog_output_setup(
        self,
        output: AnalogOutput,
        input_channel: InputChannel,
        source: Units,
        high_value: float,
        low_value: float,
        bipolar: State,
    ) -> int:
        """Configures what an analog output shows in monitor out mode (`ANALOG`).
        `set_control_mode` puts it in that mode.

        Args:
            output (AnalogOutput): The output to configure.
            input_channel (InputChannel): The input it follows.
            source (Units): The input's units it follows.
            high_value (float): The data at +100 % output.
            low_value (float): The data at -100 % output (bipolar) or 0 %.
            bipolar (State): Whether it is bipolar, or positive only.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"ANALOG {output.raw_value},{_input_number(input_channel)},"
            f"{source.raw_value},{_number(high_value)},{_number(low_value)},"
            f"{bipolar.raw_value}"
        )

    @mark_query
    def get_analog_output_setup(self, output: AnalogOutput) -> dict:
        """Queries what an analog output shows in monitor out mode (`ANALOG?`).

        Args:
            output (AnalogOutput): The output to query.

        Returns:
            dict: `input_channel` (InputChannel, or None if none is set), `source`
                (Units), `high_value` (float), `low_value` (float) and `bipolar`
                (State).
        """
        f = _fields(self.query(f"ANALOG? {output.raw_value}"))
        return {
            "input_channel": _input_from_number(f[0]),
            "source": Units.from_raw_value(_int(f[1])),
            "high_value": float(f[2]),
            "low_value": float(f[3]),
            "bipolar": State.from_raw_value(_int(f[4])),
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

    @mark_command
    def set_warmup(
        self, output: AnalogOutput, control: WarmupControl, percent: float
    ) -> int:
        """Configures an analog output's warmup supply (`WARMUP`). `set_output_mode`
        sets its mode and control input.

        Args:
            output (AnalogOutput): The output to configure.
            control (WarmupControl): How the supply is controlled.
            percent (float): The output, in percent of 10 V, that turns the external
                supply on.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"WARMUP {output.raw_value},{control.raw_value},{percent:.2f}"
        )

    @mark_query
    def get_warmup(self, output: AnalogOutput) -> dict:
        """Queries an analog output's warmup supply (`WARMUP?`).

        Args:
            output (AnalogOutput): The output to query.

        Returns:
            dict: `control` (WarmupControl) and `percent` (float).
        """
        f = _fields(self.query(f"WARMUP? {output.raw_value}"))
        return {
            "control": WarmupControl.from_raw_value(_int(f[0])),
            "percent": float(f[1]),
        }

    # ---------------------------------------------------------------------- relays
    @mark_command
    def set_relay(
        self,
        relay: Relay,
        mode: RelayMode,
        input_channel: InputChannel,
        alarm_type: AlarmType,
    ) -> int:
        """Configures a relay (`RELAY`).

        Args:
            relay (Relay): The relay to configure.
            mode (RelayMode): Off, on, or worked by an alarm.
            input_channel (InputChannel): The input whose alarm works it, in alarm
                mode.
            alarm_type (AlarmType): Which of the input's alarms work it, in alarm
                mode.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"RELAY {relay.raw_value},{mode.raw_value},{input_channel.raw_value},"
            f"{alarm_type.raw_value}"
        )

    @mark_query
    def get_relay(self, relay: Relay) -> dict:
        """Queries a relay's configuration (`RELAY?`).

        Args:
            relay (Relay): The relay to query.

        Returns:
            dict: `mode` (RelayMode), `input_channel` (InputChannel) and
                `alarm_type` (AlarmType).
        """
        f = _fields(self.query(f"RELAY? {relay.raw_value}"))
        return {
            "mode": RelayMode.from_raw_value(_int(f[0])),
            "input_channel": InputChannel.from_raw_value(f[1][:1]),
            "alarm_type": AlarmType.from_raw_value(_int(f[2])),
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

    # --------------------------------------------------------------------- display
    @mark_command
    def set_display(
        self, mode: DisplayMode, fields: int, output_channel: OutputChannel
    ) -> int:
        """Configures the display (`DISPLAY`).

        Args:
            mode (DisplayMode): What it shows.
            fields (int): In custom mode, 0 for 2 large fields, 1 for 4 large, 2 for
                8 small. In all inputs mode, 0 for small readings with names, 1 for
                large ones without.
            output_channel (OutputChannel): The output whose loop the custom mode
                shows at the bottom.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"DISPLAY {mode.raw_value},{int(fields)},{output_channel.raw_value}"
        )

    @mark_query
    def get_display(self) -> dict:
        """Queries the display's configuration (`DISPLAY?`).

        Returns:
            dict: `mode` (DisplayMode), `fields` (int) and `output_channel`
                (OutputChannel).
        """
        f = _fields(self.query("DISPLAY?"))
        return {
            "mode": DisplayMode.from_raw_value(_int(f[0])),
            "fields": _int(f[1]),
            "output_channel": OutputChannel.from_raw_value(_int(f[2])),
        }

    @mark_command
    def set_display_contrast(self, contrast: int) -> int:
        """Sets the display's contrast (`BRIGT`).

        Args:
            contrast (int): The contrast: 1 to 32.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"BRIGT {int(contrast)}")

    @mark_query
    def get_display_contrast(self) -> int:
        """Queries the display's contrast (`BRIGT?`).

        Returns:
            int: The contrast: 1 to 32.
        """
        return _int(self.query("BRIGT?"))

    @mark_command
    def set_display_field(
        self, field: int, input_channel: InputChannel, source: DisplayData
    ) -> int:
        """Sets what a field of the custom display shows (`DISPFLD`).

        Args:
            field (int): The field: 1 to 8.
            input_channel (InputChannel): The input it shows.
            source (DisplayData): The input's data it shows.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"DISPFLD {int(field)},{_input_number(input_channel)},{source.raw_value}"
        )

    @mark_query
    def get_display_field(self, field: int) -> dict:
        """Queries what a field of the custom display shows (`DISPFLD?`).

        Args:
            field (int): The field: 1 to 8.

        Returns:
            dict: `input_channel` (InputChannel, or None if none is set) and
                `source` (DisplayData).
        """
        f = _fields(self.query(f"DISPFLD? {int(field)}"))
        return {
            "input_channel": _input_from_number(f[0]),
            "source": DisplayData.from_raw_value(_int(f[1])),
        }

    @mark_command
    def set_leds(self, state: State) -> int:
        """Turns the front panel's LEDs on or off (`LEDS`).

        Args:
            state (State): Whether they work.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"LEDS {state.raw_value}")

    @mark_query
    def get_leds(self) -> State:
        """Queries whether the front panel's LEDs are on (`LEDS?`).

        Returns:
            State: State.ON if they are.
        """
        return State.from_raw_value(_int(self.query("LEDS?")))

    @mark_command
    def set_lockout(self, state: State, code: int) -> int:
        """Locks or unlocks the front panel's keys, all but All Off (`LOCK`).

        Args:
            state (State): Whether they are locked.
            code (int): The code that unlocks them at the front panel: 0 to 999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"LOCK {state.raw_value},{int(code):03d}")

    @mark_query
    def get_lockout(self) -> dict:
        """Queries whether the front panel is locked, and its code (`LOCK?`).

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
    def set_interface(self, interface: Interface) -> int:
        """Enables a remote interface (`INTSEL`). A connection over another stops
        working.

        Args:
            interface (Interface): USB, Ethernet or IEEE-488.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"INTSEL {interface.raw_value}")

    @mark_query
    def get_interface(self) -> Interface:
        """Queries which remote interface is enabled (`INTSEL?`).

        Returns:
            Interface: The interface.
        """
        return Interface.from_raw_value(_int(self.query("INTSEL?")))

    @mark_command
    def set_ieee_interface(self, address: int) -> int:
        """Sets the IEEE-488 address (`IEEE`). It takes effect after the next
        terminator, so a connection over it must change to match.

        Args:
            address (int): The GPIB address: 1 to 30.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"IEEE {int(address)}")

    @mark_query
    def get_ieee_interface(self) -> dict:
        """Queries the IEEE-488 interface's configuration (`IEEE?`).

        Returns:
            dict: `address` (int).
        """
        return {"address": _int(self.query("IEEE?"))}

    @mark_command
    def set_network(
        self,
        dhcp: State,
        auto_ip: State,
        ip: str,
        subnet_mask: str,
        gateway: str,
        primary_dns: str,
        secondary_dns: str,
        hostname: str,
        domain: str,
        description: str,
    ) -> int:
        """Configures the Ethernet interface (`NET`). The addresses are for a static
        configuration.

        Args:
            dhcp (State): Whether DHCP is on.
            auto_ip (State): Whether link-local addressing (Auto IP) is on.
            ip (str): The IP address, such as `192.168.0.12`.
            subnet_mask (str): The subnet mask.
            gateway (str): The gateway's address.
            primary_dns (str): The primary DNS server's address.
            secondary_dns (str): The secondary DNS server's address.
            hostname (str): The preferred hostname, up to 15 characters.
            domain (str): The preferred domain name, up to 64 characters.
            description (str): The instrument's description, up to 32 characters.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"NET {dhcp.raw_value},{auto_ip.raw_value},{ip},{subnet_mask},{gateway},"
            f"{primary_dns},{secondary_dns},{_quoted(hostname)},{_quoted(domain)},"
            f"{_quoted(description)}"
        )

    @mark_query
    def get_network(self) -> dict:
        """Queries the Ethernet interface's configuration (`NET?`).

        Returns:
            dict: `dhcp` (State), `auto_ip` (State), `ip`, `subnet_mask`,
                `gateway`, `primary_dns`, `secondary_dns`, `hostname`, `domain` and
                `description` (each str).
        """
        f = _fields(self.query("NET?"))
        keys = (
            "ip",
            "subnet_mask",
            "gateway",
            "primary_dns",
            "secondary_dns",
            "hostname",
            "domain",
            "description",
        )
        return {
            "dhcp": State.from_raw_value(_int(f[0])),
            "auto_ip": State.from_raw_value(_int(f[1])),
            **dict(zip(keys, f[2:])),
        }

    @mark_query
    def get_network_status(self) -> dict:
        """Queries the Ethernet interface's state and the addresses it has
        (`NETID?`).

        Returns:
            dict: `lan_status` (LanStatus), `ip`, `subnet_mask`, `gateway`,
                `primary_dns`, `secondary_dns`, `mac_address`, `hostname` and
                `domain` (each str).
        """
        f = _fields(self.query("NETID?"))
        keys = (
            "ip",
            "subnet_mask",
            "gateway",
            "primary_dns",
            "secondary_dns",
            "mac_address",
            "hostname",
            "domain",
        )
        return {
            "lan_status": LanStatus.from_raw_value(_int(f[0])),
            **dict(zip(keys, f[1:])),
        }

    @mark_command
    def set_web_login(self, username: str, password: str) -> int:
        """Sets the login of the 350's website (`WEBLOG`).

        Args:
            username (str): The username, up to 15 characters.
            password (str): The password, up to 15 characters.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"WEBLOG {_quoted(username)},{_quoted(password)}")

    @mark_query
    def get_web_login(self) -> dict:
        """Queries the login of the 350's website (`WEBLOG?`).

        Returns:
            dict: `username` (str) and `password` (str).
        """
        f = _fields(self.query("WEBLOG?"))
        return {"username": f[0], "password": f[1]}

    # ---------------------------------------------------------------------- system
    @mark_command
    def reset_to_factory_defaults(self) -> int:
        """Sets every setting to its factory default, and resets the 350
        (`DFLT 99`).

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
        """Sets a user curve's header (`CRVHDR`). The 350 works the coefficient out
        from the curve's first two points.

        Args:
            curve_index (int): The curve: 21 to 59.
            name (str): Its name, up to 15 characters.
            serial_no (str): Its serial number, up to 10 characters: NONE if it
                has none.
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
            curve_index (int): The curve: 1 to 59.

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
        """Sets a point of a user curve (`CRVPT`).

        Args:
            curve_index (int): The curve: 21 to 59.
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
            curve_index (int): The curve: 1 to 59.
            point_index (int): The point: 1 to 200.

        Returns:
            dict: `sensor` (float) and `temperature` (float, kelvin).
        """
        f = _fields(self.query(f"CRVPT? {int(curve_index)},{int(point_index)}"))
        return {"sensor": float(f[0]), "temperature": float(f[1])}

    @mark_command
    def delete_curve(self, curve_index: int) -> int:
        """Deletes a user curve (`CRVDEL`).

        Args:
            curve_index (int): The curve: 21 to 59.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CRVDEL {int(curve_index)}")

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
        """Makes a SoftCal curve from a standard curve and calibration points
        (`SCAL`).

        Args:
            standard_curve (int): The standard curve to start from: 1, 6 or 7.
            user_curve (int): The user curve to write: 21 to 59.
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
        points = [t1, u1, t2, u2]
        if t3 is not None and u3 is not None:
            points += [t3, u3]
        return self.command(
            f"SCAL {int(standard_curve)},{int(user_curve)},{serial_no},"
            + ",".join(_number(p) for p in points)
        )
