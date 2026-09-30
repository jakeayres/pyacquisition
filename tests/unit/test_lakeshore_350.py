"""The Lakeshore 350's driver (instruments/lakeshore/lakeshore_350.py): each command
sends the message the manual (section 6.6) gives, each reply is taken apart, every
command in the manual's summary is there, the interface can call them, and the
methods it shares with the Lakeshore 340 are called the same way."""

import inspect
import re

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment
from pyacquisition.core.instrument import resolve_enum_kwargs
from pyacquisition.instruments import Lakeshore_340, Lakeshore_350, instrument_map
from pyacquisition.instruments.lakeshore import lakeshore_350 as module
from pyacquisition.instruments.lakeshore.lakeshore_350 import (
    AlarmType,
    AnalogOutput,
    AutotuneMode,
    Coefficient,
    ControlMode,
    CurveFormat,
    DiodeCurrent,
    DisplayData,
    DisplayMode,
    Excitation,
    HeaterDisplay,
    HeaterRange,
    HeaterResistance,
    InputChannel,
    Interface,
    LanStatus,
    MaxCurrent,
    OutputChannel,
    Relay,
    RelayMode,
    RemoteMode,
    SensorType,
    State,
    Units,
    WarmupControl,
)

A, B, C, D = InputChannel
OUT_1, OUT_2, OUT_3, OUT_4 = OutputChannel
ON, OFF = State.ON, State.OFF

# Every command in the manual's command summary (table 6-6).
MANUAL = """
*CLS *ESE *ESE? *ESR? *IDN? *OPC *OPC? *RST *SRE *SRE? *STB? *TST? *WAI
ALARM ALARM? ALARMST? ALMRST ANALOG ANALOG? AOUT? ATUNE BRIGT BRIGT? CRDG? CRVDEL
CRVHDR CRVHDR? CRVPT CRVPT? DFLT DIOCUR DISPFLD DISPFLD? DISPLAY DISPLAY? FILTER
FILTER? HTR? HTRSET HTRSET? HTRST? IEEE IEEE? INCRV INCRV? INNAME INNAME? INTSEL
INTSEL? INTYPE INTYPE? KRDG? LEDS LEDS? LOCK LOCK? MDAT? MNMXRST MODE MODE? MOUT
MOUT? NET NET? NETID? OPST? OPSTE OPSTE? OPSTR? OUTMODE OUTMODE? PID PID? RAMP RAMP?
RAMPST? RANGE RANGE? RDGST? RELAY RELAY? RELAYST? SCAL SETP SETP? SRDG? TEMP? TLIMIT
TLIMIT? TUNEST? WARMUP WARMUP? WEBLOG WEBLOG? ZONE ZONE?
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
    return Lakeshore_350("lakeshore", visa)


def test_registered_in_instrument_map():
    assert instrument_map["Lakeshore_350"] is Lakeshore_350


def test_init_only_clears_the_status_registers(visa, ls):
    assert visa.written == ["*CLS"]
    assert visa.queried == []


def test_every_public_method_is_a_query_or_a_command_and_says_what_it_does():
    for name, member in vars(Lakeshore_350).items():
        if name.startswith("_") or not callable(member) or isinstance(member, type):
            continue  # the enums that the class exposes are not methods
        assert hasattr(member, "_is_query") ^ hasattr(member, "_is_command"), name
        assert member.__doc__, name


def test_getters_are_queries_and_setters_are_commands():
    queries = {m.__name__ for m in Lakeshore_350._queries}
    commands = {m.__name__ for m in Lakeshore_350._commands}
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
    assert [c for c in MANUAL if c not in sent] == []


# ------------------------------------------------------------------ commands
@pytest.mark.parametrize(
    "call, sent",
    [
        (lambda ls: ls.reset(), "*RST"),
        (lambda ls: ls.set_event_enable(145), "*ESE 145"),
        (lambda ls: ls.operation_complete(), "*OPC"),
        (lambda ls: ls.wait_to_continue(), "*WAI"),
        (lambda ls: ls.set_service_request_enable(208), "*SRE 208"),
        (lambda ls: ls.set_operational_status_enable(12), "OPSTE 12"),
        (lambda ls: ls.set_alarm(B, ON, 270.0, 0.0, ON), "ALARM B,1,270,0,0,1,1,1"),
        (
            lambda ls: ls.set_alarm(A, ON, 300, 4, OFF, 0.5, OFF, ON),
            "ALARM A,1,300,4,0.5,0,0,1",
        ),
        (lambda ls: ls.reset_alarms(), "ALMRST"),
        (lambda ls: ls.set_filter(B, ON, 10, 2), "FILTER B,1,10,2"),
        (lambda ls: ls.set_input_curve(A, 23), "INCRV A,23"),
        (
            lambda ls: ls.set_input_type(
                A, SensorType.NTC_RTD, ON, 0, ON, Units.KELVIN, Excitation.VOLTAGE_10_MV
            ),
            "INTYPE A,3,1,0,1,1,1",
        ),
        (lambda ls: ls.set_input_name(A, "Sample Space"), 'INNAME A,"Sample Space"'),
        (lambda ls: ls.set_diode_current(D, DiodeCurrent.CURRENT_1_MA), "DIOCUR D,1"),
        (lambda ls: ls.reset_min_max(), "MNMXRST"),
        (lambda ls: ls.set_temperature_limit(B, 450), "TLIMIT B,450"),
        (
            lambda ls: ls.set_output_mode(OUT_1, ControlMode.ZONE, A, OFF),
            "OUTMODE 1,2,1,0",
        ),
        (lambda ls: ls.set_autotune_pid(OUT_2, AutotuneMode.PI), "ATUNE 2,1"),
        (lambda ls: ls.set_pid(OUT_1, 10, 50, 0), "PID 1,10,50,0"),
        (lambda ls: ls.set_setpoint(OUT_1, 122.5), "SETP 1,122.5"),
        (lambda ls: ls.set_ramp(OUT_1, ON, 10.5), "RAMP 1,1,10.500"),
        (lambda ls: ls.set_manual_output(OUT_1, 22.45), "MOUT 1,22.45"),
        (lambda ls: ls.set_heater_range(OUT_2, HeaterRange.RANGE_3), "RANGE 2,3"),
        (lambda ls: ls.set_heater_range(OUT_3, HeaterRange.RANGE_1), "RANGE 3,1"),
        (
            lambda ls: ls.set_heater_setup(
                OUT_1,
                HeaterResistance.OHM_25,
                MaxCurrent.CURRENT_1,
                0,
                HeaterDisplay.CURRENT,
            ),
            "HTRSET 1,1,2,0.000,1",
        ),
        (
            lambda ls: ls.set_zone(
                OUT_1, 1, 25.0, 10, 20, 0, 0, HeaterRange.RANGE_2, B, 10
            ),
            "ZONE 1,1,25,10,20,0,0.00,2,2,10",
        ),
        (
            lambda ls: ls.set_zone(OUT_1, 2, 50.0, 10, 20, 0, 0, HeaterRange.RANGE_3),
            "ZONE 1,2,50,10,20,0,0.00,3,0,0",
        ),
        (
            lambda ls: ls.set_analog_output_setup(
                AnalogOutput.OUTPUT_4, A, Units.KELVIN, 100.0, 0.0, OFF
            ),
            "ANALOG 4,1,1,100,0,0",
        ),
        (
            lambda ls: ls.set_warmup(
                AnalogOutput.OUTPUT_3, WarmupControl.CONTINUOUS, 50
            ),
            "WARMUP 3,1,50.00",
        ),
        (
            lambda ls: ls.set_relay(Relay.RELAY_1, RelayMode.ALARMS, B, AlarmType.LOW),
            "RELAY 1,2,B,0",
        ),
        (lambda ls: ls.set_display(DisplayMode.CUSTOM, 0, OUT_1), "DISPLAY 4,0,1"),
        (lambda ls: ls.set_display_contrast(16), "BRIGT 16"),
        (lambda ls: ls.set_display_field(2, A, DisplayData.KELVIN), "DISPFLD 2,1,1"),
        (lambda ls: ls.set_leds(OFF), "LEDS 0"),
        (lambda ls: ls.set_lockout(ON, 123), "LOCK 1,123"),
        (lambda ls: ls.set_remote_mode(RemoteMode.REMOTE_LOCKOUT), "MODE 2"),
        (lambda ls: ls.set_interface(Interface.ETHERNET), "INTSEL 1"),
        (lambda ls: ls.set_ieee_interface(4), "IEEE 4"),
        (
            lambda ls: ls.set_network(
                OFF,
                OFF,
                "192.168.0.12",
                "255.255.255.0",
                "192.168.0.1",
                "0.0.0.0",
                "0.0.0.0",
                "LS350",
                "lab.local",
                "Cryostat 1",
            ),
            'NET 0,0,192.168.0.12,255.255.255.0,192.168.0.1,0.0.0.0,0.0.0.0,"LS350",'
            '"lab.local","Cryostat 1"',
        ),
        (lambda ls: ls.set_web_login("user", "pass"), 'WEBLOG "user","pass"'),
        (lambda ls: ls.reset_to_factory_defaults(), "DFLT 99"),
        (
            lambda ls: ls.set_curve_header(
                21, "DT-470", "00011134", CurveFormat.V_K, 325.0, Coefficient.NEGATIVE
            ),
            "CRVHDR 21,DT-470,00011134,2,325,1",
        ),
        (
            lambda ls: ls.set_curve_point(21, 2, 0.10191, 470.0),
            "CRVPT 21,2,0.10191,470",
        ),
        (lambda ls: ls.delete_curve(21), "CRVDEL 21"),
        (
            lambda ls: ls.generate_softcal(
                1, 21, "1234567890", 4.2, 1.626, 77.32, 1.0205, 300.0, 0.5189
            ),
            "SCAL 1,21,1234567890,4.2,1.626,77.32,1.0205,300,0.5189",
        ),
    ],
)
def test_each_command_sends_the_manuals_message(visa, ls, call, sent):
    call(ls)
    assert visa.written[-1] == sent


def test_setting_the_control_mode_keeps_the_input_and_power_up(visa, ls):
    visa.replies["OUTMODE? 1"] = "1,2,1"
    ls.set_control_mode(OUT_1, ControlMode.OPEN_LOOP)
    assert visa.written[-1] == "OUTMODE 1,3,2,1"


def test_setting_the_control_input_keeps_the_mode_and_power_up(visa, ls):
    visa.replies["OUTMODE? 2"] = "2,1,0"
    ls.set_control_input(OUT_2, D)
    assert visa.written[-1] == "OUTMODE 2,2,4,0"


def test_outputs_3_and_4_are_not_heaters(visa, ls):
    with pytest.raises(ValueError, match="isn't a heater"):
        ls.get_heater_status(OUT_3)
    assert visa.queried == []


def test_an_input_of_the_3062_card_says_what_it_is(visa, ls):
    visa.replies["OUTMODE? 1"] = "1,6,0"
    with pytest.raises(ValueError, match="3062 card"):
        ls.get_output_mode(OUT_1)


# ------------------------------------------------------------------- queries
@pytest.mark.parametrize(
    "call, query, reply, result",
    [
        (
            lambda ls: ls.identify(),
            "*IDN?",
            "LSCI,MODEL350,1234567/1234567,1.0",
            "LSCI,MODEL350,1234567/1234567,1.0",
        ),
        (lambda ls: ls.get_event_enable(), "*ESE?", "145", 145),
        (lambda ls: ls.get_event_status(), "*ESR?", "128", 128),
        (lambda ls: ls.get_operation_complete(), "*OPC?", "1", 1),
        (lambda ls: ls.get_service_request_enable(), "*SRE?", "208", 208),
        (lambda ls: ls.get_status_byte(), "*STB?", "016", 16),
        (lambda ls: ls.self_test(), "*TST?", "0", 0),
        (lambda ls: ls.get_operational_status(), "OPST?", "064", 64),
        (lambda ls: ls.get_operational_status_register(), "OPSTR?", "002", 2),
        (lambda ls: ls.get_operational_status_enable(), "OPSTE?", "012", 12),
        (lambda ls: ls.get_temperature(A), "KRDG? A", "+004.2150", 4.215),
        (
            lambda ls: ls.get_all_temperatures(),
            "KRDG? 0",
            "+4.2150,+77.000,+300.00,+0.0000",
            {"INPUT_A": 4.215, "INPUT_B": 77.0, "INPUT_C": 300.0, "INPUT_D": 0.0},
        ),
        (lambda ls: ls.get_temperature_celsius(B), "CRDG? B", "-268.935", -268.935),
        (lambda ls: ls.get_sensor_reading(A), "SRDG? A", "+1000.00", 1000.0),
        (lambda ls: ls.get_reading_status(A), "RDGST? A", "000", 0),
        (lambda ls: ls.get_junction_temperature(), "TEMP?", "+295.12", 295.12),
        (
            lambda ls: ls.get_alarm(B),
            "ALARM? B",
            "1,+270.000,+0.00000,+0.00000,1,1,1",
            {
                "state": ON,
                "high_value": 270.0,
                "low_value": 0.0,
                "deadband": 0.0,
                "latch": ON,
                "audible": ON,
                "visible": ON,
            },
        ),
        (
            lambda ls: ls.get_alarm_status(A),
            "ALARMST? A",
            "0,1",
            {"high": OFF, "low": ON},
        ),
        (
            lambda ls: ls.get_filter(B),
            "FILTER? B",
            "1,10,2",
            {"state": ON, "points": 10, "window": 2},
        ),
        (lambda ls: ls.get_input_curve(A), "INCRV? A", "23", 23),
        (
            lambda ls: ls.get_input_type(A),
            "INTYPE? A",
            "3,1,4,1,1,1",
            {
                "sensor_type": SensorType.NTC_RTD,
                "autorange": ON,
                "input_range": 4,
                "compensation": ON,
                "units": Units.KELVIN,
                "excitation": Excitation.VOLTAGE_10_MV,
            },
        ),
        (
            lambda ls: ls.get_input_name(A),
            "INNAME? A",
            '"Sample Space   "',
            "Sample Space",
        ),
        (
            lambda ls: ls.get_min_max_data(A),
            "MDAT? A",
            "+4.2000,+300.00",
            {"min": 4.2, "max": 300.0},
        ),
        (lambda ls: ls.get_temperature_limit(B), "TLIMIT? B", "+450.0", 450.0),
        (
            lambda ls: ls.get_output_mode(OUT_1),
            "OUTMODE? 1",
            "2,1,0",
            {"mode": ControlMode.ZONE, "input_channel": A, "powerup": OFF},
        ),
        (
            lambda ls: ls.get_control_mode(OUT_1),
            "OUTMODE? 1",
            "3,2,1",
            ControlMode.OPEN_LOOP,
        ),
        (lambda ls: ls.get_control_input(OUT_1), "OUTMODE? 1", "3,2,1", B),
        (lambda ls: ls.get_control_input(OUT_3), "OUTMODE? 3", "0,0,0", None),
        (lambda ls: ls.get_tuning(), "TUNEST?", "1,2,0,03", True),
        (
            lambda ls: ls.get_tuning_status(),
            "TUNEST?",
            "0,1,1,00",
            {"tuning": False, "output_channel": OUT_1, "error": True, "stage": 0},
        ),
        (
            lambda ls: ls.get_pid(OUT_1),
            "PID? 1",
            "+10.0,+50.0,+0",
            {"p": 10.0, "i": 50.0, "d": 0.0},
        ),
        (lambda ls: ls.get_setpoint(OUT_1), "SETP? 1", "+122.500", 122.5),
        (lambda ls: ls.get_ramp(OUT_1), "RAMP? 1", "1,10.5", 10.5),
        (lambda ls: ls.get_ramp_state(OUT_1), "RAMP? 1", "1,10.5", ON),
        (lambda ls: ls.get_ramping(OUT_2), "RAMPST? 2", "1", True),
        (lambda ls: ls.get_manual_output(OUT_1), "MOUT? 1", "+22.45", 22.45),
        (lambda ls: ls.get_heater_range(OUT_1), "RANGE? 1", "3", HeaterRange.RANGE_3),
        (lambda ls: ls.get_heater_output(OUT_1), "HTR? 1", "+045.2", 45.2),
        (lambda ls: ls.get_heater_output(OUT_3), "AOUT? 3", "-012.5", -12.5),
        (lambda ls: ls.get_heater_status(OUT_2), "HTRST? 2", "1", 1),
        (
            lambda ls: ls.get_heater_setup(OUT_1),
            "HTRSET? 1",
            "1,2,+0.000,1",
            {
                "resistance": HeaterResistance.OHM_25,
                "max_current": MaxCurrent.CURRENT_1,
                "max_user_current": 0.0,
                "heater_display": HeaterDisplay.CURRENT,
            },
        ),
        (
            lambda ls: ls.get_zone(OUT_1, 1),
            "ZONE? 1,1",
            "+25.000,+10.0,+20.0,+0,+0.00,2,2,+10.0",
            {
                "top": 25.0,
                "p": 10.0,
                "i": 20.0,
                "d": 0.0,
                "manual_output": 0.0,
                "heater_range": HeaterRange.RANGE_2,
                "input_channel": B,
                "rate": 10.0,
            },
        ),
        (
            lambda ls: ls.get_analog_output_setup(AnalogOutput.OUTPUT_4),
            "ANALOG? 4",
            "1,1,+100.000,+0.000,0",
            {
                "input_channel": A,
                "source": Units.KELVIN,
                "high_value": 100.0,
                "low_value": 0.0,
                "bipolar": OFF,
            },
        ),
        (
            lambda ls: ls.get_analog_output(AnalogOutput.OUTPUT_3),
            "AOUT? 3",
            "+050.0",
            50.0,
        ),
        (
            lambda ls: ls.get_warmup(AnalogOutput.OUTPUT_3),
            "WARMUP? 3",
            "1,+50.00",
            {"control": WarmupControl.CONTINUOUS, "percent": 50.0},
        ),
        (
            lambda ls: ls.get_relay(Relay.RELAY_1),
            "RELAY? 1",
            "2,B,0",
            {"mode": RelayMode.ALARMS, "input_channel": B, "alarm_type": AlarmType.LOW},
        ),
        (lambda ls: ls.get_relay_status(Relay.RELAY_2), "RELAYST? 2", "1", ON),
        (
            lambda ls: ls.get_display(),
            "DISPLAY?",
            "4,0,1",
            {"mode": DisplayMode.CUSTOM, "fields": 0, "output_channel": OUT_1},
        ),
        (lambda ls: ls.get_display_contrast(), "BRIGT?", "16", 16),
        (
            lambda ls: ls.get_display_field(2),
            "DISPFLD? 2",
            "1,1",
            {"input_channel": A, "source": DisplayData.KELVIN},
        ),
        (lambda ls: ls.get_leds(), "LEDS?", "1", ON),
        (lambda ls: ls.get_lockout(), "LOCK?", "1,123", {"state": ON, "code": 123}),
        (lambda ls: ls.get_remote_mode(), "MODE?", "1", RemoteMode.REMOTE),
        (lambda ls: ls.get_interface(), "INTSEL?", "2", Interface.IEEE_488),
        (lambda ls: ls.get_ieee_interface(), "IEEE?", "12", {"address": 12}),
        (
            lambda ls: ls.get_network(),
            "NET?",
            "0,1,192.168.000.012,255.255.255.000,192.168.000.001,000.000.000.000,"
            '000.000.000.000,"LS350          ","lab.local","Cryostat 1"',
            {
                "dhcp": OFF,
                "auto_ip": ON,
                "ip": "192.168.000.012",
                "subnet_mask": "255.255.255.000",
                "gateway": "192.168.000.001",
                "primary_dns": "000.000.000.000",
                "secondary_dns": "000.000.000.000",
                "hostname": "LS350",
                "domain": "lab.local",
                "description": "Cryostat 1",
            },
        ),
        (
            lambda ls: ls.get_network_status(),
            "NETID?",
            "1,192.168.000.012,255.255.255.000,192.168.000.001,000.000.000.000,"
            '000.000.000.000,00:11:22:33:44:55,"LS350","lab.local"',
            {
                "lan_status": LanStatus.DHCP,
                "ip": "192.168.000.012",
                "subnet_mask": "255.255.255.000",
                "gateway": "192.168.000.001",
                "primary_dns": "000.000.000.000",
                "secondary_dns": "000.000.000.000",
                "mac_address": "00:11:22:33:44:55",
                "hostname": "LS350",
                "domain": "lab.local",
            },
        ),
        (
            lambda ls: ls.get_web_login(),
            "WEBLOG?",
            '"user           ","pass           "',
            {"username": "user", "password": "pass"},
        ),
        (
            lambda ls: ls.get_curve_header(1),
            "CRVHDR? 1",
            "DT-470         ,Standard C,2,+475.000,1",
            {
                "name": "DT-470",
                "serial_no": "Standard C",
                "curve_format": CurveFormat.V_K,
                "upper_limit": 475.0,
                "coefficient": Coefficient.NEGATIVE,
            },
        ),
        (
            lambda ls: ls.get_curve_point(21, 2),
            "CRVPT? 21,2",
            "+0.10191,+470.000",
            {"sensor": 0.10191, "temperature": 470.0},
        ),
    ],
)
def test_each_query_asks_the_manuals_question_and_reads_the_reply(
    visa, ls, call, query, reply, result
):
    visa.replies[query] = reply
    assert call(ls) == result
    assert visa.queried[-1] == query


# ------------------------------------------------- interchangeable with the 340
def arguments(cls, name):
    return list(inspect.signature(getattr(cls, name)).parameters)[1:]


def shared_methods():
    names = lambda cls: {m.__name__ for m in (*cls._queries, *cls._commands)}  # noqa: E731
    return sorted(names(Lakeshore_340) & names(Lakeshore_350))


def test_most_of_what_they_do_they_both_do():
    assert len(shared_methods()) >= 76


@pytest.mark.parametrize("name", shared_methods())
def test_a_shared_method_takes_the_same_arguments_first(name):
    """The same call works on either: where one takes more, it takes them last, with
    defaults, or they are different instruments' own (a relay, the display)."""
    own = {"set_relay", "set_display", "set_input_type"}  # different hardware
    if name in own:
        return
    a, b = arguments(Lakeshore_340, name), arguments(Lakeshore_350, name)
    shared = 0
    while shared < min(len(a), len(b)) and a[shared] == b[shared]:
        shared += 1
    for cls in (Lakeshore_340, Lakeshore_350):
        rest = list(inspect.signature(getattr(cls, name)).parameters.values())[
            1 + shared :
        ]
        assert all(p.default is not inspect.Parameter.empty for p in rest), (cls, a, b)


@pytest.mark.parametrize(
    "enum, members",
    [
        ("State", None),
        ("InputChannel", None),
        ("Units", None),
        ("HeaterRange", None),
        ("HeaterDisplay", None),
        ("AutotuneMode", None),
        ("RemoteMode", None),
        ("Coefficient", None),
        ("ControlMode", {"PID", "ZONE", "OPEN_LOOP"}),
        ("OutputChannel", {"OUTPUT_1", "OUTPUT_2"}),
        ("CurveFormat", {"MV_K", "V_K", "OHM_K", "LOGOHM_K"}),
        ("MaxCurrent", {"CURRENT_1", "CURRENT_2", "USER"}),
    ],
)
def test_the_shared_choices_have_the_same_names(enum, members):
    names = lambda cls: {m.name for m in getattr(cls, enum)}  # noqa: E731
    if members is None:
        assert names(Lakeshore_340) == names(Lakeshore_350)
    else:
        assert members <= names(Lakeshore_340) and members <= names(Lakeshore_350)


def open_loop(ls, percent):
    """Drives a heater by hand, written once for either controller."""
    output = ls.OutputChannel.OUTPUT_1
    ls.set_control_input(output, ls.InputChannel.INPUT_B)
    ls.set_control_mode(output, ls.ControlMode.OPEN_LOOP)
    ls.set_heater_range(output, ls.HeaterRange.RANGE_3)
    ls.set_manual_output(output, percent)
    return ls.get_temperature(ls.InputChannel.INPUT_B), ls.get_heater_output(output)


@pytest.mark.parametrize(
    "cls, replies, sent",
    [
        (
            Lakeshore_340,
            {"KRDG? B": "4.2", "HTR?": "40.0"},
            ["CSET 1,B", "CMODE 1,3", "RANGE 3", "MOUT 1,40.00"],
        ),
        (
            Lakeshore_350,
            {"KRDG? B": "4.2", "HTR? 1": "40.0", "OUTMODE? 1": "1,2,1"},
            ["OUTMODE 1,1,2,1", "OUTMODE 1,3,2,1", "RANGE 1,3", "MOUT 1,40.00"],
        ),
    ],
    ids=["340", "350"],
)
def test_the_same_code_drives_either_controller(cls, replies, sent):
    visa = FakeVisa()
    visa.replies.update(replies)
    ls = cls("lakeshore", visa)
    visa.written.clear()
    if cls is Lakeshore_350:
        # the second OUTMODE? answers what the first OUTMODE set
        answers = iter(["1,1,1", "1,2,1"])
        visa.query = lambda text: (
            visa.queried.append(text)
            or (next(answers) if text == "OUTMODE? 1" else visa.replies.get(text, "0"))
        )
    assert open_loop(ls, 40.0) == (4.2, 40.0)
    assert visa.written == sent


@pytest.mark.parametrize("cls", [Lakeshore_340, Lakeshore_350])
def test_a_choice_given_as_text_works_on_either(cls):
    kwargs = resolve_enum_kwargs(
        cls.set_control_mode, {"output_channel": "OUTPUT_1", "mode": "OPEN_LOOP"}
    )
    assert kwargs["mode"] is cls.ControlMode.OPEN_LOOP
    assert kwargs["output_channel"] is cls.OutputChannel.OUTPUT_1


# ---------------------------------------------------------- in an experiment
def test_the_interface_can_call_its_queries_and_commands(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    ls = Lakeshore_350(
        "lakeshore",
        "GPIB0::12::INSTR",
        adapter="mock",
        responses={"HTR? 1": "045.2", "OUTMODE? 1": "1,1,0"},
    )
    experiment.add_instrument(ls)
    experiment._rack._register_endpoints(experiment._api_server)
    client = TestClient(experiment._api_server.app)

    answer = client.get(
        "/lakeshore/get_heater_output", params={"output_channel": "Output 1"}
    )
    assert answer.json()["data"] == 45.2
    answer = client.get(
        "/lakeshore/set_control_mode",
        params={"output_channel": "Output 1", "mode": "Open loop"},
    )
    assert answer.status_code == 200, answer.text
    answer = client.get(
        "/lakeshore/set_zone",
        params={
            "output_channel": "Output 1",
            "zone": 1,
            "top": 25,
            "p": 10,
            "i": 20,
            "d": 0,
            "manual_output": 0,
            "heater_range": "Range 2",
        },
    )
    assert answer.status_code == 200, answer.text
