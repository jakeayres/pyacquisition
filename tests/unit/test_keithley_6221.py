import math

import pytest

from pyacquisition.instruments import Keithley_6221, instrument_map
from pyacquisition.instruments.keithley import keithley_6221 as module
from pyacquisition.instruments.keithley.keithley_6221 import (
    ArmSource,
    DisplayLine,
    InnerShield,
    Key,
    ListParameter,
    PowerOnSetup,
    ReadingElement,
    ReadingUnits,
    State,
    StatusRegister,
    SweepSpacing,
    TriggerLayer,
    WaveFunction,
)


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
def k(visa):
    return Keithley_6221("k", visa)


def test_registered_in_instrument_map():
    assert instrument_map["Keithley_6221"] is Keithley_6221


def test_init_clears_status_and_selects_ascii(visa, k):
    assert visa.written == ["*CLS", "FORM:SREG ASC", "FORM ASC"]


def test_every_public_method_is_a_query_or_a_command():
    for name, member in vars(Keithley_6221).items():
        if name.startswith("_") or not callable(member):
            continue
        assert hasattr(member, "_is_query") ^ hasattr(member, "_is_command"), name
        assert member.__doc__, name


def test_getters_are_queries_and_setters_are_commands():
    queries = {m.__name__ for m in Keithley_6221._queries}
    commands = {m.__name__ for m in Keithley_6221._commands}
    assert all(
        name.startswith("get_") or name in {"identify", "self_test"} for name in queries
    )
    assert not any(name.startswith("get_") for name in commands)
    assert "get_operation_complete" in queries


def test_no_duplicate_definitions():
    with open(module.__file__, encoding="utf-8") as f:
        source = f.read()
    names = [
        line.split("def ")[1].split("(")[0]
        for line in source.splitlines()
        if line.startswith("    def ")
    ]
    assert len(names) == len(set(names))


# -------------------------------------------------------------- formatting
def test_currents_are_sent_in_scientific_notation(visa, k):
    k.set_current(1e-12)
    k.set_current(-0.0123456789)
    assert visa.written[-2:] == ["SOUR:CURR 1.000000e-12", "SOUR:CURR -1.234568e-02"]


def test_small_values_are_not_truncated(visa, k):
    k.set_sweep_step(1e-13)
    assert visa.written[-1] == "SOUR:CURR:STEP 1.000000e-13"


def test_infinite_counts_and_durations(visa, k):
    k.set_delta_count(math.inf)
    k.set_delta_count(10)
    k.set_wave_duration_time(math.inf)
    k.set_wave_duration_time(2.5)
    assert visa.written[-4:] == [
        "SOUR:DELT:COUN INF",
        "SOUR:DELT:COUN 10",
        "SOUR:WAVE:DUR:TIME INF",
        "SOUR:WAVE:DUR:TIME 2.500000e+00",
    ]


def test_infinite_count_reply_is_read_as_a_float(visa, k):
    visa.replies["SOUR:DELT:COUN?"] = "+9.9E37"
    assert k.get_delta_count() > 1e37
    visa.replies["SOUR:DELT:COUN?"] = "INF"
    assert k.get_delta_count() == math.inf


# -------------------------------------------------------------- getters
def test_float_getter(visa, k):
    visa.replies["SOUR:CURR?"] = "+1.500000E-03\n"
    assert k.get_current() == pytest.approx(1.5e-3)


def test_int_getter_accepts_scientific_notation(visa, k):
    visa.replies["SOUR:SWE:POIN?"] = "+1.100000E+01"
    assert k.get_sweep_points() == 11


def test_state_round_trip(visa, k):
    k.set_output_state(State.ON)
    assert visa.written[-1] == "OUTP 1"
    visa.replies["OUTP?"] = "1"
    assert k.get_output_state() is State.ON
    visa.replies["OUTP?"] = "0"
    assert k.get_output_state() is State.OFF


@pytest.mark.parametrize(
    "reply, expected",
    [
        ("SIN", WaveFunction.SINUSOID),
        ("SQU", WaveFunction.SQUARE),
        ("SQUARE", WaveFunction.SQUARE),
        ('"ARB3"', WaveFunction.ARBITRARY_3),
        ("ramp\n", WaveFunction.RAMP),
    ],
)
def test_enum_replies_accept_short_and_long_forms(visa, k, reply, expected):
    visa.replies["SOUR:WAVE:FUNC?"] = reply
    assert k.get_wave_function() is expected


def test_enum_prefixes_do_not_confuse_members(visa, k):
    visa.replies["SOUR:SWE:SPAC?"] = "LIST"
    assert k.get_sweep_spacing() is SweepSpacing.LIST
    visa.replies["SOUR:SWE:SPAC?"] = "LIN"
    assert k.get_sweep_spacing() is SweepSpacing.LINEAR
    visa.replies["TRAC:FEED?"] = "CALC1"
    assert k.get_buffer_feed().raw_value == "CALC1"


def test_unknown_enum_reply_raises(visa, k):
    visa.replies["SOUR:WAVE:FUNC?"] = "TRI"
    with pytest.raises(ValueError):
        k.get_wave_function()


def test_flags(visa, k):
    visa.replies["SOUR:DELT:ARM?"] = "1"
    assert k.get_delta_armed() is True
    visa.replies["OUTP:INT:TRIP?"] = "0"
    assert k.get_interlock_closed() is False


# -------------------------------------------------------------- commands
def test_enum_setters(visa, k):
    k.set_inner_shield(InnerShield.GUARD)
    k.set_reading_units(ReadingUnits.SIEMENS)
    k.set_wave_function(WaveFunction.ARBITRARY_2)
    k.set_arm_source(ArmSource.TRIGGER_LINK)
    k.set_power_on_setup(PowerOnSetup.SAVED_4)
    assert visa.written[-5:] == [
        "OUTP:ISH GUAR",
        "UNIT:VOLT:DC SIEM",
        "SOUR:WAVE:FUNC ARB2",
        "ARM:SOUR TLIN",
        "SYST:POS SAV4",
    ]


def test_layer_commands_share_one_method(visa, k):
    k.set_layer_input_line(TriggerLayer.ARM, 3)
    k.set_layer_input_line(TriggerLayer.TRIGGER, 4)
    k.bypass_layer(TriggerLayer.TRIGGER)
    assert visa.written[-3:] == [
        "ARM:TCON:ASYN:ILIN 3",
        "TRIG:TCON:ASYN:ILIN 4",
        "TRIG:SIGN",
    ]
    visa.replies["TRIG:TCON:ASYN:ILIN?"] = "4"
    assert k.get_layer_input_line(TriggerLayer.TRIGGER) == 4


def test_lists(visa, k):
    k.set_list(ListParameter.CURRENT, [1e-3, -2e-3])
    k.append_list(ListParameter.DELAY, [0.5])
    assert visa.written[-2:] == [
        "SOUR:LIST:CURR 1.000000e-03,-2.000000e-03",
        "SOUR:LIST:DEL:APP 5.000000e-01",
    ]
    visa.replies["SOUR:LIST:CURR?"] = "+1.0E-03,-2.0E-03"
    assert k.get_list(ListParameter.CURRENT) == [1e-3, -2e-3]
    visa.replies["SOUR:LIST:CURR:POIN?"] = "2"
    assert k.get_list_points(ListParameter.CURRENT) == 2


def test_arbitrary_points(visa, k):
    k.set_arbitrary_data([-1, 0, 1])
    assert visa.written[-1] == (
        "SOUR:WAVE:ARB:DATA -1.000000e+00,0.000000e+00,1.000000e+00"
    )


def test_display_text_uses_the_line(visa, k):
    k.set_display_text(DisplayLine.BOTTOM, "hello")
    assert visa.written[-1] == "DISP:WIND2:TEXT:DATA 'hello'"
    visa.replies["DISP:WIND1:TEXT:DATA?"] = '"hi"'
    assert k.get_display_text(DisplayLine.TOP) == "hi"


def test_status_registers(visa, k):
    k.set_status_enable(StatusRegister.MEASUREMENT, 512)
    assert visa.written[-1] == "STAT:MEAS:ENAB 512"
    visa.replies["STAT:OPER:EVEN?"] = "+16"
    assert k.get_status_event(StatusRegister.OPERATION) == 16
    visa.replies["STAT:QUES:COND?"] = "0"
    assert k.get_status_condition(StatusRegister.QUESTIONABLE) == 0


def test_error_queue(visa, k):
    visa.replies["SYST:ERR?"] = '-222,"Parameter data out of range"'
    assert k.get_error() == {"code": -222, "message": "Parameter data out of range"}
    visa.replies["STAT:QUE?"] = '0,"No error"'
    assert k.get_next_error() == {"code": 0, "message": "No error"}


def test_error_message_containing_a_comma(visa, k):
    visa.replies["SYST:ERR?"] = '-100,"Command error, unknown header"'
    assert k.get_error()["message"] == "Command error, unknown header"


def test_readings_ignore_units_suffix(visa, k):
    visa.replies["SENS:DATA?"] = "+1.23456789E-03VDC,+0.000SECS"
    assert k.get_latest_reading() == pytest.approx(1.23456789e-3)
    visa.replies["CALC1:DATA?"] = "-4.5E+00OHM"
    assert k.get_math_reading() == pytest.approx(-4.5)
    visa.replies["SENS:DATA:FRES?"] = "+9.9E37"
    assert k.get_fresh_reading() == pytest.approx(9.9e37)


def test_reading_without_a_number_raises(visa, k):
    visa.replies["SENS:DATA?"] = "garbage"
    with pytest.raises(ValueError):
        k.get_latest_reading()


def test_reading_elements(visa, k):
    k.set_reading_elements([ReadingElement.READING, ReadingElement.COMPLIANCE])
    assert visa.written[-1] == "FORM:ELEM READ,COMP"
    visa.replies["FORM:ELEM?"] = "READ,TST,UNIT"
    assert k.get_reading_elements() == [
        ReadingElement.READING,
        ReadingElement.TIMESTAMP,
        ReadingElement.UNITS,
    ]


def test_press_key_and_last_key(visa, k):
    k.press_key(Key.DC)
    assert visa.written[-1] == "SYST:KEY 29"
    visa.replies["SYST:KEY?"] = "33"
    assert k.get_last_key() is Key.KNOB_PUSH


def test_buffer_selected_reading(visa, k):
    visa.replies["TRAC:DATA:SEL? 3,2"] = "1,2"
    assert k.get_buffer_selected(3, 2) == "1,2"


def test_event_register_is_queried_not_written(visa, k):
    visa.replies["*ESR?"] = "1"
    assert k.get_event_status() == 1
    assert "*ESR?" in visa.queried
    assert "*ESR" not in visa.written


def test_preset_waits_for_completion(visa, k):
    k.preset()
    assert visa.written[-1] == "SYST:PRES"
    assert visa.queried[-1] == "*OPC?"
