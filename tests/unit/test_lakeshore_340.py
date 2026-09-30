"""The Lakeshore 340's driver (instruments/lakeshore/lakeshore_340.py): each command
sends the message the manual (section 9.4) gives, each reply is taken apart, every
command in the manual's list is there, and the interface can call each one."""

import re
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment
from pyacquisition.instruments import Lakeshore_340, instrument_map
from pyacquisition.instruments.lakeshore import lakeshore_340 as module
from pyacquisition.instruments.lakeshore.lakeshore_340 import (
    AnalogMode,
    AnalogOutput,
    AutotuneMode,
    BaudRate,
    Coefficient,
    Compensation,
    ControlMode,
    CurveFormat,
    DigitalOutputMode,
    DisplayData,
    Excitation,
    HeaterDisplay,
    HeaterRange,
    IeeeTerminator,
    InputChannel,
    InputData,
    InputRange,
    LinearEquation,
    LinearOffset,
    LogPointType,
    LogStartMode,
    LogType,
    LoopDisplay,
    MaxCurrent,
    MinMaxMode,
    OutputChannel,
    Parity,
    ProgramCommand,
    Relay,
    RelayMode,
    RemoteMode,
    ScanMode,
    SensorType,
    SensorUnits,
    SerialTerminator,
    State,
    Units,
)

A, B = InputChannel.INPUT_A, InputChannel.INPUT_B
LOOP_1, LOOP_2 = OutputChannel.OUTPUT_1, OutputChannel.OUTPUT_2
ON, OFF = State.ON, State.OFF

# Every command in the manual's list (section 9.3), but `?`, which re-sends the last
# reply over the serial interface, and `*WAI`, which the 340 doesn't support.
MANUAL = """
*CLS *ESE *ESE? *ESR? *IDN? *OPC *OPC? *RST *SRE *SRE? *STB? *TST?
ALARM ALARM? ALARMST? CRDG? FILTER FILTER? INCRV INCRV? INSET INSET? INTYPE INTYPE?
KRDG? LDAT? LDATST? LINEAR LINEAR? MDAT? MDATST? MNMX MNMX? RDGST? SRDG?
CDISP CDISP? CFILT CFILT? CLIMI CLIMI? CLIMIT CLIMIT? CMODE CMODE? CSET CSET?
HTR? HTRST? MOUT MOUT? PID PID? RAMP RAMP? RAMPST? RANGE RANGE? SETP SETP?
SETTLE SETTLE? TUNEST? ZONE ZONE?
ALMRST ANALOG ANALOG? AOUT? BEEP BEEP? BEEPST? BUSY? COMM COMM? DATETIME DATETIME?
DFLT DIOST? DISPFLD DISPFLD? DISPLAY DISPLAY? DOUT DOUT? IEEE IEEE? KEYST? LOCK LOCK?
MNMXRST MODE MODE? RELAY RELAY? RELAYST? REV? XSCAN XSCAN?
CRVDEL CRVHDR CRVHDR? CRVPT CRVPT? CRVSAV SCAL
PGM PGM? PGMDEL PGMMEM? PGMRUN PGMRUN?
LOG LOG? LOGCNT? LOGPNT LOGPNT? LOGSET LOGSET? LOGVIEW?
""".split()


class FakeVisa:
    """Records what is written and answers queries from a table."""

    def __init__(self):
        self.written = []
        self.queried = []
        self.replies = {}

    def write(self, text):
        self.written.append(text)
        return len(text)

    def query(self, text):
        self.queried.append(text)
        return self.replies.get(text, "0")


@pytest.fixture
def visa():
    return FakeVisa()


@pytest.fixture
def ls(visa):
    return Lakeshore_340("lakeshore", visa)


def test_registered_in_instrument_map():
    assert instrument_map["Lakeshore_340"] is Lakeshore_340


def test_init_only_clears_the_status_registers(visa, ls):
    assert visa.written == ["*CLS"]
    assert visa.queried == []


def test_every_public_method_is_a_query_or_a_command_and_says_what_it_does():
    for name, member in vars(Lakeshore_340).items():
        if name.startswith("_") or not callable(member) or isinstance(member, type):
            continue  # the enums that the class exposes are not methods
        assert hasattr(member, "_is_query") ^ hasattr(member, "_is_command"), name
        assert member.__doc__, name


def test_getters_are_queries_and_setters_are_commands():
    queries = {m.__name__ for m in Lakeshore_340._queries}
    commands = {m.__name__ for m in Lakeshore_340._commands}
    assert all(n.startswith("get_") or n in {"identify", "self_test"} for n in queries)
    assert not any(n.startswith("get_") for n in commands)


def test_no_duplicate_definitions():
    with open(module.__file__, encoding="utf-8") as f:
        names = [
            line.split("def ")[1].split("(")[0]
            for line in f.read().splitlines()
            if line.startswith("    def ")
        ]
    assert len(names) == len(set(names))


def test_every_command_in_the_manual_is_sent_by_a_method():
    with open(module.__file__, encoding="utf-8") as f:
        source = f.read()
    sent = set(re.findall(r'f?"([*A-Z]+\??)(?=[ "])', source))  # a message's start
    missing = [c for c in MANUAL if c not in sent]
    assert missing == []


def test_the_enums_are_reached_from_the_class():
    assert Lakeshore_340.HeaterRange is HeaterRange
    assert Lakeshore_340.ControlMode is ControlMode
    assert Lakeshore_340.InputChannel is InputChannel


def test_the_340_has_two_control_loops():
    assert [c.raw_value for c in OutputChannel] == [1, 2]


# ------------------------------------------------------------------ commands
@pytest.mark.parametrize(
    "call, sent",
    [
        (lambda ls: ls.reset(), "*RST"),
        (lambda ls: ls.clear(), "*CLS"),
        (lambda ls: ls.set_event_enable(143), "*ESE 143"),
        (lambda ls: ls.operation_complete(), "*OPC"),
        (lambda ls: ls.set_service_request_enable(89), "*SRE 89"),
        (
            lambda ls: ls.set_alarm(B, ON, InputData.KELVIN, 270.0, 0.0, ON, OFF),
            "ALARM B,1,1,270,0,1,0",
        ),
        (lambda ls: ls.reset_alarms(), "ALMRST"),
        (lambda ls: ls.set_filter(B, ON, 10, 2), "FILTER B,1,10,2"),
        (lambda ls: ls.set_input_curve(A, 23), "INCRV A,23"),
        (lambda ls: ls.set_input_setup(A, ON, Compensation.ON), "INSET A,1,1"),
        (lambda ls: ls.set_input_type(A, SensorType.GAALAS_DIODE), "INTYPE A,2"),
        (
            lambda ls: ls.set_input_type_special(
                B, SensorUnits.OHMS, Coefficient.NEGATIVE, Excitation.CURRENT_30_UA,
                InputRange.RANGE_100_MV,
            ),
            "INTYPE B,0,2,1,7,7",
        ),
        (
            lambda ls: ls.set_linear_equation(
                A, LinearEquation.MX_PLUS_B, 1.0, Units.KELVIN,
                LinearOffset.MINUS_SETPOINT_1, 0.0,
            ),
            "LINEAR A,1,1,1,3,0",
        ),
        (lambda ls: ls.set_min_max(B, MinMaxMode.ON, InputData.SENSOR_UNITS), "MNMX B,1,3"),
        (lambda ls: ls.reset_min_max(), "MNMXRST"),
        (lambda ls: ls.set_control_loop(LOOP_1, A, Units.KELVIN, ON, OFF), "CSET 1,A,1,1,0"),
        (lambda ls: ls.set_control_mode(LOOP_1, ControlMode.OPEN_LOOP), "CMODE 1,3"),
        (lambda ls: ls.set_autotune_pid(LOOP_1, AutotuneMode.PID), "CMODE 1,4"),
        (lambda ls: ls.set_autotune_pid(LOOP_2, AutotuneMode.P), "CMODE 2,6"),
        (lambda ls: ls.set_pid(LOOP_1, 25, 15, 6), "PID 1,25,15,6"),
        (lambda ls: ls.set_setpoint(LOOP_1, 122.5), "SETP 1,122.5"),
        (lambda ls: ls.set_setpoint(LOOP_1, 1.2345), "SETP 1,1.2345"),
        (lambda ls: ls.set_ramp(LOOP_1, ON, 10.5), "RAMP 1,1,10.500"),
        (lambda ls: ls.set_manual_output(LOOP_1, 22.45), "MOUT 1,22.45"),
        (lambda ls: ls.set_heater_range(HeaterRange.OFF), "RANGE 0"),
        (lambda ls: ls.set_heater_range(HeaterRange.RANGE_3), "RANGE 3"),
        (
            lambda ls: ls.set_control_limits(
                LOOP_1, 325.0, 10, 0, MaxCurrent.CURRENT_1, HeaterRange.RANGE_5
            ),
            "CLIMIT 1,325,10,0,3,5",
        ),
        (lambda ls: ls.set_max_user_current(1.5), "CLIMI 1.500"),
        (lambda ls: ls.set_control_filter(LOOP_1, ON), "CFILT 1,1"),
        (lambda ls: ls.set_settle(10.0, 10), "SETTLE 10,10"),
        (
            lambda ls: ls.set_zone(LOOP_1, 1, 25.0, 10, 20, 0, 0, HeaterRange.RANGE_2),
            "ZONE 1,1,25,10,20,0,0.00,2",
        ),
        (
            lambda ls: ls.set_control_display(
                LOOP_1, LoopDisplay.LOOP_1, 25, HeaterDisplay.CURRENT, ON
            ),
            "CDISP 1,1,25,1,1",
        ),
        (
            lambda ls: ls.set_analog_output_setup(
                AnalogOutput.ANALOG_2, OFF, AnalogMode.INPUT, A, InputData.KELVIN,
                100.0, 0.0, 0.0,
            ),
            "ANALOG 2,0,1,A,1,100,0,0.0",
        ),
        (lambda ls: ls.set_relay(Relay.HIGH, RelayMode.MANUAL, ON), "RELAY 1,2,1"),
        (lambda ls: ls.set_digital_output(DigitalOutputMode.MANUAL, 21), "DOUT 3,21"),
        (lambda ls: ls.set_display(3, 60, ON), "DISPLAY 3,60,1"),
        (lambda ls: ls.set_display_contrast(60), "DISPLAY ,60"),
        (lambda ls: ls.set_display_field(2, A, DisplayData.KELVIN), "DISPFLD 2,A,1"),
        (lambda ls: ls.set_beeper(ON), "BEEP 1"),
        (lambda ls: ls.set_lockout(ON, 123), "LOCK 1,123"),
        (lambda ls: ls.set_lockout(OFF, 7), "LOCK 0,007"),
        (lambda ls: ls.set_remote_mode(RemoteMode.REMOTE), "MODE 2"),
        (
            lambda ls: ls.set_serial_interface(
                SerialTerminator.CR_LF, BaudRate.BPS_19200, Parity.EIGHT_NONE
            ),
            "COMM 1,6,3",
        ),
        (lambda ls: ls.set_ieee_interface(IeeeTerminator.CR_LF, ON, 4), "IEEE 1,1,4"),
        (lambda ls: ls.set_scanner(ScanMode.AUTOSCAN, 1, 5), "XSCAN 2,1,5"),
        (lambda ls: ls.set_date_time(1996, 2, 3, 15, 30, 0), "DATETIME 2,3,1996,15,30,0,0"),
        (lambda ls: ls.reset_to_factory_defaults(), "DFLT 99"),
        (
            lambda ls: ls.set_curve_header(
                21, "DT-470", "00011134", CurveFormat.V_K, 325.0, Coefficient.NEGATIVE
            ),
            "CRVHDR 21,DT-470,00011134,2,325,1",
        ),
        (lambda ls: ls.set_curve_point(21, 2, 0.10191, 470.0), "CRVPT 21,2,0.10191,470"),
        (lambda ls: ls.delete_curve(21), "CRVDEL 21"),
        (lambda ls: ls.save_curves(), "CRVSAV"),
        (
            lambda ls: ls.generate_softcal(1, 21, "340000", 4.2, 1.626, 77.32, 1.0205, 300.0, 0.5189),
            "SCAL 1,21,340000,4.2,1.626,77.32,1.0205,300,0.5189",
        ),
        (
            lambda ls: ls.generate_softcal(1, 21, "340000", 4.2, 1.626, 77.32, 1.0205),
            "SCAL 1,21,340000,4.2,1.626,77.32,1.0205",
        ),
        (lambda ls: ls.add_program_line(1, ProgramCommand.CALL, "2"), "PGM 1,5,2"),
        (lambda ls: ls.add_program_line(1, ProgramCommand.END_REPEAT), "PGM 1,3"),
        (lambda ls: ls.delete_program(2), "PGMDEL 2"),
        (lambda ls: ls.run_program(1), "PGMRUN 1"),
        (lambda ls: ls.stop_program(), "PGMRUN 0"),
        (lambda ls: ls.set_logging(ON), "LOG 1"),
        (
            lambda ls: ls.set_log_setup(LogType.SECONDS, 10, OFF, LogStartMode.CONTINUE),
            "LOGSET 2,10,0,1",
        ),
        (
            lambda ls: ls.set_log_point(1, LogPointType.INPUT, A, DisplayData.KELVIN),
            "LOGPNT 1,1,A,1",
        ),
        (
            lambda ls: ls.set_log_point(2, LogPointType.OUTPUT_1, A, DisplayData.KELVIN),
            "LOGPNT 2,4",
        ),
    ],
)
def test_each_command_sends_the_manuals_message(visa, ls, call, sent):
    call(ls)
    assert visa.written[-1] == sent


def test_clearing_the_event_register_reads_it(visa, ls):
    visa.replies["*ESR?"] = "32"
    assert ls.clear_event_register() == 32
    assert visa.queried == ["*ESR?"]


# ------------------------------------------------------------------- queries
@pytest.mark.parametrize(
    "call, query, reply, result",
    [
        (lambda ls: ls.identify(), "*IDN?", "LSCI,MODEL340,123456,040102", "LSCI,MODEL340,123456,040102"),
        (lambda ls: ls.get_event_enable(), "*ESE?", "143", 143),
        (lambda ls: ls.get_event_status(), "*ESR?", "128", 128),
        (lambda ls: ls.get_operation_complete(), "*OPC?", "1", 1),
        (lambda ls: ls.get_service_request_enable(), "*SRE?", "089", 89),
        (lambda ls: ls.get_status_byte(), "*STB?", "004", 4),
        (lambda ls: ls.self_test(), "*TST?", "0", 0),
        (lambda ls: ls.get_temperature(A), "KRDG? A", "+004.2150E+0", 4.215),
        (lambda ls: ls.get_temperature_celsius(B), "CRDG? B", "-268.935E+0", -268.935),
        (lambda ls: ls.get_sensor_reading(A), "SRDG? A", "+1.62600E+0", 1.626),
        (lambda ls: ls.get_reading_status(A), "RDGST? A", "016", 16),
        (
            lambda ls: ls.get_alarm(B),
            "ALARM? B",
            "1,1,+270.000E+0,+000.000E+0,1,0",
            {"state": ON, "source": InputData.KELVIN, "high_value": 270.0, "low_value": 0.0,
             "latch": ON, "relay": OFF},
        ),
        (lambda ls: ls.get_alarm_status(A), "ALARMST? A", "1,0", {"high": ON, "low": OFF}),
        (lambda ls: ls.get_filter(B), "FILTER? B", "1,10,2", {"state": ON, "points": 10, "window": 2}),
        (lambda ls: ls.get_input_curve(A), "INCRV? A", "23", 23),
        (
            lambda ls: ls.get_input_setup(A),
            "INSET? A",
            "1,2",
            {"enabled": ON, "compensation": Compensation.PAUSE},
        ),
        (
            lambda ls: ls.get_input_type(A),
            "INTYPE? A",
            "2,1,1,06,11",
            {"sensor_type": SensorType.GAALAS_DIODE, "units": SensorUnits.VOLTS,
             "coefficient": Coefficient.NEGATIVE, "excitation": Excitation.CURRENT_10_UA,
             "input_range": InputRange.RANGE_2_5_V},
        ),
        (
            lambda ls: ls.get_linear_equation(A),
            "LINEAR? A",
            "1,+001.000,1,3,+000.000",
            {"equation": LinearEquation.MX_PLUS_B, "m": 1.0, "x_source": Units.KELVIN,
             "b_source": LinearOffset.MINUS_SETPOINT_1, "b": 0.0},
        ),
        (lambda ls: ls.get_linear_data(A), "LDAT? A", "-1.00000E+1", -10.0),
        (lambda ls: ls.get_linear_data_status(A), "LDATST? A", "000", 0),
        (
            lambda ls: ls.get_min_max(B),
            "MNMX? B",
            "2,4",
            {"mode": MinMaxMode.PAUSED, "source": InputData.LINEAR},
        ),
        (lambda ls: ls.get_min_max_data(A), "MDAT? A", "+4.2000E+0,+3.0000E+2", {"min": 4.2, "max": 300.0}),
        (lambda ls: ls.get_min_max_data_status(A), "MDATST? A", "000,032", {"min": 0, "max": 32}),
        (
            lambda ls: ls.get_control_loop(LOOP_1),
            "CSET? 1",
            "A,1,1,0",
            {"input_channel": A, "units": Units.KELVIN, "state": ON, "powerup": OFF},
        ),
        (lambda ls: ls.get_control_mode(LOOP_1), "CMODE? 1", "3", ControlMode.OPEN_LOOP),
        (lambda ls: ls.get_tuning(), "TUNEST?", "1", True),
        (lambda ls: ls.get_pid(LOOP_1), "PID? 1", "0025.0,0015.0,0006", {"p": 25.0, "i": 15.0, "d": 6.0}),
        (lambda ls: ls.get_setpoint(LOOP_1), "SETP? 1", "+122.500E+0", 122.5),
        (lambda ls: ls.get_ramp(LOOP_1), "RAMP? 1", "1,010.5", 10.5),
        (lambda ls: ls.get_ramp_state(LOOP_1), "RAMP? 1", "1,010.5", ON),
        (lambda ls: ls.get_ramping(LOOP_2), "RAMPST? 2", "0", False),
        (lambda ls: ls.get_manual_output(LOOP_1), "MOUT? 1", "+022.45", 22.45),
        (lambda ls: ls.get_heater_range(), "RANGE?", "3", HeaterRange.RANGE_3),
        (lambda ls: ls.get_heater_output(), "HTR?", "045.2", 45.2),
        (lambda ls: ls.get_heater_status(), "HTRST?", "00", 0),
        (
            lambda ls: ls.get_control_limits(LOOP_1),
            "CLIMIT? 1",
            "+325.000E+0,010.0,000.0,3,5",
            {"setpoint_limit": 325.0, "positive_slope": 10.0, "negative_slope": 0.0,
             "max_current": MaxCurrent.CURRENT_1, "max_range": HeaterRange.RANGE_5},
        ),
        (lambda ls: ls.get_max_user_current(), "CLIMI?", "1.500", 1.5),
        (lambda ls: ls.get_control_filter(LOOP_1), "CFILT? 1", "1", ON),
        (lambda ls: ls.get_settle(), "SETTLE?", "010.00,00010", {"threshold": 10.0, "seconds": 10}),
        (
            lambda ls: ls.get_zone(LOOP_1, 1),
            "ZONE? 1,1",
            "025.000,0010.0,0020.0,0000,+000.00,2",
            {"top": 25.0, "p": 10.0, "i": 20.0, "d": 0.0, "manual_output": 0.0,
             "heater_range": HeaterRange.RANGE_2},
        ),
        (
            lambda ls: ls.get_control_display(LOOP_1),
            "CDISP? 1",
            "1,0025,1,1",
            {"loops_shown": LoopDisplay.LOOP_1, "resistance": 25,
             "heater_display": HeaterDisplay.CURRENT, "large_output": ON},
        ),
        (
            lambda ls: ls.get_analog_output_setup(AnalogOutput.ANALOG_2),
            "ANALOG? 2",
            "0,1,A,1,+100.000E+0,+000.000E+0,+000.0",
            {"bipolar": OFF, "mode": AnalogMode.INPUT, "input_channel": A,
             "source": InputData.KELVIN, "high_value": 100.0, "low_value": 0.0,
             "manual_value": 0.0},
        ),
        (lambda ls: ls.get_analog_output(AnalogOutput.ANALOG_1), "AOUT? 1", "-025.5", -25.5),
        (lambda ls: ls.get_relay(Relay.LOW), "RELAY? 2", "2,1", {"mode": RelayMode.MANUAL, "state": ON}),
        (lambda ls: ls.get_relay_status(Relay.HIGH), "RELAYST? 1", "0", OFF),
        (
            lambda ls: ls.get_digital_output(),
            "DOUT?",
            "3,021",
            {"mode": DigitalOutputMode.MANUAL, "bits": 21},
        ),
        (lambda ls: ls.get_digital_io_status(), "DIOST?", "000,021", {"inputs": 0, "outputs": 21}),
        (lambda ls: ls.get_display(), "DISPLAY?", "3,060,1", {"fields": 3, "contrast": 60, "backlight": ON}),
        (lambda ls: ls.get_display_contrast(), "DISPLAY?", "3,060,1", 60),
        (
            lambda ls: ls.get_display_field(2),
            "DISPFLD? 2",
            "A,1",
            {"input_channel": A, "source": DisplayData.KELVIN},
        ),
        (lambda ls: ls.get_beeper(), "BEEP?", "1", ON),
        (lambda ls: ls.get_beeper_status(), "BEEPST?", "0", OFF),
        (lambda ls: ls.get_key_pressed(), "KEYST?", "1", True),
        (lambda ls: ls.get_lockout(), "LOCK?", "1,123", {"state": ON, "code": 123}),
        (lambda ls: ls.get_remote_mode(), "MODE?", "3", RemoteMode.REMOTE_LOCKOUT),
        (
            lambda ls: ls.get_serial_interface(),
            "COMM?",
            "1,6,3",
            {"terminator": SerialTerminator.CR_LF, "baud_rate": BaudRate.BPS_19200,
             "parity": Parity.EIGHT_NONE},
        ),
        (
            lambda ls: ls.get_ieee_interface(),
            "IEEE?",
            "1,1,04",
            {"terminator": IeeeTerminator.CR_LF, "eoi": ON, "address": 4},
        ),
        (
            lambda ls: ls.get_scanner(),
            "XSCAN?",
            "2,01,005",
            {"mode": ScanMode.AUTOSCAN, "channel": 1, "interval": 5},
        ),
        (lambda ls: ls.get_busy(), "BUSY?", "0", False),
        (
            lambda ls: ls.get_date_time(),
            "DATETIME?",
            "02,03,1996,15,30,00,250",
            datetime(1996, 2, 3, 15, 30, 0, 250000),
        ),
        (
            lambda ls: ls.get_curve_header(1),
            "CRVHDR? 1",
            "DT-470         ,Standard C ,2,+475.000,1",
            {"name": "DT-470", "serial_no": "Standard C", "curve_format": CurveFormat.V_K,
             "upper_limit": 475.0, "coefficient": Coefficient.NEGATIVE},
        ),
        (
            lambda ls: ls.get_curve_point(21, 2),
            "CRVPT? 21,2",
            "+0.10191E+0,+470.000E+0",
            {"sensor": 0.10191, "temperature": 470.0},
        ),
        (lambda ls: ls.get_program_line(1, 1), "PGM? 1,1", "5,2", "5,2"),
        (lambda ls: ls.get_program_memory(), "PGMMEM?", "640", 640),
        (lambda ls: ls.get_program_status(), "PGMRUN?", "01,0", {"program": 1, "status": 0}),
        (lambda ls: ls.get_logging(), "LOG?", "0", OFF),
        (lambda ls: ls.get_log_count(), "LOGCNT?", "12", 12),
        (
            lambda ls: ls.get_log_setup(),
            "LOGSET?",
            "2,10,0,1",
            {"log_type": LogType.SECONDS, "interval": 10, "overwrite": OFF,
             "start_mode": LogStartMode.CONTINUE},
        ),
        (
            lambda ls: ls.get_log_point(1),
            "LOGPNT? 1",
            "1,A,1",
            {"point_type": LogPointType.INPUT, "input_channel": A, "source": DisplayData.KELVIN},
        ),
        (
            lambda ls: ls.get_log_point(2),
            "LOGPNT? 2",
            "4",
            {"point_type": LogPointType.OUTPUT_1, "input_channel": None, "source": None},
        ),
        (lambda ls: ls.get_log_record(1, 1), "LOGVIEW? 1,1", "02,03,1996,15,30,00,000,+4.2E+0,0", "02,03,1996,15,30,00,000,+4.2E+0,0"),
    ],
)
def test_each_query_asks_the_manuals_question_and_reads_the_reply(visa, ls, call, query, reply, result):
    visa.replies[query] = reply
    assert call(ls) == result
    assert visa.queried[-1] == query


def test_revision_is_every_field_by_name(visa, ls):
    visa.replies["REV?"] = "040102,01.03.08,123456,000,040102,01.00.02,3462,040102,01.00.00"
    rev = ls.get_revision()
    assert rev["master_revision"] == "01.03.08"
    assert rev["option_id"] == "3462"
    assert len(rev) == 9


def test_logging_settings_with_no_data_card_are_zeros(visa, ls):
    visa.replies["LOGSET?"] = "0,0,0,0"
    assert ls.get_log_setup()["log_type"] is None


# ---------------------------------------------------------- in an experiment
def test_the_interface_can_call_its_queries_and_commands(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    ls = Lakeshore_340(
        "lakeshore",
        "GPIB0::12::INSTR",
        adapter="mock",
        responses={"DATETIME?": "02,03,1996,15,30,00,250", "HTR?": "045.2"},
    )
    experiment.add_instrument(ls)
    experiment._rack._register_endpoints(experiment._api_server)
    client = TestClient(experiment._api_server.app)

    assert client.get("/lakeshore/get_heater_output").json()["data"] == 45.2
    assert client.get("/lakeshore/get_date_time").json()["data"] == "1996-02-03T15:30:00.250000"
    answer = client.get(
        "/lakeshore/set_heater_range", params={"heater_range": "Range 3"}
    )
    assert answer.status_code == 200, answer.text
    answer = client.get(
        "/lakeshore/generate_softcal",
        params={"standard_curve": 1, "user_curve": 21, "serial_no": "X1",
                "t1": 4.2, "u1": 1.6, "t2": 77.3, "u2": 1.0},
    )
    assert answer.status_code == 200, answer.text
