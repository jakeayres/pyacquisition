from ...core.instrument import BaseEnum, Instrument, mark_command, mark_query
from ._scpi import (
    FilterControl,
    State,
    StatusRegister,
    TraceControl,
    TraceFeed,
    first_number,
    format_count,
    format_duration,
    format_list,
    format_number,
    parse_enum,
    parse_error,
    to_floats,
    to_int,
    unquote,
)


class DisplayLine(BaseEnum):
    TOP = (1, "Top line")
    BOTTOM = (2, "Bottom line")


class OutputResponse(BaseEnum):
    FAST = ("FAST", "Fast")
    SLOW = ("SLOW", "Slow")


class InnerShield(BaseEnum):
    OUTPUT_LOW = ("OLOW", "Output low")
    GUARD = ("GUAR", "Cable guard")


class SweepSpacing(BaseEnum):
    LINEAR = ("LIN", "Linear")
    LOGARITHMIC = ("LOG", "Logarithmic")
    LIST = ("LIST", "List")


class SweepRanging(BaseEnum):
    AUTO = ("AUTO", "Auto")
    BEST = ("BEST", "Best fixed")
    FIXED = ("FIX", "Fixed")


class Ranging(BaseEnum):
    BEST = ("BEST", "Best fixed")
    FIXED = ("FIX", "Fixed")


class WaveFunction(BaseEnum):
    SINUSOID = ("SIN", "Sinusoid")
    SQUARE = ("SQU", "Square")
    RAMP = ("RAMP", "Ramp")
    ARBITRARY_0 = ("ARB0", "Arbitrary 0")
    ARBITRARY_1 = ("ARB1", "Arbitrary 1")
    ARBITRARY_2 = ("ARB2", "Arbitrary 2")
    ARBITRARY_3 = ("ARB3", "Arbitrary 3")
    ARBITRARY_4 = ("ARB4", "Arbitrary 4")


class ListParameter(BaseEnum):
    CURRENT = ("CURR", "Current")
    DELAY = ("DEL", "Delay")
    COMPLIANCE = ("COMP", "Compliance")


class ReadingUnits(BaseEnum):
    VOLTS = ("V", "Volts")
    OHMS = ("OHMS", "Ohms")
    WATTS = ("W", "Watts")
    SIEMENS = ("SIEM", "Siemens")


class PowerType(BaseEnum):
    PEAK = ("PEAK", "Peak")
    AVERAGE = ("AVER", "Average")


class ReadingElement(BaseEnum):
    READING = ("READ", "Reading")
    TIMESTAMP = ("TST", "Timestamp")
    UNITS = ("UNIT", "Units")
    READING_NUMBER = ("RNUM", "Reading number")
    SOURCE = ("SOUR", "Source level")
    COMPLIANCE = ("COMP", "Compliance state")
    AVERAGE_VOLTAGE = ("AVOL", "Average voltage")


class MathFormat(BaseEnum):
    NONE = ("NONE", "None")
    MX_PLUS_B = ("MXB", "mX+b")
    RECIPROCAL = ("REC", "m/X+b")


class StatisticFormat(BaseEnum):
    MEAN = ("MEAN", "Mean")
    STANDARD_DEVIATION = ("SDEV", "Standard deviation")
    MAXIMUM = ("MAX", "Maximum")
    MINIMUM = ("MIN", "Minimum")
    PEAK_TO_PEAK = ("PKPK", "Peak to peak")


class TimestampFormat(BaseEnum):
    ABSOLUTE = ("ABS", "Absolute")
    DELTA = ("DELT", "Delta")


class TriggerLayer(BaseEnum):
    ARM = ("ARM", "Arm layer")
    TRIGGER = ("TRIG", "Trigger layer")


class ArmSource(BaseEnum):
    IMMEDIATE = ("IMM", "Immediate")
    TIMER = ("TIM", "Timer")
    BUS = ("BUS", "Bus")
    TRIGGER_LINK = ("TLIN", "Trigger link")
    BSTEST = ("BST", "BSTest")
    PSTEST = ("PST", "PSTest")
    NSTEST = ("NST", "NSTest")
    MANUAL = ("MAN", "Manual")


class TriggerSource(BaseEnum):
    IMMEDIATE = ("IMM", "Immediate")
    TRIGGER_LINK = ("TLIN", "Trigger link")


class BypassDirection(BaseEnum):
    SOURCE = ("SOUR", "Source")
    ACCEPTOR = ("ACC", "Acceptor")


class ArmOutput(BaseEnum):
    TRIGGER_ENTER = ("TENT", "On entering the layer")
    TRIGGER_EXIT = ("TEX", "On exiting the layer")
    NONE = ("NONE", "None")


class TriggerOutput(BaseEnum):
    SOURCE = ("SOUR", "After the source is set")
    DELAY = ("DEL", "After the delay")
    NONE = ("NONE", "None")


class PowerOnSetup(BaseEnum):
    RST = ("RST", "*RST defaults")
    PRESET = ("PRES", "Preset defaults")
    SAVED_0 = ("SAV0", "Saved setup 0")
    SAVED_1 = ("SAV1", "Saved setup 1")
    SAVED_2 = ("SAV2", "Saved setup 2")
    SAVED_3 = ("SAV3", "Saved setup 3")
    SAVED_4 = ("SAV4", "Saved setup 4")


class Key(BaseEnum):
    """Front panel key codes for the Model 6221, as used by SYSTem:KEY."""

    RANGE_UP = (1, "Range up")
    WAVE = (2, "WAVE")
    AMPL = (3, "AMPL")
    MENU = (4, "MENU")
    SWEEP = (5, "SWP")
    DISPLAY = (6, "DISP")
    SETUP = (7, "SETUP")
    LOCAL = (8, "LOCAL")
    AUTO = (9, "AUTO")
    FREQ = (10, "FREQ")
    EXIT = (11, "EXIT")
    CONDUCTANCE = (12, "COND")
    TRIGGER = (13, "TRIG")
    TRIAX = (14, "TRIAX")
    FILTER = (15, "FILT")
    CONFIG = (16, "CONFIG")
    RANGE_DOWN = (17, "Range down")
    ENTER = (18, "ENTER")
    DELTA = (19, "DELTA")
    UNITS = (20, "UNITS")
    AVERAGE = (21, "AVG")
    PRESENT = (22, "PRES")
    COMM = (23, "COMM")
    OUTPUT = (24, "OUTPUT On/Off")
    PULSE = (26, "PULSE")
    RECALL = (27, "RECALL")
    MATH = (28, "MATH")
    DC = (29, "DC")
    ADDRESS = (30, "ADDR")
    SAVE = (31, "SAVE")
    KNOB_PUSH = (33, "Push rotary knob")
    CURSOR_RIGHT = (39, "Cursor right")
    CURSOR_LEFT = (40, "Cursor left")
    KNOB_LEFT = (43, "Turn rotary knob left")
    KNOB_RIGHT = (45, "Turn rotary knob right")


class Keithley_6221(Instrument):
    """Class for controlling the Keithley 6221 AC and DC current source.

    The delta, pulse delta and differential conductance commands need a Keithley
    2182 or 2182A nanovoltmeter connected over the trigger link and RS-232 port.
    """

    def __init__(self, *args, **kwargs):
        """Initializes the Keithley 6221 instrument.

        Clears the status structure and selects ASCII formats, because the
        methods here parse ASCII replies.
        """
        super().__init__(*args, **kwargs)
        self.clear()
        self.command("FORM:SREG ASC")
        self.command("FORM ASC")

    """ IEEE-488.2 COMMON COMMANDS """

    @mark_query
    def identify(self) -> str:
        """Identifies the instrument.

        Returns:
            str: The identification string of the instrument.
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
            str: The model numbers of any installed options.
        """
        return self.query("*OPT?")

    @mark_command
    def save_setup(self, location: int) -> int:
        """Saves the present setup to memory.

        Args:
            location (int): The memory location, 0 to 4.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"*SAV {location}")

    @mark_command
    def recall_setup(self, location: int) -> int:
        """Recalls a setup from memory.

        Args:
            location (int): The memory location, 0 to 4.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"*RCL {location}")

    @mark_command
    def trigger(self) -> int:
        """Sends a bus trigger. Only acts if BUS is the arm control source.

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
        """Resets the operation, measurement and questionable enable registers to 0.

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
        """Reads and removes the latest entry in the error queue.

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
    def set_display_text(self, line: DisplayLine, text: str) -> int:
        """Sets the display message.

        Args:
            line (DisplayLine): The display line (top or bottom).
            text (str): The display message.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"DISP:WIND{line.raw_value}:TEXT:DATA '{text}'")

    @mark_query
    def get_display_text(self, line: DisplayLine) -> str:
        """Queries the display message.

        Args:
            line (DisplayLine): The display line (top or bottom).

        Returns:
            str: The display message.
        """
        return unquote(self.query(f"DISP:WIND{line.raw_value}:TEXT:DATA?"))

    @mark_command
    def set_display_text_state(self, line: DisplayLine, state: State) -> int:
        """Enables or disables the display message.

        Args:
            line (DisplayLine): The display line (top or bottom).
            state (State): State.ON to enable or State.OFF to disable the display message.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"DISP:WIND{line.raw_value}:TEXT:STAT {state.raw_value}")

    @mark_query
    def get_display_text_state(self, line: DisplayLine) -> State:
        """Queries whether the display message is enabled.

        Args:
            line (DisplayLine): The display line (top or bottom).

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(
            to_int(self.query(f"DISP:WIND{line.raw_value}:TEXT:STAT?"))
        )

    @mark_query
    def get_display_text_attributes(self, line: DisplayLine) -> str:
        """Queries whether each character of the display message is blinking.

        Args:
            line (DisplayLine): The display line (top or bottom).

        Returns:
            str: Blinking (1) or not blinking (0) for each character.
        """
        return unquote(self.query(f"DISP:WIND{line.raw_value}:ATTR?"))

    """ OUTPUT """

    @mark_command
    def set_output_state(self, state: State) -> int:
        """Enables or disables the current source output.

        Args:
            state (State): State.ON to enable or State.OFF to disable the current source output.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"OUTP {state.raw_value}")

    @mark_query
    def get_output_state(self) -> State:
        """Queries whether the current source output is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("OUTP?")))

    @mark_command
    def set_low_to_earth(self, state: State) -> int:
        """Enables or disables the connection of output low to earth ground.

        Args:
            state (State): State.ON to enable or State.OFF to disable the connection of output low to earth ground.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"OUTP:LTE {state.raw_value}")

    @mark_query
    def get_low_to_earth(self) -> State:
        """Queries whether the connection of output low to earth ground is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("OUTP:LTE?")))

    @mark_command
    def set_inner_shield(self, shield: InnerShield) -> int:
        """Sets the triax inner shield connection.

        Args:
            shield (InnerShield): The triax inner shield connection.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"OUTP:ISH {shield.raw_value}")

    @mark_query
    def get_inner_shield(self) -> InnerShield:
        """Queries the triax inner shield connection.

        Returns:
            InnerShield: The triax inner shield connection.
        """
        return parse_enum(InnerShield, self.query("OUTP:ISH?"))

    @mark_command
    def set_output_response(self, response: OutputResponse) -> int:
        """Sets the output response.

        Args:
            response (OutputResponse): The output response.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"OUTP:RESP {response.raw_value}")

    @mark_query
    def get_output_response(self) -> OutputResponse:
        """Queries the output response.

        Returns:
            OutputResponse: The output response.
        """
        return parse_enum(OutputResponse, self.query("OUTP:RESP?"))

    @mark_query
    def get_interlock_closed(self) -> bool:
        """Queries whether the interlock is closed.

        Returns:
            bool: True if the interlock is closed and the output can be enabled, False if it is tripped.
        """
        return to_int(self.query("OUTP:INT:TRIP?")) == 1

    """ CURRENT SOURCE """

    @mark_command
    def clear_source(self) -> int:
        """Sets the output to zero and then turns the output off.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SOUR:CLE")

    @mark_command
    def set_current(self, current: float) -> int:
        """Sets the output current.

        Args:
            current (float): The output current in A. Range: -105e-3 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:CURR {format_number(current)}")

    @mark_query
    def get_current(self) -> float:
        """Queries the output current.

        Returns:
            float: The output current in A.
        """
        return float(self.query("SOUR:CURR?"))

    @mark_command
    def set_current_range(self, range: float) -> int:
        """Sets the source range.

        Args:
            range (float): The source range in A. Range: -105e-3 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:CURR:RANG {format_number(range)}")

    @mark_query
    def get_current_range(self) -> float:
        """Queries the source range.

        Returns:
            float: The source range in A.
        """
        return float(self.query("SOUR:CURR:RANG?"))

    @mark_command
    def set_auto_range(self, state: State) -> int:
        """Enables or disables the source auto range.

        Args:
            state (State): State.ON to enable or State.OFF to disable the source auto range.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:CURR:RANG:AUTO {state.raw_value}")

    @mark_query
    def get_auto_range(self) -> State:
        """Queries whether the source auto range is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SOUR:CURR:RANG:AUTO?")))

    @mark_command
    def set_compliance(self, compliance: float) -> int:
        """Sets the voltage compliance.

        Args:
            compliance (float): The voltage compliance in V. Range: 0.1 to 105.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:CURR:COMP {format_number(compliance)}")

    @mark_query
    def get_compliance(self) -> float:
        """Queries the voltage compliance.

        Returns:
            float: The voltage compliance in V.
        """
        return float(self.query("SOUR:CURR:COMP?"))

    @mark_command
    def set_analog_filter(self, state: State) -> int:
        """Enables or disables the analog filter.

        Args:
            state (State): State.ON to enable or State.OFF to disable the analog filter.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:CURR:FILT {state.raw_value}")

    @mark_query
    def get_analog_filter(self) -> State:
        """Queries whether the analog filter is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SOUR:CURR:FILT?")))

    """ SWEEPS """

    @mark_command
    def set_sweep_start(self, start: float) -> int:
        """Sets the sweep start current.

        Args:
            start (float): The sweep start current in A. Range: -105e-3 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:CURR:STAR {format_number(start)}")

    @mark_query
    def get_sweep_start(self) -> float:
        """Queries the sweep start current.

        Returns:
            float: The sweep start current in A.
        """
        return float(self.query("SOUR:CURR:STAR?"))

    @mark_command
    def set_sweep_stop(self, stop: float) -> int:
        """Sets the sweep stop current.

        Args:
            stop (float): The sweep stop current in A. Range: -105e-3 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:CURR:STOP {format_number(stop)}")

    @mark_query
    def get_sweep_stop(self) -> float:
        """Queries the sweep stop current.

        Returns:
            float: The sweep stop current in A.
        """
        return float(self.query("SOUR:CURR:STOP?"))

    @mark_command
    def set_sweep_step(self, step: float) -> int:
        """Sets the sweep step current.

        Args:
            step (float): The sweep step current in A. Range: 1e-13 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:CURR:STEP {format_number(step)}")

    @mark_query
    def get_sweep_step(self) -> float:
        """Queries the sweep step current.

        Returns:
            float: The sweep step current in A.
        """
        return float(self.query("SOUR:CURR:STEP?"))

    @mark_command
    def set_sweep_center(self, center: float) -> int:
        """Sets the sweep center current.

        Args:
            center (float): The sweep center current in A. Range: -105e-3 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:CURR:CENT {format_number(center)}")

    @mark_query
    def get_sweep_center(self) -> float:
        """Queries the sweep center current.

        Returns:
            float: The sweep center current in A.
        """
        return float(self.query("SOUR:CURR:CENT?"))

    @mark_command
    def set_sweep_span(self, span: float) -> int:
        """Sets the sweep span current.

        Args:
            span (float): The sweep span current in A. Range: 2e-13 to 210e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:CURR:SPAN {format_number(span)}")

    @mark_query
    def get_sweep_span(self) -> float:
        """Queries the sweep span current.

        Returns:
            float: The sweep span current in A.
        """
        return float(self.query("SOUR:CURR:SPAN?"))

    @mark_command
    def set_source_delay(self, delay: float) -> int:
        """Sets the source delay.

        Args:
            delay (float): The source delay in s. Range: 1e-3 to 999999.999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DEL {format_number(delay)}")

    @mark_query
    def get_source_delay(self) -> float:
        """Queries the source delay.

        Returns:
            float: The source delay in s.
        """
        return float(self.query("SOUR:DEL?"))

    @mark_command
    def set_sweep_spacing(self, spacing: SweepSpacing) -> int:
        """Sets the sweep type.

        Args:
            spacing (SweepSpacing): The sweep type.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:SWE:SPAC {spacing.raw_value}")

    @mark_query
    def get_sweep_spacing(self) -> SweepSpacing:
        """Queries the sweep type.

        Returns:
            SweepSpacing: The sweep type.
        """
        return parse_enum(SweepSpacing, self.query("SOUR:SWE:SPAC?"))

    @mark_command
    def set_sweep_points(self, points: int) -> int:
        """Sets the number of sweep points.

        Args:
            points (int): The number of sweep points. Range: 1 to 65535.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:SWE:POIN {points}")

    @mark_query
    def get_sweep_points(self) -> int:
        """Queries the number of sweep points.

        Returns:
            int: The number of sweep points.
        """
        return to_int(self.query("SOUR:SWE:POIN?"))

    @mark_command
    def set_sweep_ranging(self, ranging: SweepRanging) -> int:
        """Sets the sweep ranging.

        Args:
            ranging (SweepRanging): The sweep ranging.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:SWE:RANG {ranging.raw_value}")

    @mark_query
    def get_sweep_ranging(self) -> SweepRanging:
        """Queries the sweep ranging.

        Returns:
            SweepRanging: The sweep ranging.
        """
        return parse_enum(SweepRanging, self.query("SOUR:SWE:RANG?"))

    @mark_command
    def set_sweep_count(self, count: float) -> int:
        """Sets the number of sweeps.

        Args:
            count (float): The number of sweeps. Use math.inf for an infinite count. Range: 1 to 9999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:SWE:COUN {format_count(count)}")

    @mark_query
    def get_sweep_count(self) -> float:
        """Queries the number of sweeps.

        Returns:
            float: The number of sweeps.
        """
        return float(self.query("SOUR:SWE:COUN?"))

    @mark_command
    def set_sweep_compliance_abort(self, state: State) -> int:
        """Enables or disables the abort of the sweep on compliance.

        Args:
            state (State): State.ON to enable or State.OFF to disable the abort of the sweep on compliance.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:SWE:CAB {state.raw_value}")

    @mark_query
    def get_sweep_compliance_abort(self) -> State:
        """Queries whether the abort of the sweep on compliance is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SOUR:SWE:CAB?")))

    @mark_command
    def arm_sweep(self) -> int:
        """Arms the sweep.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SOUR:SWE:ARM")

    @mark_command
    def abort_sweep(self) -> int:
        """Aborts a sweep, delta, pulse delta or differential conductance test immediately.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SOUR:SWE:ABOR")

    """ CUSTOM SWEEP LISTS """

    @mark_command
    def set_list(self, parameter: ListParameter, values: list[float]) -> int:
        """Defines a list of values for a custom sweep.

        Args:
            parameter (ListParameter): Which list to define.
            values (list[float]): The values: currents in A, delays in s or compliances in V.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:LIST:{parameter.raw_value} {format_list(values)}")

    @mark_command
    def append_list(self, parameter: ListParameter, values: list[float]) -> int:
        """Adds values to the end of a custom sweep list.

        Args:
            parameter (ListParameter): Which list to extend.
            values (list[float]): The values to add.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(
            f"SOUR:LIST:{parameter.raw_value}:APP {format_list(values)}"
        )

    @mark_query
    def get_list(self, parameter: ListParameter) -> list[float]:
        """Queries a custom sweep list.

        Args:
            parameter (ListParameter): Which list to read.

        Returns:
            list[float]: The values in the list.
        """
        return to_floats(self.query(f"SOUR:LIST:{parameter.raw_value}?"))

    @mark_query
    def get_list_points(self, parameter: ListParameter) -> int:
        """Queries the number of values in a custom sweep list.

        Args:
            parameter (ListParameter): Which list to count.

        Returns:
            int: The number of values.
        """
        return to_int(self.query(f"SOUR:LIST:{parameter.raw_value}:POIN?"))

    """ DELTA """

    @mark_query
    def get_nanovoltmeter_present(self) -> bool:
        """Queries whether a 2182 or 2182A nanovoltmeter is connected.

        Returns:
            bool: True if a nanovoltmeter is connected.
        """
        return to_int(self.query("SOUR:DELT:NVPR?")) == 1

    @mark_command
    def set_delta_high(self, high: float) -> int:
        """Sets the delta high source value.

        Args:
            high (float): The delta high source value in A. Range: 0 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DELT:HIGH {format_number(high)}")

    @mark_query
    def get_delta_high(self) -> float:
        """Queries the delta high source value.

        Returns:
            float: The delta high source value in A.
        """
        return float(self.query("SOUR:DELT:HIGH?"))

    @mark_command
    def set_delta_low(self, low: float) -> int:
        """Sets the delta low source value.

        Args:
            low (float): The delta low source value in A. Range: 0 to -105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DELT:LOW {format_number(low)}")

    @mark_query
    def get_delta_low(self) -> float:
        """Queries the delta low source value.

        Returns:
            float: The delta low source value in A.
        """
        return float(self.query("SOUR:DELT:LOW?"))

    @mark_command
    def set_delta_delay(self, delay: float) -> int:
        """Sets the delta delay.

        Args:
            delay (float): The delta delay in s. Range: 1e-3 to 9999.999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DELT:DEL {format_number(delay)}")

    @mark_query
    def get_delta_delay(self) -> float:
        """Queries the delta delay.

        Returns:
            float: The delta delay in s.
        """
        return float(self.query("SOUR:DELT:DEL?"))

    @mark_command
    def set_delta_count(self, count: float) -> int:
        """Sets the number of delta cycles.

        Args:
            count (float): The number of delta cycles. Use math.inf for an infinite count. Range: 1 to 65536.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DELT:COUN {format_count(count)}")

    @mark_query
    def get_delta_count(self) -> float:
        """Queries the number of delta cycles.

        Returns:
            float: The number of delta cycles.
        """
        return float(self.query("SOUR:DELT:COUN?"))

    @mark_command
    def set_delta_compliance_abort(self, state: State) -> int:
        """Enables or disables the abort of the delta test on compliance.

        Args:
            state (State): State.ON to enable or State.OFF to disable the abort of the delta test on compliance.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DELT:CAB {state.raw_value}")

    @mark_query
    def get_delta_compliance_abort(self) -> State:
        """Queries whether the abort of the delta test on compliance is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SOUR:DELT:CAB?")))

    @mark_command
    def set_delta_cold_switching(self, state: State) -> int:
        """Enables or disables the cold switching mode.

        Args:
            state (State): State.ON to enable or State.OFF to disable the cold switching mode.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DELT:CSW {state.raw_value}")

    @mark_query
    def get_delta_cold_switching(self) -> State:
        """Queries whether the cold switching mode is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SOUR:DELT:CSW?")))

    @mark_command
    def arm_delta(self) -> int:
        """Arms the delta test.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SOUR:DELT:ARM")

    @mark_query
    def get_delta_armed(self) -> bool:
        """Queries whether the delta test is armed.

        Returns:
            bool: True if delta is armed.
        """
        return to_int(self.query("SOUR:DELT:ARM?")) == 1

    """ PULSE DELTA """

    @mark_command
    def set_pulse_delta_high(self, high: float) -> int:
        """Sets the pulse delta high value.

        Args:
            high (float): The pulse delta high value in A. Range: -105e-3 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:PDEL:HIGH {format_number(high)}")

    @mark_query
    def get_pulse_delta_high(self) -> float:
        """Queries the pulse delta high value.

        Returns:
            float: The pulse delta high value in A.
        """
        return float(self.query("SOUR:PDEL:HIGH?"))

    @mark_command
    def set_pulse_delta_low(self, low: float) -> int:
        """Sets the pulse delta low value.

        Args:
            low (float): The pulse delta low value in A. Range: -105e-3 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:PDEL:LOW {format_number(low)}")

    @mark_query
    def get_pulse_delta_low(self) -> float:
        """Queries the pulse delta low value.

        Returns:
            float: The pulse delta low value in A.
        """
        return float(self.query("SOUR:PDEL:LOW?"))

    @mark_command
    def set_pulse_delta_width(self, width: float) -> int:
        """Sets the pulse width.

        Args:
            width (float): The pulse width in s. Range: 50e-6 to 12e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:PDEL:WIDT {format_number(width)}")

    @mark_query
    def get_pulse_delta_width(self) -> float:
        """Queries the pulse width.

        Returns:
            float: The pulse width in s.
        """
        return float(self.query("SOUR:PDEL:WIDT?"))

    @mark_command
    def set_pulse_delta_source_delay(self, delay: float) -> int:
        """Sets the pulse source delay.

        Args:
            delay (float): The pulse source delay in s. Range: 16e-6 to 11.966e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:PDEL:SDEL {format_number(delay)}")

    @mark_query
    def get_pulse_delta_source_delay(self) -> float:
        """Queries the pulse source delay.

        Returns:
            float: The pulse source delay in s.
        """
        return float(self.query("SOUR:PDEL:SDEL?"))

    @mark_command
    def set_pulse_delta_count(self, count: float) -> int:
        """Sets the number of pulse delta readings.

        Args:
            count (float): The number of pulse delta readings. Use math.inf for an infinite count. Range: 1 to 65636.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:PDEL:COUN {format_count(count)}")

    @mark_query
    def get_pulse_delta_count(self) -> float:
        """Queries the number of pulse delta readings.

        Returns:
            float: The number of pulse delta readings.
        """
        return float(self.query("SOUR:PDEL:COUN?"))

    @mark_command
    def set_pulse_delta_ranging(self, ranging: Ranging) -> int:
        """Sets the pulse source ranging.

        Args:
            ranging (Ranging): The pulse source ranging.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:PDEL:RANG {ranging.raw_value}")

    @mark_query
    def get_pulse_delta_ranging(self) -> Ranging:
        """Queries the pulse source ranging.

        Returns:
            Ranging: The pulse source ranging.
        """
        return parse_enum(Ranging, self.query("SOUR:PDEL:RANG?"))

    @mark_command
    def set_pulse_delta_interval(self, interval: int) -> int:
        """Sets the interval of each pulse cycle in power line cycles.

        Args:
            interval (int): The interval of each pulse cycle in power line cycles. Range: 5 to 999999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:PDEL:INT {interval}")

    @mark_query
    def get_pulse_delta_interval(self) -> int:
        """Queries the interval of each pulse cycle in power line cycles.

        Returns:
            int: The interval of each pulse cycle in power line cycles.
        """
        return to_int(self.query("SOUR:PDEL:INT?"))

    @mark_command
    def set_pulse_delta_sweep(self, state: State) -> int:
        """Enables or disables the pulse delta sweep output mode.

        Args:
            state (State): State.ON to enable or State.OFF to disable the pulse delta sweep output mode.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:PDEL:SWE {state.raw_value}")

    @mark_query
    def get_pulse_delta_sweep(self) -> State:
        """Queries whether the pulse delta sweep output mode is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SOUR:PDEL:SWE?")))

    @mark_command
    def set_pulse_delta_low_measurements(self, count: int) -> int:
        """Sets the number of low measurements per cycle.

        Args:
            count (int): The number of low measurements per cycle. Range: 1 or 2.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:PDEL:LME {count}")

    @mark_query
    def get_pulse_delta_low_measurements(self) -> int:
        """Queries the number of low measurements per cycle.

        Returns:
            int: The number of low measurements per cycle.
        """
        return to_int(self.query("SOUR:PDEL:LME?"))

    @mark_command
    def arm_pulse_delta(self) -> int:
        """Arms the pulse delta test.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SOUR:PDEL:ARM")

    @mark_query
    def get_pulse_delta_armed(self) -> bool:
        """Queries whether the pulse delta test is armed.

        Returns:
            bool: True if pulse delta is armed.
        """
        return to_int(self.query("SOUR:PDEL:ARM?")) == 1

    """ DIFFERENTIAL CONDUCTANCE """

    @mark_query
    def get_diffcond_v_zero(self) -> float:
        """Queries the V-zero value acquired from the nanovoltmeter.

        Returns:
            float: The V-zero value in V.
        """
        return float(self.query("SOUR:DCON:NVZ?"))

    @mark_command
    def set_diffcond_start(self, start: float) -> int:
        """Sets the differential conductance start value.

        Args:
            start (float): The differential conductance start value in A. Range: -105e-3 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DCON:STAR {format_number(start)}")

    @mark_query
    def get_diffcond_start(self) -> float:
        """Queries the differential conductance start value.

        Returns:
            float: The differential conductance start value in A.
        """
        return float(self.query("SOUR:DCON:STAR?"))

    @mark_command
    def set_diffcond_step(self, step: float) -> int:
        """Sets the differential conductance step size.

        Args:
            step (float): The differential conductance step size in A. Range: 0 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DCON:STEP {format_number(step)}")

    @mark_query
    def get_diffcond_step(self) -> float:
        """Queries the differential conductance step size.

        Returns:
            float: The differential conductance step size in A.
        """
        return float(self.query("SOUR:DCON:STEP?"))

    @mark_command
    def set_diffcond_stop(self, stop: float) -> int:
        """Sets the differential conductance stop value.

        Args:
            stop (float): The differential conductance stop value in A. Range: -105e-3 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DCON:STOP {format_number(stop)}")

    @mark_query
    def get_diffcond_stop(self) -> float:
        """Queries the differential conductance stop value.

        Returns:
            float: The differential conductance stop value in A.
        """
        return float(self.query("SOUR:DCON:STOP?"))

    @mark_command
    def set_diffcond_delta(self, delta: float) -> int:
        """Sets the differential conductance delta value.

        Args:
            delta (float): The differential conductance delta value in A. Range: 0 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DCON:DELT {format_number(delta)}")

    @mark_query
    def get_diffcond_delta(self) -> float:
        """Queries the differential conductance delta value.

        Returns:
            float: The differential conductance delta value in A.
        """
        return float(self.query("SOUR:DCON:DELT?"))

    @mark_command
    def set_diffcond_delay(self, delay: float) -> int:
        """Sets the differential conductance delay.

        Args:
            delay (float): The differential conductance delay in s. Range: 1e-3 to 9999.999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DCON:DEL {format_number(delay)}")

    @mark_query
    def get_diffcond_delay(self) -> float:
        """Queries the differential conductance delay.

        Returns:
            float: The differential conductance delay in s.
        """
        return float(self.query("SOUR:DCON:DEL?"))

    @mark_command
    def set_diffcond_compliance_abort(self, state: State) -> int:
        """Enables or disables the abort of the differential conductance test on compliance.

        Args:
            state (State): State.ON to enable or State.OFF to disable the abort of the differential conductance test on compliance.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:DCON:CAB {state.raw_value}")

    @mark_query
    def get_diffcond_compliance_abort(self) -> State:
        """Queries whether the abort of the differential conductance test on compliance is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SOUR:DCON:CAB?")))

    @mark_command
    def arm_diffcond(self) -> int:
        """Arms the differential conductance test.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SOUR:DCON:ARM")

    @mark_query
    def get_diffcond_armed(self) -> bool:
        """Queries whether the differential conductance test is armed.

        Returns:
            bool: True if differential conductance is armed.
        """
        return to_int(self.query("SOUR:DCON:ARM?")) == 1

    """ WAVE GENERATOR """

    @mark_command
    def set_wave_function(self, function: WaveFunction) -> int:
        """Sets the wave function.

        Args:
            function (WaveFunction): The wave function.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:FUNC {function.raw_value}")

    @mark_query
    def get_wave_function(self) -> WaveFunction:
        """Queries the wave function.

        Returns:
            WaveFunction: The wave function.
        """
        return parse_enum(WaveFunction, self.query("SOUR:WAVE:FUNC?"))

    @mark_command
    def set_wave_duty_cycle(self, duty_cycle: float) -> int:
        """Sets the wave duty cycle.

        Args:
            duty_cycle (float): The wave duty cycle in %. Range: 0 to 100.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:DCYC {format_number(duty_cycle)}")

    @mark_query
    def get_wave_duty_cycle(self) -> float:
        """Queries the wave duty cycle.

        Returns:
            float: The wave duty cycle in %.
        """
        return float(self.query("SOUR:WAVE:DCYC?"))

    @mark_command
    def set_wave_amplitude(self, amplitude: float) -> int:
        """Sets the wave amplitude.

        Args:
            amplitude (float): The wave amplitude in A peak. Range: 2e-12 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:AMPL {format_number(amplitude)}")

    @mark_query
    def get_wave_amplitude(self) -> float:
        """Queries the wave amplitude.

        Returns:
            float: The wave amplitude in A peak.
        """
        return float(self.query("SOUR:WAVE:AMPL?"))

    @mark_command
    def set_wave_frequency(self, frequency: float) -> int:
        """Sets the wave frequency.

        Args:
            frequency (float): The wave frequency in Hz. Range: 1e-3 to 1e5.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:FREQ {format_number(frequency)}")

    @mark_query
    def get_wave_frequency(self) -> float:
        """Queries the wave frequency.

        Returns:
            float: The wave frequency in Hz.
        """
        return float(self.query("SOUR:WAVE:FREQ?"))

    @mark_command
    def set_wave_offset(self, offset: float) -> int:
        """Sets the wave offset.

        Args:
            offset (float): The wave offset in A. Range: -105e-3 to 105e-3.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:OFFS {format_number(offset)}")

    @mark_query
    def get_wave_offset(self) -> float:
        """Queries the wave offset.

        Returns:
            float: The wave offset in A.
        """
        return float(self.query("SOUR:WAVE:OFFS?"))

    @mark_command
    def set_wave_phase_marker_level(self, phase: float) -> int:
        """Sets the phase marker phase.

        Args:
            phase (float): The phase marker phase in degrees. Range: 0 to 360.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:PMAR {format_number(phase)}")

    @mark_query
    def get_wave_phase_marker_level(self) -> float:
        """Queries the phase marker phase.

        Returns:
            float: The phase marker phase in degrees.
        """
        return float(self.query("SOUR:WAVE:PMAR?"))

    @mark_command
    def set_wave_phase_marker_line(self, line: int) -> int:
        """Sets the phase marker trigger line.

        Args:
            line (int): The phase marker trigger line. Range: 1 to 6.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:PMAR:OLIN {line}")

    @mark_query
    def get_wave_phase_marker_line(self) -> int:
        """Queries the phase marker trigger line.

        Returns:
            int: The phase marker trigger line.
        """
        return to_int(self.query("SOUR:WAVE:PMAR:OLIN?"))

    @mark_command
    def set_wave_phase_marker_state(self, state: State) -> int:
        """Enables or disables the phase marker.

        Args:
            state (State): State.ON to enable or State.OFF to disable the phase marker.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:PMAR:STAT {state.raw_value}")

    @mark_query
    def get_wave_phase_marker_state(self) -> State:
        """Queries whether the phase marker is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SOUR:WAVE:PMAR:STAT?")))

    @mark_command
    def set_arbitrary_data(self, points: list[float]) -> int:
        """Defines the points of the arbitrary waveform.

        Args:
            points (list[float]): Up to 100 points, each -1 to +1.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:ARB:DATA {format_list(points)}")

    @mark_command
    def append_arbitrary_data(self, points: list[float]) -> int:
        """Appends points to the arbitrary waveform.

        Args:
            points (list[float]): Up to 100 points per call, each -1 to +1.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:ARB:APP {format_list(points)}")

    @mark_query
    def get_arbitrary_data(self) -> list[float]:
        """Queries the points of the arbitrary waveform.

        Returns:
            list[float]: The points of the waveform.
        """
        return to_floats(self.query("SOUR:WAVE:ARB:DATA?"))

    @mark_query
    def get_arbitrary_points(self) -> int:
        """Queries the number of points in the arbitrary waveform.

        Returns:
            int: The number of points.
        """
        return to_int(self.query("SOUR:WAVE:ARB:POIN?"))

    @mark_command
    def copy_arbitrary_to_memory(self, location: int) -> int:
        """Copies the arbitrary waveform to non-volatile memory.

        Args:
            location (int): The memory location, 1 to 4.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:ARB:COPY {location}")

    @mark_command
    def set_wave_ranging(self, ranging: Ranging) -> int:
        """Sets the wave source ranging.

        Args:
            ranging (Ranging): The wave source ranging.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:RANG {ranging.raw_value}")

    @mark_query
    def get_wave_ranging(self) -> Ranging:
        """Queries the wave source ranging.

        Returns:
            Ranging: The wave source ranging.
        """
        return parse_enum(Ranging, self.query("SOUR:WAVE:RANG?"))

    @mark_command
    def set_wave_duration_time(self, duration: float) -> int:
        """Sets the wave duration.

        Args:
            duration (float): The wave duration in s. Use math.inf for an infinite duration. Range: 100e-9 to 999999.999.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:DUR:TIME {format_duration(duration)}")

    @mark_query
    def get_wave_duration_time(self) -> float:
        """Queries the wave duration.

        Returns:
            float: The wave duration in s.
        """
        return float(self.query("SOUR:WAVE:DUR:TIME?"))

    @mark_command
    def set_wave_duration_cycles(self, cycles: float) -> int:
        """Sets the wave duration in cycles.

        Args:
            cycles (float): The wave duration in cycles. Use math.inf for an infinite duration. Range: 1e-3 to 99999999900.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:DUR:CYCL {format_duration(cycles)}")

    @mark_query
    def get_wave_duration_cycles(self) -> float:
        """Queries the wave duration in cycles.

        Returns:
            float: The wave duration in cycles.
        """
        return float(self.query("SOUR:WAVE:DUR:CYCL?"))

    @mark_command
    def arm_wave(self) -> int:
        """Arms the wave function.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SOUR:WAVE:ARM")

    @mark_command
    def start_wave(self) -> int:
        """Starts the waveform output.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SOUR:WAVE:INIT")

    @mark_command
    def abort_wave(self) -> int:
        """Aborts the waveform output.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SOUR:WAVE:ABOR")

    @mark_command
    def set_wave_external_trigger(self, state: State) -> int:
        """Enables or disables the external triggering of the waveform generator.

        Args:
            state (State): State.ON to enable or State.OFF to disable the external triggering of the waveform generator.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:EXTR {state.raw_value}")

    @mark_query
    def get_wave_external_trigger(self) -> State:
        """Queries whether the external triggering of the waveform generator is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SOUR:WAVE:EXTR?")))

    @mark_command
    def set_wave_external_trigger_line(self, line: int) -> int:
        """Sets the trigger link input line for the waveform.

        Args:
            line (int): The trigger link input line for the waveform. Range: 0 (none) or 1 to 6.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:EXTR:ILIN {line}")

    @mark_query
    def get_wave_external_trigger_line(self) -> int:
        """Queries the trigger link input line for the waveform.

        Returns:
            int: The trigger link input line for the waveform.
        """
        return to_int(self.query("SOUR:WAVE:EXTR:ILIN?"))

    @mark_command
    def set_wave_ignore_retrigger(self, state: State) -> int:
        """Enables or disables the ignoring of retriggers, which otherwise restart the waveform.

        Args:
            state (State): State.ON to enable or State.OFF to disable the ignoring of retriggers, which otherwise restart the waveform.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:EXTR:IGN {state.raw_value}")

    @mark_query
    def get_wave_ignore_retrigger(self) -> State:
        """Queries whether the ignoring of retriggers, which otherwise restart the waveform is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SOUR:WAVE:EXTR:IGN?")))

    @mark_command
    def set_wave_inactive_value(self, value: float) -> int:
        """Sets the value output before and after the waveform.

        Args:
            value (float): The value output before and after the waveform. Range: -1 to +1.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SOUR:WAVE:EXTR:IVAL {format_number(value)}")

    @mark_query
    def get_wave_inactive_value(self) -> float:
        """Queries the value output before and after the waveform.

        Returns:
            float: The value output before and after the waveform.
        """
        return float(self.query("SOUR:WAVE:EXTR:IVAL?"))

    """ READINGS FROM THE NANOVOLTMETER """

    @mark_query
    def get_latest_reading(self) -> float:
        """Reads the latest pre-math delta, pulse delta or differential conductance reading.

        Returns:
            float: The reading, in the units selected with set_reading_units.
        """
        return first_number(self.query("SENS:DATA?"))

    @mark_query
    def get_fresh_reading(self) -> float:
        """Reads the latest pre-math reading, which can only be returned once.

        Returns:
            float: The reading, in the units selected with set_reading_units.
        """
        return first_number(self.query("SENS:DATA:FRES?"))

    @mark_command
    def set_average_filter_control(self, control: FilterControl) -> int:
        """Sets the averaging filter control.

        Args:
            control (FilterControl): The averaging filter control.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:AVER:TCON {control.raw_value}")

    @mark_query
    def get_average_filter_control(self) -> FilterControl:
        """Queries the averaging filter control.

        Returns:
            FilterControl: The averaging filter control.
        """
        return parse_enum(FilterControl, self.query("SENS:AVER:TCON?"))

    @mark_command
    def set_average_filter_window(self, window: float) -> int:
        """Sets the averaging filter window.

        Args:
            window (float): The averaging filter window in % of range. Range: 0 to 10.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:AVER:WIND {format_number(window)}")

    @mark_query
    def get_average_filter_window(self) -> float:
        """Queries the averaging filter window.

        Returns:
            float: The averaging filter window in % of range.
        """
        return float(self.query("SENS:AVER:WIND?"))

    @mark_command
    def set_average_filter_count(self, count: int) -> int:
        """Sets the averaging filter count.

        Args:
            count (int): The averaging filter count. Range: 2 to 300.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:AVER:COUN {count}")

    @mark_query
    def get_average_filter_count(self) -> int:
        """Queries the averaging filter count.

        Returns:
            int: The averaging filter count.
        """
        return to_int(self.query("SENS:AVER:COUN?"))

    @mark_command
    def set_average_filter(self, state: State) -> int:
        """Enables or disables the averaging filter.

        Args:
            state (State): State.ON to enable or State.OFF to disable the averaging filter.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS:AVER:STAT {state.raw_value}")

    @mark_query
    def get_average_filter(self) -> State:
        """Queries whether the averaging filter is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("SENS:AVER:STAT?")))

    @mark_command
    def set_reading_units(self, units: ReadingUnits) -> int:
        """Sets the reading units.

        Args:
            units (ReadingUnits): The reading units.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"UNIT:VOLT:DC {units.raw_value}")

    @mark_query
    def get_reading_units(self) -> ReadingUnits:
        """Queries the reading units.

        Returns:
            ReadingUnits: The reading units.
        """
        return parse_enum(ReadingUnits, self.query("UNIT:VOLT:DC?"))

    @mark_command
    def set_power_type(self, power_type: PowerType) -> int:
        """Sets the pulse delta power reading type.

        Args:
            power_type (PowerType): The pulse delta power reading type.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"UNIT:POW:TYPE {power_type.raw_value}")

    @mark_query
    def get_power_type(self) -> PowerType:
        """Queries the pulse delta power reading type.

        Returns:
            PowerType: The pulse delta power reading type.
        """
        return parse_enum(PowerType, self.query("UNIT:POW:TYPE?"))

    """ READING FORMAT """

    @mark_command
    def set_reading_elements(self, elements: list[ReadingElement]) -> int:
        """Selects the data elements included in reading strings.

        Args:
            elements (list[ReadingElement]): The elements to include.

        Returns:
            int: Status code indicating the success of the operation.
        """
        items = ",".join(element.raw_value for element in elements)
        return self.command(f"FORM:ELEM {items}")

    @mark_query
    def get_reading_elements(self) -> list[ReadingElement]:
        """Queries the data elements included in reading strings.

        Returns:
            list[ReadingElement]: The elements included.
        """
        reply = self.query("FORM:ELEM?")
        return [parse_enum(ReadingElement, item) for item in reply.split(",")]

    """ MATH, STATISTICS AND LIMIT TESTING """

    @mark_command
    def set_math_format(self, math_format: MathFormat) -> int:
        """Sets the math format.

        Args:
            math_format (MathFormat): The math format.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC1:FORM {math_format.raw_value}")

    @mark_query
    def get_math_format(self) -> MathFormat:
        """Queries the math format.

        Returns:
            MathFormat: The math format.
        """
        return parse_enum(MathFormat, self.query("CALC1:FORM?"))

    @mark_command
    def set_math_factor_m(self, factor: float) -> int:
        """Sets the math "m" factor.

        Args:
            factor (float): The math "m" factor. Range: -9.99999e20 to 9.99999e20.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC1:KMAT:MMF {format_number(factor)}")

    @mark_query
    def get_math_factor_m(self) -> float:
        """Queries the math "m" factor.

        Returns:
            float: The math "m" factor.
        """
        return float(self.query("CALC1:KMAT:MMF?"))

    @mark_command
    def set_math_factor_b(self, factor: float) -> int:
        """Sets the math "b" factor.

        Args:
            factor (float): The math "b" factor. Range: -9.99999e20 to 9.99999e20.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC1:KMAT:MBF {format_number(factor)}")

    @mark_query
    def get_math_factor_b(self) -> float:
        """Queries the math "b" factor.

        Returns:
            float: The math "b" factor.
        """
        return float(self.query("CALC1:KMAT:MBF?"))

    @mark_command
    def set_math_state(self, state: State) -> int:
        """Enables or disables the math calculation.

        Args:
            state (State): State.ON to enable or State.OFF to disable the math calculation.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC1:STAT {state.raw_value}")

    @mark_query
    def get_math_state(self) -> State:
        """Queries whether the math calculation is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("CALC1:STAT?")))

    @mark_query
    def get_math_reading(self) -> float:
        """Reads the latest post-math reading.

        Returns:
            float: The reading.
        """
        return first_number(self.query("CALC1:DATA?"))

    @mark_query
    def get_fresh_math_reading(self) -> float:
        """Reads the latest post-math reading, which can only be returned once.

        Returns:
            float: The reading.
        """
        return first_number(self.query("CALC1:DATA:FRES?"))

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
        return float(self.query("CALC2:DATA?"))

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

    @mark_command
    def set_limit_fail_pattern(self, pattern: int) -> int:
        """Sets the limit test fail pattern.

        Args:
            pattern (int): The limit test fail pattern. Range: 0 to 15.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC3:LIM:SOUR2 {pattern}")

    @mark_query
    def get_limit_fail_pattern(self) -> int:
        """Queries the limit test fail pattern.

        Returns:
            int: The limit test fail pattern.
        """
        return to_int(self.query("CALC3:LIM:SOUR2?"))

    @mark_query
    def get_limit_test_failed(self) -> bool:
        """Queries whether the limit test failed.

        Returns:
            bool: True if the limit test failed.
        """
        return to_int(self.query("CALC3:LIM:FAIL?")) == 1

    @mark_command
    def set_io_pattern_force(self, state: State) -> int:
        """Enables or disables the I/O pattern force.

        Args:
            state (State): State.ON to enable or State.OFF to disable the I/O pattern force.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC3:FORC:STAT {state.raw_value}")

    @mark_query
    def get_io_pattern_force(self) -> State:
        """Queries whether the I/O pattern force is enabled.

        Returns:
            State: State.ON if enabled, otherwise State.OFF.
        """
        return State.from_raw_value(to_int(self.query("CALC3:FORC:STAT?")))

    @mark_command
    def set_io_pattern(self, pattern: int) -> int:
        """Sets the forced I/O pattern.

        Args:
            pattern (int): The forced I/O pattern. Range: 0 to 15.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"CALC3:FORC:PATT {pattern}")

    @mark_query
    def get_io_pattern(self) -> int:
        """Queries the forced I/O pattern.

        Returns:
            int: The forced I/O pattern.
        """
        return to_int(self.query("CALC3:FORC:PATT?"))

    """ BUFFER """

    @mark_command
    def clear_buffer(self) -> int:
        """Clears the readings from the buffer.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("TRAC:CLE")

    @mark_query
    def get_buffer_free(self) -> str:
        """Queries the memory available in the buffer.

        Returns:
            str: The reply, in bytes.
        """
        return unquote(self.query("TRAC:FREE?"))

    @mark_command
    def set_buffer_size(self, size: int) -> int:
        """Sets the buffer size.

        Args:
            size (int): The buffer size. Range: 1 to 65536.

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

    @mark_query
    def get_buffer_count(self) -> int:
        """Queries the number of readings stored in the buffer.

        Returns:
            int: The number of readings.
        """
        return to_int(self.query("TRAC:POIN:ACT?"))

    @mark_command
    def set_buffer_notify(self, count: int) -> int:
        """Sets the number of stored readings that sets the trace notify bit.

        Args:
            count (int): The number of stored readings that sets the trace notify bit. Range: 1 to (buffer size - 1).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRAC:NOT {count}")

    @mark_query
    def get_buffer_notify(self) -> int:
        """Queries the number of stored readings that sets the trace notify bit.

        Returns:
            int: The number of stored readings that sets the trace notify bit.
        """
        return to_int(self.query("TRAC:NOT?"))

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

    @mark_command
    def set_buffer_timestamp_format(self, timestamp_format: TimestampFormat) -> int:
        """Sets the buffer timestamp format.

        Args:
            timestamp_format (TimestampFormat): The buffer timestamp format.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRAC:TST:FORM {timestamp_format.raw_value}")

    @mark_query
    def get_buffer_timestamp_format(self) -> TimestampFormat:
        """Queries the buffer timestamp format.

        Returns:
            TimestampFormat: The buffer timestamp format.
        """
        return parse_enum(TimestampFormat, self.query("TRAC:TST:FORM?"))

    @mark_query
    def get_buffer_data(self) -> str:
        """Reads all the readings in the buffer.

        Returns:
            str: The readings, laid out as chosen with set_reading_elements.
        """
        return unquote(self.query("TRAC:DATA?"))

    @mark_query
    def get_buffer_type(self) -> str:
        """Queries the type of readings in the buffer.

        Returns:
            str: NONE, DELT, DCON or PULS.
        """
        return unquote(self.query("TRAC:DATA:TYPE?"))

    @mark_query
    def get_buffer_selected(self, start: int, count: int) -> str:
        """Reads a range of the readings in the buffer.

        Args:
            start (int): The index of the first reading.
            count (int): The number of readings.

        Returns:
            str: The readings, laid out as chosen with set_reading_elements.
        """
        return unquote(self.query(f"TRAC:DATA:SEL? {start},{count}"))

    """ TRIGGER MODEL """

    @mark_command
    def initiate(self) -> int:
        """Takes the instrument out of idle and starts one trigger cycle.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("INIT:IMM")

    @mark_command
    def abort_trigger(self) -> int:
        """Resets the trigger system.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("ABOR")

    @mark_command
    def set_arm_source(self, source: ArmSource) -> int:
        """Sets the arm event detector.

        Args:
            source (ArmSource): The arm event detector.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ARM:SOUR {source.raw_value}")

    @mark_query
    def get_arm_source(self) -> ArmSource:
        """Queries the arm event detector.

        Returns:
            ArmSource: The arm event detector.
        """
        return parse_enum(ArmSource, self.query("ARM:SOUR?"))

    @mark_command
    def set_arm_timer(self, interval: float) -> int:
        """Sets the arm timer interval.

        Args:
            interval (float): The arm timer interval in s. Range: 0 to 99999.99.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ARM:TIM {format_number(interval)}")

    @mark_query
    def get_arm_timer(self) -> float:
        """Queries the arm timer interval.

        Returns:
            float: The arm timer interval in s.
        """
        return float(self.query("ARM:TIM?"))

    @mark_command
    def set_arm_output(self, output: ArmOutput) -> int:
        """Sets the arm output trigger.

        Args:
            output (ArmOutput): The arm output trigger.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ARM:TCON:ASYN:OUTP {output.raw_value}")

    @mark_query
    def get_arm_output(self) -> ArmOutput:
        """Queries the arm output trigger.

        Returns:
            ArmOutput: The arm output trigger.
        """
        return parse_enum(ArmOutput, self.query("ARM:TCON:ASYN:OUTP?"))

    @mark_command
    def set_trigger_source(self, source: TriggerSource) -> int:
        """Sets the trigger event detector.

        Args:
            source (TriggerSource): The trigger event detector.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRIG:SOUR {source.raw_value}")

    @mark_query
    def get_trigger_source(self) -> TriggerSource:
        """Queries the trigger event detector.

        Returns:
            TriggerSource: The trigger event detector.
        """
        return parse_enum(TriggerSource, self.query("TRIG:SOUR?"))

    @mark_command
    def set_trigger_output(self, output: TriggerOutput) -> int:
        """Sets the trigger output trigger.

        Args:
            output (TriggerOutput): The trigger output trigger.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"TRIG:TCON:ASYN:OUTP {output.raw_value}")

    @mark_query
    def get_trigger_output(self) -> TriggerOutput:
        """Queries the trigger output trigger.

        Returns:
            TriggerOutput: The trigger output trigger.
        """
        return parse_enum(TriggerOutput, self.query("TRIG:TCON:ASYN:OUTP?"))

    @mark_command
    def bypass_layer(self, layer: TriggerLayer) -> int:
        """Bypasses the control source of a trigger model layer.

        Args:
            layer (TriggerLayer): The trigger model layer.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"{layer.raw_value}:SIGN")

    @mark_command
    def set_layer_direction(
        self, layer: TriggerLayer, direction: BypassDirection
    ) -> int:
        """Sets the control source bypass direction.

        Args:
            layer (TriggerLayer): The trigger model layer.
            direction (BypassDirection): The control source bypass direction.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"{layer.raw_value}:TCON:DIR {direction.raw_value}")

    @mark_query
    def get_layer_direction(self, layer: TriggerLayer) -> BypassDirection:
        """Queries the control source bypass direction.

        Args:
            layer (TriggerLayer): The trigger model layer.

        Returns:
            BypassDirection: The control source bypass direction.
        """
        return parse_enum(BypassDirection, self.query(f"{layer.raw_value}:TCON:DIR?"))

    @mark_command
    def set_layer_input_line(self, layer: TriggerLayer, line: int) -> int:
        """Sets the input signal line.

        Args:
            layer (TriggerLayer): The trigger model layer.
            line (int): The input signal line. Range: 1 to 6.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"{layer.raw_value}:TCON:ASYN:ILIN {line}")

    @mark_query
    def get_layer_input_line(self, layer: TriggerLayer) -> int:
        """Queries the input signal line.

        Args:
            layer (TriggerLayer): The trigger model layer.

        Returns:
            int: The input signal line.
        """
        return to_int(self.query(f"{layer.raw_value}:TCON:ASYN:ILIN?"))

    @mark_command
    def set_layer_output_line(self, layer: TriggerLayer, line: int) -> int:
        """Sets the output signal line.

        Args:
            layer (TriggerLayer): The trigger model layer.
            line (int): The output signal line. Range: 1 to 6.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"{layer.raw_value}:TCON:ASYN:OLIN {line}")

    @mark_query
    def get_layer_output_line(self, layer: TriggerLayer) -> int:
        """Queries the output signal line.

        Args:
            layer (TriggerLayer): The trigger model layer.

        Returns:
            int: The output signal line.
        """
        return to_int(self.query(f"{layer.raw_value}:TCON:ASYN:OLIN?"))

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

    @mark_command
    def reset_timestamp(self) -> int:
        """Resets the system timestamp to zero seconds.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SYST:TST:RES")

    @mark_command
    def reset_reading_number(self) -> int:
        """Resets the system reading number to zero.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("SYST:RNUM:RES")

    @mark_query
    def get_scpi_version(self) -> str:
        """Queries the revision level of the SCPI standard.

        Returns:
            str: The SCPI version.
        """
        return unquote(self.query("SYST:VERS?"))

    @mark_query
    def get_analog_board_serial(self) -> str:
        """Queries the serial number of the analog board.

        Returns:
            str: The serial number.
        """
        return unquote(self.query("SYST:ABO:SNUM?"))

    @mark_query
    def get_analog_board_revision(self) -> str:
        """Queries the revision level of the analog board.

        Returns:
            str: The revision level.
        """
        return unquote(self.query("SYST:ABO:REV?"))

    @mark_query
    def get_digital_board_serial(self) -> str:
        """Queries the serial number of the digital board.

        Returns:
            str: The serial number.
        """
        return unquote(self.query("SYST:DBO:SNUM?"))

    @mark_query
    def get_digital_board_revision(self) -> str:
        """Queries the revision level of the digital board.

        Returns:
            str: The revision level.
        """
        return unquote(self.query("SYST:DBO:REV?"))
