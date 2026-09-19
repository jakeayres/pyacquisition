from ...core.instrument import BaseEnum, Instrument, mark_command, mark_query
from ._scpi import (
    FilterControl,
    State,
    StatusRegister,
    TraceControl,
    TraceFeed,
    first_number,
    format_count,
    format_number,
    parse_enum,
    parse_error,
    to_floats,
    to_int,
    to_ints,
    unquote,
)


def format_channels(channels: list[int]) -> str:
    """Formats channels as a SCPI channel list, for example `(@1,3,5)`."""
    return "(@" + ",".join(str(int(channel)) for channel in channels) + ")"


def parse_channels(reply: str) -> list[int]:
    """Reads a SCPI channel list such as `(@1:3,5)`, expanding the ranges."""
    channels = []
    for item in unquote(reply).strip("()@ ").split(","):
        item = item.strip()
        if not item:
            continue
        low, _, high = item.partition(":")
        channels.extend(range(int(low), int(high or low) + 1))
    return channels


class Function(BaseEnum):
    """A measurement function."""

    DC_VOLTAGE = ("VOLT:DC", "DC voltage")
    AC_VOLTAGE = ("VOLT:AC", "AC voltage")
    DC_CURRENT = ("CURR:DC", "DC current")
    AC_CURRENT = ("CURR:AC", "AC current")
    RESISTANCE = ("RES", "2-wire resistance")
    RESISTANCE_4W = ("FRES", "4-wire resistance")
    FREQUENCY = ("FREQ", "Frequency")
    PERIOD = ("PER", "Period")
    TEMPERATURE = ("TEMP", "Temperature")
    DIODE = ("DIOD", "Diode test")
    CONTINUITY = ("CONT", "Continuity test")


class RangeFunction(BaseEnum):
    """A function that has a measurement range."""

    DC_VOLTAGE = ("VOLT:DC", "DC voltage")
    AC_VOLTAGE = ("VOLT:AC", "AC voltage")
    DC_CURRENT = ("CURR:DC", "DC current")
    AC_CURRENT = ("CURR:AC", "AC current")
    RESISTANCE = ("RES", "2-wire resistance")
    RESISTANCE_4W = ("FRES", "4-wire resistance")


class NplcFunction(BaseEnum):
    """A function whose integration time can be set."""

    DC_VOLTAGE = ("VOLT:DC", "DC voltage")
    AC_VOLTAGE = ("VOLT:AC", "AC voltage")
    DC_CURRENT = ("CURR:DC", "DC current")
    AC_CURRENT = ("CURR:AC", "AC current")
    RESISTANCE = ("RES", "2-wire resistance")
    RESISTANCE_4W = ("FRES", "4-wire resistance")
    TEMPERATURE = ("TEMP", "Temperature")


class FilterFunction(BaseEnum):
    """A function that has an averaging filter."""

    DC_VOLTAGE = ("VOLT:DC", "DC voltage")
    AC_VOLTAGE = ("VOLT:AC", "AC voltage")
    DC_CURRENT = ("CURR:DC", "DC current")
    AC_CURRENT = ("CURR:AC", "AC current")
    RESISTANCE = ("RES", "2-wire resistance")
    RESISTANCE_4W = ("FRES", "4-wire resistance")
    TEMPERATURE = ("TEMP", "Temperature")


class DigitsFunction(BaseEnum):
    """A function whose display resolution can be set."""

    DC_VOLTAGE = ("VOLT:DC", "DC voltage")
    AC_VOLTAGE = ("VOLT:AC", "AC voltage")
    DC_CURRENT = ("CURR:DC", "DC current")
    AC_CURRENT = ("CURR:AC", "AC current")
    RESISTANCE = ("RES", "2-wire resistance")
    RESISTANCE_4W = ("FRES", "4-wire resistance")
    FREQUENCY = ("FREQ", "Frequency")
    PERIOD = ("PER", "Period")
    TEMPERATURE = ("TEMP", "Temperature")


class ReferenceFunction(BaseEnum):
    """A function that has a reference (relative) value."""

    DC_VOLTAGE = ("VOLT:DC", "DC voltage")
    AC_VOLTAGE = ("VOLT:AC", "AC voltage")
    DC_CURRENT = ("CURR:DC", "DC current")
    AC_CURRENT = ("CURR:AC", "AC current")
    RESISTANCE = ("RES", "2-wire resistance")
    RESISTANCE_4W = ("FRES", "4-wire resistance")
    FREQUENCY = ("FREQ", "Frequency")
    PERIOD = ("PER", "Period")
    TEMPERATURE = ("TEMP", "Temperature")


class BandwidthFunction(BaseEnum):
    """A AC function whose bandwidth can be set."""

    AC_VOLTAGE = ("VOLT:AC", "AC voltage")
    AC_CURRENT = ("CURR:AC", "AC current")


class ThresholdFunction(BaseEnum):
    """A function whose threshold voltage range can be set."""

    FREQUENCY = ("FREQ", "Frequency")
    PERIOD = ("PER", "Period")


class ThermocoupleType(BaseEnum):
    J = ("J", "Type J")
    K = ("K", "Type K")
    T = ("T", "Type T")


class ReferenceJunction(BaseEnum):
    SIMULATED = ("SIM", "Simulated")
    REAL = ("REAL", "Real")


class TemperatureUnit(BaseEnum):
    CELSIUS = ("C", "Celsius")
    FAHRENHEIT = ("F", "Fahrenheit")
    KELVIN = ("K", "Kelvin")


class VoltageUnit(BaseEnum):
    VOLTS = ("V", "Volts")
    DECIBELS = ("DB", "dB")
    DECIBELS_MILLIWATT = ("DBM", "dBm")


class MathFormat(BaseEnum):
    NONE = ("NONE", "None")
    MX_PLUS_B = ("MXB", "mX+b")
    PERCENT = ("PERC", "Percent")


class StatisticFormat(BaseEnum):
    NONE = ("NONE", "None")
    MEAN = ("MEAN", "Mean")
    STANDARD_DEVIATION = ("SDEV", "Standard deviation")
    MAXIMUM = ("MAX", "Maximum")
    MINIMUM = ("MIN", "Minimum")


class TriggerSource(BaseEnum):
    IMMEDIATE = ("IMM", "Immediate")
    EXTERNAL = ("EXT", "External")
    TIMER = ("TIM", "Timer")
    MANUAL = ("MAN", "Manual")
    BUS = ("BUS", "Bus")


class ScanMode(BaseEnum):
    NONE = ("NONE", "None")
    INTERNAL = ("INT", "Internal")
    EXTERNAL = ("EXT", "External")


class PowerOnSetup(BaseEnum):
    RST = ("RST", "*RST defaults")
    PRESET = ("PRES", "Preset defaults")
    SAVED = ("SAV0", "Saved setup")


class Key(BaseEnum):
    """Front panel key codes, as used by SYSTem:KEY."""

    SHIFT = (1, "SHIFT")
    DC_VOLTAGE = (2, "DCV")
    AC_VOLTAGE = (3, "ACV")
    DC_CURRENT = (4, "DCI")
    AC_CURRENT = (5, "ACI")
    RESISTANCE = (6, "Ω2")
    RESISTANCE_4W = (7, "Ω4")
    FREQUENCY = (8, "FREQ")
    UP = (11, "Up arrow")
    AUTO = (12, "AUTO")
    DOWN = (13, "Down arrow")
    ENTER = (14, "ENTER")
    RIGHT = (15, "Right arrow")
    TEMPERATURE = (16, "TEMP")
    LOCAL = (17, "LOCAL")
    EXTERNAL_TRIGGER = (18, "EX TRIG")
    TRIGGER = (19, "TRIG")
    STORE = (20, "STORE")
    RECALL = (21, "RECALL")
    FILTER = (22, "FILTER")
    REL = (23, "REL")
    LEFT = (24, "Left arrow")
    OPEN = (26, "OPEN")
    CLOSE = (27, "CLOSE")
    STEP = (28, "STEP")
    SCAN = (29, "SCAN")
    DIGITS = (30, "DIGITS")
    RATE = (31, "RATE")
    EXIT = (32, "EXIT")


class Keithley_2000(Instrument):
    """Class for controlling the Keithley 2000 6½-digit multimeter.

    Only the SCPI language is implemented, which is the factory setting. The
    Keithley 196/199 and Fluke 8840A/8842A emulations are not, nor are the RS-232
    commands, calibration, or the settings that change the remote interface.

    Each measurement function keeps its own configuration, so the settings that
    take a `function` change that function whether or not it is the one selected.
    Which functions a setting applies to differs, and each has its own enum
    (`RangeFunction`, `NplcFunction`...) so that only valid ones can be given.

    An optional Model 2000-SCAN or 2001-TCSCAN scanner card adds the channel
    and scan methods.
    """

    def __init__(self, *args, **kwargs):
        """Initializes the Keithley 2000 instrument.

        Clears the status structure and selects ASCII readings with the reading
        alone (no units or channel), because the methods here parse them that way.
        """
        super().__init__(*args, **kwargs)
        self.clear()
        self.command("FORM ASC")
        self.command("FORM:ELEM READ")

    """ IEEE-488.2 COMMON COMMANDS """

    @mark_query
    def identify(self) -> str:
        """Identifies the instrument.

        Returns:
            str: The manufacturer, model, serial number and firmware revisions.
        """
        return self.query("*IDN?")

    @mark_command
    def reset(self) -> int:
        """Resets the instrument to its *RST default state.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*RST")

    @mark_command
    def clear(self) -> int:
        """Clears the event registers and the error queue.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*CLS")

    @mark_query
    def get_options(self) -> str:
        """Queries the installed options.

        Returns:
            str: 0 if no scanner card is installed, otherwise the card model.
        """
        return unquote(self.query("*OPT?"))

    @mark_command
    def save_setup(self) -> int:
        """Saves the present setup to memory. There is one location.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*SAV 0")

    @mark_command
    def recall_setup(self) -> int:
        """Recalls the setup saved in memory.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*RCL 0")

    @mark_command
    def trigger(self) -> int:
        """Sends a bus trigger. Only acts if BUS is the trigger source.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*TRG")

    @mark_query
    def self_test(self) -> int:
        """Runs a checksum test of the ROM.

        Returns:
            int: 0 if the test passed, 1 if it failed.
        """
        return to_int(self.query("*TST?"))

    @mark_command
    def operation_complete(self) -> int:
        """Sets the operation complete bit once all pending operations finish.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*OPC")

    @mark_query
    def get_operation_complete(self) -> int:
        """Waits for all pending operations to finish.

        Returns:
            int: 1 once all pending operations are complete.
        """
        return to_int(self.query("*OPC?"))

    @mark_command
    def wait_to_continue(self) -> int:
        """Holds off later commands until all pending operations are finished.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*WAI")

    @mark_query
    def get_event_status(self) -> int:
        """Reads and clears the standard event status register.

        Returns:
            int: The value of the standard event status register.
        """
        return to_int(self.query("*ESR?"))

    @mark_command
    def set_event_enable(self, value: int) -> int:
        """Sets the standard event enable register.

        Args:
            value (int): The standard event enable register. Range: 0 to 255.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"*ESE {value}")

    @mark_query
    def get_event_enable(self) -> int:
        """Queries the standard event enable register.

        Returns:
            int: The standard event enable register.
        """
        return to_int(self.query("*ESE?"))

    @mark_query
    def get_status_byte(self) -> int:
        """Reads the status byte register.

        Returns:
            int: The value of the status byte register.
        """
        return to_int(self.query("*STB?"))

    @mark_command
    def set_service_request_enable(self, value: int) -> int:
        """Sets the service request enable register.

        Args:
            value (int): The service request enable register. Range: 0 to 255.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"*SRE {value}")

    @mark_query
    def get_service_request_enable(self) -> int:
        """Queries the service request enable register.

        Returns:
            int: The service request enable register.
        """
        return to_int(self.query("*SRE?"))

    """ STATUS STRUCTURE AND ERROR QUEUE """

    @mark_query
    def get_status_event(self, register: StatusRegister) -> int:
        """Reads and clears an event register.

        Args:
            register (StatusRegister): The status register set.

        Returns:
            int: The value of the event register.
        """
        return to_int(self.query(f"STAT:{register.raw_value}:EVEN?"))

    @mark_query
    def get_status_condition(self, register: StatusRegister) -> int:
        """Reads a condition register.

        Args:
            register (StatusRegister): The status register set.

        Returns:
            int: The value of the condition register.
        """
        return to_int(self.query(f"STAT:{register.raw_value}:COND?"))

    @mark_command
    def set_status_enable(self, register: StatusRegister, value: int) -> int:
        """Sets the event enable register.

        Args:
            register (StatusRegister): The status register set.
            value (int): The event enable register. Range: 0 to 65535.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"STAT:{register.raw_value}:ENAB {value}")

    @mark_query
    def get_status_enable(self, register: StatusRegister) -> int:
        """Queries the event enable register.

        Args:
            register (StatusRegister): The status register set.

        Returns:
            int: The event enable register.
        """
        return to_int(self.query(f"STAT:{register.raw_value}:ENAB?"))

    @mark_command
    def preset_status(self) -> int:
        """Clears the operation, measurement and questionable enable registers.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("STAT:PRES")

    @mark_query
    def get_next_error(self) -> dict:
        """Reads and removes the oldest entry in the error queue.

        Returns:
            dict: The error code (code) and message (message). A code of 0 means no error.
        """
        return parse_error(self.query("STAT:QUE?"))

    @mark_query
    def get_error(self) -> dict:
        """Reads and removes the oldest entry in the error queue.

        Returns:
            dict: The error code (code) and message (message). A code of 0 means no error.
        """
        return parse_error(self.query("SYST:ERR?"))

    @mark_command
    def clear_error_queue(self) -> int:
        """Clears all messages from the error queue.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SYST:CLE")

    @mark_command
    def set_error_queue_enable(self, messages: str) -> int:
        """Sets which error and status messages are placed in the error queue. Others are disabled.

        Args:
            messages (str): The message codes, for example '-110:-222,-220'.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"STAT:QUE:ENAB ({messages})")

    @mark_query
    def get_error_queue_enable(self) -> str:
        """Queries the messages enabled for the error queue.

        Returns:
            str: The enabled message codes.
        """
        return unquote(self.query("STAT:QUE:ENAB?"))

    @mark_command
    def set_error_queue_disable(self, messages: str) -> int:
        """Removes messages from the set placed in the error queue.

        Args:
            messages (str): The message codes, for example '-110:-222,-220'.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"STAT:QUE:DIS ({messages})")

    @mark_query
    def get_error_queue_disable(self) -> str:
        """Queries the messages disabled for the error queue.

        Returns:
            str: The disabled message codes.
        """
        return unquote(self.query("STAT:QUE:DIS?"))

    """ READINGS """

    @mark_query
    def get_reading(self) -> float:
        """Reads the latest reading, without triggering one.

        Returns:
            float: The reading in V, A, ohms, Hz, s or the temperature unit. It is the same reading until a new one is taken.
        """
        return first_number(self.query("SENS:DATA?"))

    @mark_query
    def fetch(self) -> list[float]:
        """Reads the latest post-math readings, without triggering any.

        Returns:
            list[float]: The readings.
        """
        return to_floats(self.query("FETC?"))

    @mark_query
    def read(self) -> list[float]:
        """Aborts, initiates a new set of readings and returns them. The number is set by the sample count.

        Returns:
            list[float]: The readings.
        """
        return to_floats(self.query("READ?"))

    @mark_query
    def measure(self, function: Function) -> float:
        """Configures a function to its defaults and takes one reading. This resets that function's settings.

        Args:
            function (Function): The measurement function.

        Returns:
            float: The reading.
        """
        return first_number(self.query(f"MEAS:{function.raw_value}?"))

    @mark_command
    def configure(self, function: Function) -> int:
        """Configures a function to its defaults for one-shot readings, and disables continuous initiation. Take the reading with read().

        Args:
            function (Function): The measurement function.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CONF:{function.raw_value}")

    @mark_command
    def set_function(self, function: Function) -> int:
        """Sets the measurement function.

        Args:
            function (Function): The measurement function.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:FUNC '{function.raw_value}'")

    @mark_query
    def get_function(self) -> Function:
        """Queries the measurement function.

        Returns:
            Function: The measurement function.
        """
        return parse_enum(Function, self.query("SENS:FUNC?"))

    """ SETTINGS THAT EVERY FUNCTION KEEPS FOR ITSELF """

    @mark_command
    def set_nplc(self, function: NplcFunction, nplc: float) -> int:
        """Sets the integration time.

        Args:
            function (NplcFunction): The measurement function.
            nplc (float): The integration time in power line cycles. Range: 0.01 to 10.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:{function.raw_value}:NPLC {format_number(nplc)}")

    @mark_query
    def get_nplc(self, function: NplcFunction) -> float:
        """Queries the integration time.

        Args:
            function (NplcFunction): The measurement function.

        Returns:
            float: The integration time in power line cycles.
        """
        return float(self.query(f"SENS:{function.raw_value}:NPLC?"))

    @mark_command
    def set_range(self, function: RangeFunction, expected: float) -> int:
        """Sets the measurement range.

        Args:
            function (RangeFunction): The measurement function.
            expected (float): The measurement range in V, A or ohms. Give the largest reading expected: the most sensitive range that holds it is chosen and auto range is turned off. Range: 0 to 3.1 for current, 757.5 for AC volts, 1010 for DC volts, 120e6 for ohms.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"SENS:{function.raw_value}:RANG:UPP {format_number(expected)}"
        )

    @mark_query
    def get_range(self, function: RangeFunction) -> float:
        """Queries the full-scale value of the present range.

        Args:
            function (RangeFunction): The measurement function.

        Returns:
            float: The full-scale value of the present range in V, A or ohms.
        """
        return float(self.query(f"SENS:{function.raw_value}:RANG:UPP?"))

    @mark_command
    def set_auto_range(self, function: RangeFunction, state: State) -> int:
        """Enables or disables the auto range.

        Args:
            function (RangeFunction): The measurement function.
            state (State): State.ON to enable or State.OFF to disable the auto range.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:{function.raw_value}:RANG:AUTO {state.raw_value}")

    @mark_query
    def get_auto_range(self, function: RangeFunction) -> State:
        """Queries whether the auto range is enabled.

        Args:
            function (RangeFunction): The measurement function.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(
            to_int(self.query(f"SENS:{function.raw_value}:RANG:AUTO?"))
        )

    @mark_command
    def set_digits(self, function: DigitsFunction, digits: int) -> int:
        """Sets the display resolution.

        Args:
            function (DigitsFunction): The measurement function.
            digits (int): The display resolution. Range: 4 to 7, which is 3.5 to 6.5 digits.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:{function.raw_value}:DIG {digits}")

    @mark_query
    def get_digits(self, function: DigitsFunction) -> int:
        """Queries the display resolution.

        Args:
            function (DigitsFunction): The measurement function.

        Returns:
            int: The display resolution.
        """
        return to_int(self.query(f"SENS:{function.raw_value}:DIG?"))

    @mark_command
    def set_reference(self, function: ReferenceFunction, reference: float) -> int:
        """Sets the reference (relative) value.

        Args:
            function (ReferenceFunction): The measurement function.
            reference (float): The reference (relative) value in the function's unit. Enabled with set_reference_state.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:{function.raw_value}:REF {format_number(reference)}")

    @mark_query
    def get_reference(self, function: ReferenceFunction) -> float:
        """Queries the reference (relative) value.

        Args:
            function (ReferenceFunction): The measurement function.

        Returns:
            float: The reference (relative) value in the function's unit.
        """
        return float(self.query(f"SENS:{function.raw_value}:REF?"))

    @mark_command
    def set_reference_state(self, function: ReferenceFunction, state: State) -> int:
        """Enables or disables the reference (relative) value.

        Args:
            function (ReferenceFunction): The measurement function.
            state (State): State.ON to enable or State.OFF to disable the reference (relative) value.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:{function.raw_value}:REF:STAT {state.raw_value}")

    @mark_query
    def get_reference_state(self, function: ReferenceFunction) -> State:
        """Queries whether the reference (relative) value is enabled.

        Args:
            function (ReferenceFunction): The measurement function.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(
            to_int(self.query(f"SENS:{function.raw_value}:REF:STAT?"))
        )

    @mark_command
    def acquire_reference(self, function: ReferenceFunction) -> int:
        """Uses the present input as the reference value. The function must be the one selected, and have a valid reading.

        Args:
            function (ReferenceFunction): The measurement function.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:{function.raw_value}:REF:ACQ")

    @mark_command
    def set_average_filter(self, function: FilterFunction, state: State) -> int:
        """Enables or disables the averaging filter.

        Args:
            function (FilterFunction): The measurement function.
            state (State): State.ON to enable or State.OFF to disable the averaging filter.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:{function.raw_value}:AVER:STAT {state.raw_value}")

    @mark_query
    def get_average_filter(self, function: FilterFunction) -> State:
        """Queries whether the averaging filter is enabled.

        Args:
            function (FilterFunction): The measurement function.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(
            to_int(self.query(f"SENS:{function.raw_value}:AVER:STAT?"))
        )

    @mark_command
    def set_average_filter_control(
        self, function: FilterFunction, control: FilterControl
    ) -> int:
        """Sets the averaging filter type.

        Args:
            function (FilterFunction): The measurement function.
            control (FilterControl): The averaging filter type.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:{function.raw_value}:AVER:TCON {control.raw_value}")

    @mark_query
    def get_average_filter_control(self, function: FilterFunction) -> FilterControl:
        """Queries the averaging filter type.

        Args:
            function (FilterFunction): The measurement function.

        Returns:
            FilterControl: The averaging filter type.
        """
        return parse_enum(
            FilterControl, self.query(f"SENS:{function.raw_value}:AVER:TCON?")
        )

    @mark_command
    def set_average_filter_count(self, function: FilterFunction, count: int) -> int:
        """Sets the averaging filter count.

        Args:
            function (FilterFunction): The measurement function.
            count (int): The averaging filter count. Range: 1 to 100.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:{function.raw_value}:AVER:COUN {count}")

    @mark_query
    def get_average_filter_count(self, function: FilterFunction) -> int:
        """Queries the averaging filter count.

        Args:
            function (FilterFunction): The measurement function.

        Returns:
            int: The averaging filter count.
        """
        return to_int(self.query(f"SENS:{function.raw_value}:AVER:COUN?"))

    @mark_command
    def set_bandwidth(self, function: BandwidthFunction, bandwidth: float) -> int:
        """Sets the AC bandwidth.

        Args:
            function (BandwidthFunction): The measurement function.
            bandwidth (float): The AC bandwidth in Hz. Range: 3 to 300e3. Give the lowest frequency of interest, and the nearest of 3, 30 or 300 is chosen.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"SENS:{function.raw_value}:DET:BAND {format_number(bandwidth)}"
        )

    @mark_query
    def get_bandwidth(self, function: BandwidthFunction) -> float:
        """Queries the AC bandwidth.

        Args:
            function (BandwidthFunction): The measurement function.

        Returns:
            float: The AC bandwidth in Hz.
        """
        return float(self.query(f"SENS:{function.raw_value}:DET:BAND?"))

    @mark_command
    def set_threshold_range(self, function: ThresholdFunction, level: float) -> int:
        """Sets the threshold voltage range.

        Args:
            function (ThresholdFunction): The measurement function.
            level (float): The threshold voltage range in V. Give the expected signal level, and the most sensitive range that holds it is chosen. Range: 0 to 1010.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"SENS:{function.raw_value}:THR:VOLT:RANG {format_number(level)}"
        )

    @mark_query
    def get_threshold_range(self, function: ThresholdFunction) -> float:
        """Queries the threshold voltage range.

        Args:
            function (ThresholdFunction): The measurement function.

        Returns:
            float: The threshold voltage range in V.
        """
        return float(self.query(f"SENS:{function.raw_value}:THR:VOLT:RANG?"))

    """ TEMPERATURE, DIODE AND CONTINUITY """

    @mark_command
    def set_thermocouple_type(self, thermocouple: ThermocoupleType) -> int:
        """Sets the thermocouple type.

        Args:
            thermocouple (ThermocoupleType): The thermocouple type.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:TEMP:TC:TYPE {thermocouple.raw_value}")

    @mark_query
    def get_thermocouple_type(self) -> ThermocoupleType:
        """Queries the thermocouple type.

        Returns:
            ThermocoupleType: The thermocouple type.
        """
        return parse_enum(ThermocoupleType, self.query("SENS:TEMP:TC:TYPE?"))

    @mark_command
    def set_reference_junction(self, junction: ReferenceJunction) -> int:
        """Sets the reference junction type.

        Args:
            junction (ReferenceJunction): The reference junction type.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:TEMP:TC:RJUN:RSEL {junction.raw_value}")

    @mark_query
    def get_reference_junction(self) -> ReferenceJunction:
        """Queries the reference junction type.

        Returns:
            ReferenceJunction: The reference junction type.
        """
        return parse_enum(ReferenceJunction, self.query("SENS:TEMP:TC:RJUN:RSEL?"))

    @mark_command
    def set_simulated_junction_temperature(self, temperature: float) -> int:
        """Sets the simulated reference junction temperature.

        Args:
            temperature (float): The simulated reference junction temperature in the temperature unit. Range: 0 to 50 C, 32 to 122 F, or 273 to 323 K.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:TEMP:TC:RJUN:SIM {format_number(temperature)}")

    @mark_query
    def get_simulated_junction_temperature(self) -> float:
        """Queries the simulated reference junction temperature.

        Returns:
            float: The simulated reference junction temperature in the temperature unit.
        """
        return float(self.query("SENS:TEMP:TC:RJUN:SIM?"))

    @mark_command
    def set_junction_temperature_coefficient(self, coefficient: float) -> int:
        """Sets the temperature coefficient of the real reference junction.

        Args:
            coefficient (float): The temperature coefficient of the real reference junction in C/V. Range: -0.09999 to 0.09999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:TEMP:TC:RJUN:REAL:TCO {format_number(coefficient)}")

    @mark_query
    def get_junction_temperature_coefficient(self) -> float:
        """Queries the temperature coefficient of the real reference junction.

        Returns:
            float: The temperature coefficient of the real reference junction in C/V.
        """
        return float(self.query("SENS:TEMP:TC:RJUN:REAL:TCO?"))

    @mark_command
    def set_junction_voltage_offset(self, offset: float) -> int:
        """Sets the voltage offset at 0 C of the real reference junction.

        Args:
            offset (float): The voltage offset at 0 C of the real reference junction in V. Range: -0.09999 to 0.09999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:TEMP:TC:RJUN:REAL:OFFS {format_number(offset)}")

    @mark_query
    def get_junction_voltage_offset(self) -> float:
        """Queries the voltage offset at 0 C of the real reference junction.

        Returns:
            float: The voltage offset at 0 C of the real reference junction in V.
        """
        return float(self.query("SENS:TEMP:TC:RJUN:REAL:OFFS?"))

    @mark_command
    def set_diode_current_range(self, current: float) -> int:
        """Sets the diode test current range.

        Args:
            current (float): The diode test current range in A. Give the expected current, and the range of 10e-6, 100e-6 or 1e-3 that holds it is chosen. Range: 0 to 1e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:DIOD:CURR:RANG:UPP {format_number(current)}")

    @mark_query
    def get_diode_current_range(self) -> float:
        """Queries the diode test current range.

        Returns:
            float: The diode test current range in A.
        """
        return float(self.query("SENS:DIOD:CURR:RANG:UPP?"))

    @mark_command
    def set_continuity_threshold(self, threshold: float) -> int:
        """Sets the continuity threshold resistance.

        Args:
            threshold (float): The continuity threshold resistance in ohms. Range: 1 to 1000.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:CONT:THR {format_number(threshold)}")

    @mark_query
    def get_continuity_threshold(self) -> float:
        """Queries the continuity threshold resistance.

        Returns:
            float: The continuity threshold resistance in ohms.
        """
        return float(self.query("SENS:CONT:THR?"))

    """ READING HOLD """

    @mark_command
    def set_hold_window(self, window: float) -> int:
        """Sets the reading hold window.

        Args:
            window (float): The reading hold window in % of the seed reading. Range: 0.01 to 20.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:HOLD:WIND {format_number(window)}")

    @mark_query
    def get_hold_window(self) -> float:
        """Queries the reading hold window.

        Returns:
            float: The reading hold window in % of the seed reading.
        """
        return float(self.query("SENS:HOLD:WIND?"))

    @mark_command
    def set_hold_count(self, count: int) -> int:
        """Sets the reading hold count.

        Args:
            count (int): The reading hold count. Range: 2 to 100.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:HOLD:COUN {count}")

    @mark_query
    def get_hold_count(self) -> int:
        """Queries the reading hold count.

        Returns:
            int: The reading hold count.
        """
        return to_int(self.query("SENS:HOLD:COUN?"))

    @mark_command
    def set_hold(self, state: State) -> int:
        """Enables or disables the reading hold.

        Args:
            state (State): State.ON to enable or State.OFF to disable the reading hold.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:HOLD:STAT {state.raw_value}")

    @mark_query
    def get_hold(self) -> State:
        """Queries whether the reading hold is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SENS:HOLD:STAT?")))

    """ MATH, STATISTICS AND LIMIT TESTING """

    @mark_command
    def set_math_format(self, math_format: MathFormat) -> int:
        """Sets the math format.

        Args:
            math_format (MathFormat): The math format.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC:FORM {math_format.raw_value}")

    @mark_query
    def get_math_format(self) -> MathFormat:
        """Queries the math format.

        Returns:
            MathFormat: The math format.
        """
        return parse_enum(MathFormat, self.query("CALC:FORM?"))

    @mark_command
    def set_math_factor_m(self, factor: float) -> int:
        """Sets the mX+b "m" factor.

        Args:
            factor (float): The mX+b "m" factor. Range: -100e6 to 100e6.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC:KMAT:MMF {format_number(factor)}")

    @mark_query
    def get_math_factor_m(self) -> float:
        """Queries the mX+b "m" factor.

        Returns:
            float: The mX+b "m" factor.
        """
        return float(self.query("CALC:KMAT:MMF?"))

    @mark_command
    def set_math_factor_b(self, factor: float) -> int:
        """Sets the mX+b "b" factor.

        Args:
            factor (float): The mX+b "b" factor. Range: -100e6 to 100e6.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC:KMAT:MBF {format_number(factor)}")

    @mark_query
    def get_math_factor_b(self) -> float:
        """Queries the mX+b "b" factor.

        Returns:
            float: The mX+b "b" factor.
        """
        return float(self.query("CALC:KMAT:MBF?"))

    @mark_command
    def set_math_units(self, units: str) -> int:
        """Sets the units shown for an mX+b reading.

        Args:
            units (str): The units shown for an mX+b reading. Three letters, A to Z.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC:KMAT:MUN '{units}'")

    @mark_query
    def get_math_units(self) -> str:
        """Queries the units shown for an mX+b reading.

        Returns:
            str: The units shown for an mX+b reading.
        """
        return unquote(self.query("CALC:KMAT:MUN?"))

    @mark_command
    def set_math_percent_target(self, target: float) -> int:
        """Sets the percent calculation target value.

        Args:
            target (float): The percent calculation target value. Range: -1e8 to 1e8.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC:KMAT:PERC {format_number(target)}")

    @mark_query
    def get_math_percent_target(self) -> float:
        """Queries the percent calculation target value.

        Returns:
            float: The percent calculation target value.
        """
        return float(self.query("CALC:KMAT:PERC?"))

    @mark_command
    def acquire_percent_target(self) -> int:
        """Uses the present input as the target value of the percent calculation.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("CALC:KMAT:PERC:ACQ")

    @mark_command
    def set_math_state(self, state: State) -> int:
        """Enables or disables the math calculation.

        Args:
            state (State): State.ON to enable or State.OFF to disable the math calculation.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC:STAT {state.raw_value}")

    @mark_query
    def get_math_state(self) -> State:
        """Queries whether the math calculation is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("CALC:STAT?")))

    @mark_query
    def get_math_reading(self) -> float:
        """Reads the latest post-math reading.

        Returns:
            float: The reading, or the raw reading if math is off.
        """
        return first_number(self.query("CALC:DATA?"))

    @mark_command
    def set_statistic_format(self, statistic: StatisticFormat) -> int:
        """Sets the buffer statistic.

        Args:
            statistic (StatisticFormat): The buffer statistic.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC2:FORM {statistic.raw_value}")

    @mark_query
    def get_statistic_format(self) -> StatisticFormat:
        """Queries the buffer statistic.

        Returns:
            StatisticFormat: The buffer statistic.
        """
        return parse_enum(StatisticFormat, self.query("CALC2:FORM?"))

    @mark_command
    def set_statistic_state(self, state: State) -> int:
        """Enables or disables the buffer statistic calculation.

        Args:
            state (State): State.ON to enable or State.OFF to disable the buffer statistic calculation.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC2:STAT {state.raw_value}")

    @mark_query
    def get_statistic_state(self) -> State:
        """Queries whether the buffer statistic calculation is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("CALC2:STAT?")))

    @mark_command
    def calculate_statistic(self) -> int:
        """Performs the selected statistic on the buffer contents.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("CALC2:IMM")

    @mark_query
    def get_statistic(self) -> float:
        """Reads the result of the buffer statistic.

        Returns:
            float: The statistic.
        """
        return first_number(self.query("CALC2:DATA?"))

    @mark_command
    def set_limit_upper(self, limit: float) -> int:
        """Sets the upper limit.

        Args:
            limit (float): The upper limit. Range: -100e6 to 100e6.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC3:LIM:UPP {format_number(limit)}")

    @mark_query
    def get_limit_upper(self) -> float:
        """Queries the upper limit.

        Returns:
            float: The upper limit.
        """
        return float(self.query("CALC3:LIM:UPP?"))

    @mark_command
    def set_limit_lower(self, limit: float) -> int:
        """Sets the lower limit.

        Args:
            limit (float): The lower limit. Range: -100e6 to 100e6.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC3:LIM:LOW {format_number(limit)}")

    @mark_query
    def get_limit_lower(self) -> float:
        """Queries the lower limit.

        Returns:
            float: The lower limit.
        """
        return float(self.query("CALC3:LIM:LOW?"))

    @mark_command
    def set_limit_test(self, state: State) -> int:
        """Enables or disables the limit test.

        Args:
            state (State): State.ON to enable or State.OFF to disable the limit test.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC3:LIM:STAT {state.raw_value}")

    @mark_query
    def get_limit_test(self) -> State:
        """Queries whether the limit test is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("CALC3:LIM:STAT?")))

    @mark_query
    def get_limit_test_passed(self) -> bool:
        """Queries whether the limit test passed.

        Returns:
            bool: True if it passed. This follows the manual, which says 1 is a pass even though the command is named FAIL?.
        """
        return to_int(self.query("CALC3:LIM:FAIL?")) == 1

    @mark_command
    def clear_limit_failure(self) -> int:
        """Clears the limit test failure indication.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("CALC3:LIM:CLE")

    @mark_command
    def set_limit_auto_clear(self, state: State) -> int:
        """Enables or disables the clearing of the limit failure when the instrument goes idle.

        Args:
            state (State): State.ON to enable or State.OFF to disable the clearing of the limit failure when the instrument goes idle.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC3:LIM:CLE:AUTO {state.raw_value}")

    @mark_query
    def get_limit_auto_clear(self) -> State:
        """Queries whether the clearing of the limit failure when the instrument goes idle is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("CALC3:LIM:CLE:AUTO?")))

    @mark_command
    def recalculate_limits(self) -> int:
        """Re-runs the limit test on the present reading.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("CALC3:IMM")

    """ UNITS """

    @mark_command
    def set_temperature_unit(self, unit: TemperatureUnit) -> int:
        """Sets the temperature unit.

        Args:
            unit (TemperatureUnit): The temperature unit.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"UNIT:TEMP {unit.raw_value}")

    @mark_query
    def get_temperature_unit(self) -> TemperatureUnit:
        """Queries the temperature unit.

        Returns:
            TemperatureUnit: The temperature unit.
        """
        return parse_enum(TemperatureUnit, self.query("UNIT:TEMP?"))

    @mark_command
    def set_ac_voltage_unit(self, unit: VoltageUnit) -> int:
        """Sets the AC voltage unit.

        Args:
            unit (VoltageUnit): The AC voltage unit.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"UNIT:VOLT:AC {unit.raw_value}")

    @mark_query
    def get_ac_voltage_unit(self) -> VoltageUnit:
        """Queries the AC voltage unit.

        Returns:
            VoltageUnit: The AC voltage unit.
        """
        return parse_enum(VoltageUnit, self.query("UNIT:VOLT:AC?"))

    @mark_command
    def set_dc_voltage_unit(self, unit: VoltageUnit) -> int:
        """Sets the DC voltage unit.

        Args:
            unit (VoltageUnit): The DC voltage unit.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"UNIT:VOLT:DC {unit.raw_value}")

    @mark_query
    def get_dc_voltage_unit(self) -> VoltageUnit:
        """Queries the DC voltage unit.

        Returns:
            VoltageUnit: The DC voltage unit.
        """
        return parse_enum(VoltageUnit, self.query("UNIT:VOLT:DC?"))

    @mark_command
    def set_ac_db_reference(self, reference: float) -> int:
        """Sets the AC dB reference.

        Args:
            reference (float): The AC dB reference in V. Range: 1e-7 to 1000.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"UNIT:VOLT:AC:DB:REF {format_number(reference)}")

    @mark_query
    def get_ac_db_reference(self) -> float:
        """Queries the AC dB reference.

        Returns:
            float: The AC dB reference in V.
        """
        return float(self.query("UNIT:VOLT:AC:DB:REF?"))

    @mark_command
    def set_ac_dbm_impedance(self, impedance: int) -> int:
        """Sets the AC dBm reference impedance.

        Args:
            impedance (int): The AC dBm reference impedance. Range: 1 to 9999 ohms.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"UNIT:VOLT:AC:DBM:IMP {impedance}")

    @mark_query
    def get_ac_dbm_impedance(self) -> int:
        """Queries the AC dBm reference impedance.

        Returns:
            int: The AC dBm reference impedance.
        """
        return to_int(self.query("UNIT:VOLT:AC:DBM:IMP?"))

    @mark_command
    def set_dc_db_reference(self, reference: float) -> int:
        """Sets the DC dB reference.

        Args:
            reference (float): The DC dB reference in V. Range: 1e-7 to 1000.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"UNIT:VOLT:DC:DB:REF {format_number(reference)}")

    @mark_query
    def get_dc_db_reference(self) -> float:
        """Queries the DC dB reference.

        Returns:
            float: The DC dB reference in V.
        """
        return float(self.query("UNIT:VOLT:DC:DB:REF?"))

    @mark_command
    def set_dc_dbm_impedance(self, impedance: int) -> int:
        """Sets the DC dBm reference impedance.

        Args:
            impedance (int): The DC dBm reference impedance. Range: 1 to 9999 ohms.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"UNIT:VOLT:DC:DBM:IMP {impedance}")

    @mark_query
    def get_dc_dbm_impedance(self) -> int:
        """Queries the DC dBm reference impedance.

        Returns:
            int: The DC dBm reference impedance.
        """
        return to_int(self.query("UNIT:VOLT:DC:DBM:IMP?"))

    """ DISPLAY """

    @mark_command
    def set_display_enabled(self, state: State) -> int:
        """Enables or disables the front panel display and controls.

        Args:
            state (State): State.ON to enable or State.OFF to disable the front panel display and controls.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"DISP:ENAB {state.raw_value}")

    @mark_query
    def get_display_enabled(self) -> State:
        """Queries whether the front panel display and controls is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("DISP:ENAB?")))

    @mark_command
    def set_display_text(self, text: str) -> int:
        """Sets the display message.

        Args:
            text (str): The display message. At most 12 characters.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"DISP:TEXT:DATA '{text}'")

    @mark_query
    def get_display_text(self) -> str:
        """Queries the display message.

        Returns:
            str: The display message.
        """
        return unquote(self.query("DISP:TEXT:DATA?"))

    @mark_command
    def set_display_text_state(self, state: State) -> int:
        """Enables or disables the display message.

        Args:
            state (State): State.ON to enable or State.OFF to disable the display message.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"DISP:TEXT:STAT {state.raw_value}")

    @mark_query
    def get_display_text_state(self) -> State:
        """Queries whether the display message is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("DISP:TEXT:STAT?")))

    """ BUFFER """

    @mark_command
    def clear_buffer(self) -> int:
        """Clears the readings from the buffer.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("TRAC:CLE")

    @mark_query
    def get_buffer_free(self) -> list[int]:
        """Queries the memory available for the buffer.

        Returns:
            list[int]: The bytes available, then the bytes in use.
        """
        return to_ints(self.query("TRAC:FREE?"))

    @mark_command
    def set_buffer_size(self, size: int) -> int:
        """Sets the buffer size.

        Args:
            size (int): The buffer size. Range: 2 to 1024.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRAC:POIN {size}")

    @mark_query
    def get_buffer_size(self) -> int:
        """Queries the buffer size.

        Returns:
            int: The buffer size.
        """
        return to_int(self.query("TRAC:POIN?"))

    @mark_command
    def set_buffer_feed(self, feed: TraceFeed) -> int:
        """Sets the source of the buffer readings.

        Args:
            feed (TraceFeed): The source of the buffer readings.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRAC:FEED {feed.raw_value}")

    @mark_query
    def get_buffer_feed(self) -> TraceFeed:
        """Queries the source of the buffer readings.

        Returns:
            TraceFeed: The source of the buffer readings.
        """
        return parse_enum(TraceFeed, self.query("TRAC:FEED?"))

    @mark_command
    def set_buffer_control(self, control: TraceControl) -> int:
        """Sets the buffer control.

        Args:
            control (TraceControl): The buffer control.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRAC:FEED:CONT {control.raw_value}")

    @mark_query
    def get_buffer_control(self) -> TraceControl:
        """Queries the buffer control.

        Returns:
            TraceControl: The buffer control.
        """
        return parse_enum(TraceControl, self.query("TRAC:FEED:CONT?"))

    @mark_query
    def get_buffer_data(self) -> list[float]:
        """Reads all the readings in the buffer.

        Returns:
            list[float]: The readings.
        """
        return to_floats(self.query("TRAC:DATA?"))

    """ TRIGGER MODEL """

    @mark_command
    def initiate(self) -> int:
        """Takes the instrument out of idle.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("INIT:IMM")

    @mark_command
    def abort_trigger(self) -> int:
        """Resets the trigger system and goes idle.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("ABOR")

    @mark_command
    def set_continuous_initiation(self, state: State) -> int:
        """Enables or disables the continuous initiation.

        Args:
            state (State): State.ON to enable or State.OFF to disable the continuous initiation.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"INIT:CONT {state.raw_value}")

    @mark_query
    def get_continuous_initiation(self) -> State:
        """Queries whether the continuous initiation is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("INIT:CONT?")))

    @mark_command
    def set_trigger_count(self, count: float) -> int:
        """Sets the trigger count.

        Args:
            count (float): The trigger count. Use math.inf for an infinite count. Range: 1 to 9999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRIG:COUN {format_count(count)}")

    @mark_query
    def get_trigger_count(self) -> float:
        """Queries the trigger count.

        Returns:
            float: The trigger count.
        """
        return float(self.query("TRIG:COUN?"))

    @mark_command
    def set_trigger_delay(self, delay: float) -> int:
        """Sets the trigger delay.

        Args:
            delay (float): The trigger delay in s. Range: 0 to 999999.999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRIG:DEL {format_number(delay)}")

    @mark_query
    def get_trigger_delay(self) -> float:
        """Queries the trigger delay.

        Returns:
            float: The trigger delay in s.
        """
        return float(self.query("TRIG:DEL?"))

    @mark_command
    def set_trigger_auto_delay(self, state: State) -> int:
        """Enables or disables the automatic trigger delay.

        Args:
            state (State): State.ON to enable or State.OFF to disable the automatic trigger delay.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRIG:DEL:AUTO {state.raw_value}")

    @mark_query
    def get_trigger_auto_delay(self) -> State:
        """Queries whether the automatic trigger delay is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("TRIG:DEL:AUTO?")))

    @mark_command
    def set_trigger_source(self, source: TriggerSource) -> int:
        """Sets the trigger source.

        Args:
            source (TriggerSource): The trigger source.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRIG:SOUR {source.raw_value}")

    @mark_query
    def get_trigger_source(self) -> TriggerSource:
        """Queries the trigger source.

        Returns:
            TriggerSource: The trigger source.
        """
        return parse_enum(TriggerSource, self.query("TRIG:SOUR?"))

    @mark_command
    def set_trigger_timer(self, interval: float) -> int:
        """Sets the trigger timer interval.

        Args:
            interval (float): The trigger timer interval in s. Range: 0.001 to 999999.999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRIG:TIM {format_number(interval)}")

    @mark_query
    def get_trigger_timer(self) -> float:
        """Queries the trigger timer interval.

        Returns:
            float: The trigger timer interval in s.
        """
        return float(self.query("TRIG:TIM?"))

    @mark_command
    def bypass_trigger_control(self) -> int:
        """Bypasses the trigger control source.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("TRIG:SIGN")

    @mark_command
    def set_sample_count(self, count: int) -> int:
        """Sets the sample count.

        Args:
            count (int): The sample count. Range: 1 to 1024.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SAMP:COUN {count}")

    @mark_query
    def get_sample_count(self) -> int:
        """Queries the sample count.

        Returns:
            int: The sample count.
        """
        return to_int(self.query("SAMP:COUN?"))

    """ SCANNER CARD """

    @mark_command
    def close_channel(self, channel: int) -> int:
        """Closes one channel, or channel pair for a 4-wire function, opening any other first.

        Args:
            channel (int): The channel, 1 to 10, or 1 to 5 for a 4-wire function.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ROUT:CLOS (@{channel})")

    @mark_query
    def get_closed_channel(self) -> list[int]:
        """Queries the closed channel.

        Returns:
            list[int]: The closed channel.
        """
        return parse_channels(self.query("ROUT:CLOS:STAT?"))

    @mark_command
    def open_all_channels(self) -> int:
        """Opens all the input channels.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("ROUT:OPEN:ALL")

    @mark_command
    def close_channels(self, channels: list[int]) -> int:
        """Closes several channels at once. Channel 11 is the 2-pole/4-pole relay, closed for 2-pole.

        Args:
            channels (list[int]): The channels, 1 to 11.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ROUT:MULT:CLOS {format_channels(channels)}")

    @mark_query
    def get_closed_channels(self) -> list[int]:
        """Queries all the closed channels.

        Returns:
            list[int]: The closed channels.
        """
        return parse_channels(self.query("ROUT:MULT:CLOS:STAT?"))

    @mark_command
    def open_channels(self, channels: list[int]) -> int:
        """Opens several channels.

        Args:
            channels (list[int]): The channels, 1 to 11.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ROUT:MULT:OPEN {format_channels(channels)}")

    @mark_command
    def set_internal_scan_list(self, channels: list[int]) -> int:
        """Sets the channels of the internal scan. They must be consecutive.

        Args:
            channels (list[int]): Two to ten consecutive channels, 1 to 10.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ROUT:SCAN {format_channels(channels)}")

    @mark_query
    def get_internal_scan_list(self) -> list[int]:
        """Queries the internal scan list.

        Returns:
            list[int]: The channels.
        """
        return parse_channels(self.query("ROUT:SCAN?"))

    @mark_command
    def set_external_scan_list(self, channels: list[int]) -> int:
        """Sets the channels of the external scan, made through a switch system.

        Args:
            channels (list[int]): Two to 800 channels.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ROUT:SCAN:EXT {format_channels(channels)}")

    @mark_query
    def get_external_scan_list(self) -> list[int]:
        """Queries the external scan list.

        Returns:
            list[int]: The channels.
        """
        return parse_channels(self.query("ROUT:SCAN:EXT?"))

    @mark_command
    def set_scan_mode(self, mode: ScanMode) -> int:
        """Sets the scan operation.

        Args:
            mode (ScanMode): The scan operation.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ROUT:SCAN:LSEL {mode.raw_value}")

    @mark_query
    def get_scan_mode(self) -> ScanMode:
        """Queries the scan operation.

        Returns:
            ScanMode: The scan operation.
        """
        return parse_enum(ScanMode, self.query("ROUT:SCAN:LSEL?"))

    """ SYSTEM """

    @mark_command
    def preset(self) -> int:
        """Returns the instrument to its preset defaults.

        `SYST:PRES` is slow to respond, so this waits for `*OPC?` before returning.

        Returns:
            int: Status code indicating the success of the operation.
        """
        result = self.command("SYST:PRES")
        self.query("*OPC?")
        return result

    @mark_command
    def set_power_on_setup(self, setup: PowerOnSetup) -> int:
        """Sets the power-on setup.

        Args:
            setup (PowerOnSetup): The power-on setup.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SYST:POS {setup.raw_value}")

    @mark_query
    def get_power_on_setup(self) -> PowerOnSetup:
        """Queries the power-on setup.

        Returns:
            PowerOnSetup: The power-on setup.
        """
        return parse_enum(PowerOnSetup, self.query("SYST:POS?"))

    @mark_query
    def get_front_inputs_selected(self) -> bool:
        """Queries whether the front panel inputs are selected.

        Returns:
            bool: True for the front inputs, False for the rear.
        """
        return to_int(self.query("SYST:FRSW?")) == 1

    @mark_query
    def get_scpi_version(self) -> str:
        """Queries the revision of the SCPI standard.

        Returns:
            str: The SCPI version.
        """
        return unquote(self.query("SYST:VERS?"))

    @mark_command
    def set_autozero(self, state: State) -> int:
        """Enables or disables the autozero.

        Args:
            state (State): State.ON to enable or State.OFF to disable the autozero.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SYST:AZER:STAT {state.raw_value}")

    @mark_query
    def get_autozero(self) -> State:
        """Queries whether the autozero is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SYST:AZER:STAT?")))

    @mark_query
    def get_line_frequency(self) -> float:
        """Queries the power line frequency.

        Returns:
            float: The frequency in Hz.
        """
        return float(self.query("SYST:LFR?"))

    @mark_command
    def set_beeper(self, state: State) -> int:
        """Enables or disables the beeper.

        Args:
            state (State): State.ON to enable or State.OFF to disable the beeper.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SYST:BEEP:STAT {state.raw_value}")

    @mark_query
    def get_beeper(self) -> State:
        """Queries whether the beeper is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SYST:BEEP:STAT?")))

    @mark_command
    def set_key_click(self, state: State) -> int:
        """Enables or disables the key click.

        Args:
            state (State): State.ON to enable or State.OFF to disable the key click.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SYST:KCL {state.raw_value}")

    @mark_query
    def get_key_click(self) -> State:
        """Queries whether the key click is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SYST:KCL?")))

    @mark_command
    def press_key(self, key: Key) -> int:
        """Simulates a front panel key press.

        Args:
            key (Key): The key to press.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SYST:KEY {key.raw_value}")

    @mark_query
    def get_last_key(self) -> Key:
        """Queries the last key pressed.

        Returns:
            Key: The last key pressed.
        """
        return Key.from_raw_value(to_int(self.query("SYST:KEY?")))
