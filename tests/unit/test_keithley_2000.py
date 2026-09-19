import math

import pytest

from pyacquisition.instruments import Keithley_2000, instrument_map
from pyacquisition.instruments.keithley import _scpi
from pyacquisition.instruments.keithley import keithley_2000 as module
from pyacquisition.instruments.keithley.keithley_2000 import (
    BandwidthFunction,
    DigitsFunction,
    FilterFunction,
    Function,
    Key,
    MathFormat,
    NplcFunction,
    PowerOnSetup,
    RangeFunction,
    ReferenceFunction,
    ScanMode,
    State,
    StatusRegister,
    TemperatureUnit,
    ThresholdFunction,
    TriggerSource,
    VoltageUnit,
    format_channels,
    parse_channels,
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
def dmm(visa):
    return Keithley_2000("dmm", visa)


def test_registered_in_instrument_map():
    assert instrument_map["Keithley_2000"] is Keithley_2000


def test_init_clears_status_and_selects_plain_ascii_readings(visa, dmm):
    assert visa.written == ["*CLS", "FORM ASC", "FORM:ELEM READ"]


def test_every_public_method_is_a_query_or_a_command():
    for name, member in vars(Keithley_2000).items():
        if name.startswith("_") or not callable(member):
            continue
        assert hasattr(member, "_is_query") ^ hasattr(member, "_is_command"), name
        assert member.__doc__, name


def test_getters_are_queries_and_setters_are_commands():
    queries = {m.__name__ for m in Keithley_2000._queries}
    commands = {m.__name__ for m in Keithley_2000._commands}
    actions = {"identify", "self_test", "fetch", "read", "measure"}
    assert all(n.startswith("get_") or n in actions for n in queries)
    assert not any(n.startswith("get_") for n in commands)


def test_no_duplicate_definitions():
    with open(module.__file__, encoding="utf-8") as f:
        source = f.read()
    names = [
        line.split("def ")[1].split("(")[0]
        for line in source.splitlines()
        if line.startswith("    def ")
    ]
    assert len(names) == len(set(names))


def test_the_keithley_classes_share_their_helpers():
    from pyacquisition.instruments.keithley import keithley_6221

    assert State is _scpi.State is keithley_6221.State
    assert StatusRegister is keithley_6221.StatusRegister


# ------------------------------------------------------------ functions
def names(enum):
    return {member.name for member in enum}


def test_each_setting_only_accepts_the_functions_that_have_it():
    assert names(BandwidthFunction) == {"AC_VOLTAGE", "AC_CURRENT"}
    assert names(ThresholdFunction) == {"FREQUENCY", "PERIOD"}
    assert "TEMPERATURE" not in names(RangeFunction)  # one fixed range
    assert names(NplcFunction) == names(RangeFunction) | {"TEMPERATURE"}
    assert names(FilterFunction) == names(NplcFunction)
    assert names(DigitsFunction) == names(ReferenceFunction)
    assert {"FREQUENCY", "PERIOD"} <= names(DigitsFunction)
    assert {"DIODE", "CONTINUITY"}.isdisjoint(names(DigitsFunction))
    assert len(Function) == 11


@pytest.mark.parametrize(
    "function, path",
    [
        (NplcFunction.DC_VOLTAGE, "VOLT:DC"),
        (NplcFunction.AC_VOLTAGE, "VOLT:AC"),
        (NplcFunction.DC_CURRENT, "CURR:DC"),
        (NplcFunction.AC_CURRENT, "CURR:AC"),
        (NplcFunction.RESISTANCE, "RES"),
        (NplcFunction.RESISTANCE_4W, "FRES"),
        (NplcFunction.TEMPERATURE, "TEMP"),
    ],
)
def test_a_setting_is_sent_to_the_path_of_its_function(visa, dmm, function, path):
    dmm.set_nplc(function, 0.1)
    assert visa.written[-1] == f"SENS:{path}:NPLC 1.000000e-01"
    visa.replies[f"SENS:{path}:NPLC?"] = "+1.000000E-01"
    assert dmm.get_nplc(function) == pytest.approx(0.1)


def test_settings_of_other_functions(visa, dmm):
    dmm.set_bandwidth(BandwidthFunction.AC_CURRENT, 30)
    dmm.set_threshold_range(ThresholdFunction.PERIOD, 10)
    dmm.set_digits(DigitsFunction.FREQUENCY, 6)
    dmm.set_average_filter_count(FilterFunction.TEMPERATURE, 20)
    dmm.set_auto_range(RangeFunction.RESISTANCE_4W, State.ON)
    assert visa.written[-5:] == [
        "SENS:CURR:AC:DET:BAND 3.000000e+01",
        "SENS:PER:THR:VOLT:RANG 1.000000e+01",
        "SENS:FREQ:DIG 6",
        "SENS:TEMP:AVER:COUN 20",
        "SENS:FRES:RANG:AUTO 1",
    ]


def test_range_reports_the_full_scale_value(visa, dmm):
    dmm.set_range(RangeFunction.DC_VOLTAGE, 0.05)
    assert visa.written[-1] == "SENS:VOLT:DC:RANG:UPP 5.000000e-02"
    visa.replies["SENS:VOLT:DC:RANG:UPP?"] = "+1.000000E-01"
    assert dmm.get_range(RangeFunction.DC_VOLTAGE) == pytest.approx(0.1)


def test_reference_and_acquire(visa, dmm):
    dmm.set_reference(ReferenceFunction.FREQUENCY, 100)
    dmm.set_reference_state(ReferenceFunction.FREQUENCY, State.ON)
    dmm.acquire_reference(ReferenceFunction.DC_VOLTAGE)
    assert visa.written[-3:] == [
        "SENS:FREQ:REF 1.000000e+02",
        "SENS:FREQ:REF:STAT 1",
        "SENS:VOLT:DC:REF:ACQ",
    ]


def test_the_selected_function_is_quoted(visa, dmm):
    dmm.set_function(Function.DIODE)
    dmm.set_function(Function.RESISTANCE_4W)
    assert visa.written[-2:] == ["SENS:FUNC 'DIOD'", "SENS:FUNC 'FRES'"]


@pytest.mark.parametrize("function", list(Function), ids=lambda f: f.name)
@pytest.mark.parametrize("quote", ['"', "'", ""])
def test_the_function_is_read_back_however_it_is_quoted(visa, dmm, function, quote):
    visa.replies["SENS:FUNC?"] = f"{quote}{function.raw_value}{quote}\n"
    assert dmm.get_function() is function


def test_two_wire_and_four_wire_resistance_are_not_confused(visa, dmm):
    visa.replies["SENS:FUNC?"] = '"RES"'
    assert dmm.get_function() is Function.RESISTANCE
    visa.replies["SENS:FUNC?"] = '"FRES"'
    assert dmm.get_function() is Function.RESISTANCE_4W


# ------------------------------------------------------------ readings
def test_get_reading_parses_the_latest_reading(visa, dmm):
    visa.replies["SENS:DATA?"] = "+1.234560E-03\n"
    assert dmm.get_reading() == pytest.approx(1.23456e-3)
    visa.replies["SENS:DATA?"] = "+9.9E37"
    assert dmm.get_reading() > 1e37


def test_fetch_and_read_return_every_reading(visa, dmm):
    visa.replies["FETC?"] = "+1.0E+00,-2.5E-03,+3.0E+00"
    visa.replies["READ?"] = "+4.0E+00"
    assert dmm.fetch() == [1.0, -2.5e-3, 3.0]
    assert dmm.read() == [4.0]


def test_measure_and_configure_use_the_function(visa, dmm):
    visa.replies["MEAS:RES?"] = "+1.000000E+03"
    assert dmm.measure(Function.RESISTANCE) == pytest.approx(1000)
    dmm.configure(Function.DC_CURRENT)
    assert visa.written[-1] == "CONF:CURR:DC"


def test_buffer_data_and_free(visa, dmm):
    visa.replies["TRAC:DATA?"] = "+1.0E+00,+2.0E+00"
    visa.replies["TRAC:FREE?"] = "+3.0E+03,+4.0E+02"
    assert dmm.get_buffer_data() == [1.0, 2.0]
    assert dmm.get_buffer_free() == [3000, 400]
    visa.replies["TRAC:DATA?"] = ""
    assert dmm.get_buffer_data() == []


# ------------------------------------------------------------ channels
@pytest.mark.parametrize(
    "reply, expected",
    [
        ("(@1:3)", [1, 2, 3]),
        ("(@2,4,6)", [2, 4, 6]),
        ("(@1:3,5)", [1, 2, 3, 5]),
        ("(@4)", [4]),
        ("(@)", []),
        ('"(@1:2)"\n', [1, 2]),
    ],
)
def test_channel_lists_are_read(reply, expected):
    assert parse_channels(reply) == expected


def test_channel_lists_are_formatted():
    assert format_channels([1, 3, 5]) == "(@1,3,5)"
    assert format_channels([]) == "(@)"


def test_channels(visa, dmm):
    dmm.close_channel(3)
    dmm.close_channels([1, 11])
    dmm.open_channels([1])
    dmm.open_all_channels()
    dmm.set_internal_scan_list([1, 2, 3])
    dmm.set_scan_mode(ScanMode.INTERNAL)
    assert visa.written[-6:] == [
        "ROUT:CLOS (@3)",
        "ROUT:MULT:CLOS (@1,11)",
        "ROUT:MULT:OPEN (@1)",
        "ROUT:OPEN:ALL",
        "ROUT:SCAN (@1,2,3)",
        "ROUT:SCAN:LSEL INT",
    ]
    visa.replies["ROUT:SCAN?"] = "(@1:3)"
    visa.replies["ROUT:SCAN:LSEL?"] = "NONE"
    assert dmm.get_internal_scan_list() == [1, 2, 3]
    assert dmm.get_scan_mode() is ScanMode.NONE


# ------------------------------------------------------------ everything else
def test_temperature_and_thermocouple(visa, dmm):
    dmm.set_temperature_unit(TemperatureUnit.KELVIN)
    dmm.set_simulated_junction_temperature(23)
    assert visa.written[-2:] == ["UNIT:TEMP K", "SENS:TEMP:TC:RJUN:SIM 2.300000e+01"]
    visa.replies["UNIT:TEMP?"] = "C"
    assert dmm.get_temperature_unit() is TemperatureUnit.CELSIUS


def test_decibel_units_are_not_confused(visa, dmm):
    for reply, unit in (("V", VoltageUnit.VOLTS), ("DB", VoltageUnit.DECIBELS)):
        visa.replies["UNIT:VOLT:AC?"] = reply
        assert dmm.get_ac_voltage_unit() is unit
    visa.replies["UNIT:VOLT:AC?"] = "DBM"
    assert dmm.get_ac_voltage_unit() is VoltageUnit.DECIBELS_MILLIWATT


def test_math_and_limits(visa, dmm):
    dmm.set_math_format(MathFormat.MX_PLUS_B)
    dmm.set_math_units("OHM")
    dmm.set_limit_upper(2)
    dmm.set_limit_test(State.ON)
    assert visa.written[-4:] == [
        "CALC:FORM MXB",
        "CALC:KMAT:MUN 'OHM'",
        "CALC3:LIM:UPP 2.000000e+00",
        "CALC3:LIM:STAT 1",
    ]
    visa.replies["CALC:KMAT:MUN?"] = '"OHM"'
    assert dmm.get_math_units() == "OHM"
    visa.replies["CALC:FORM?"] = "PERC"
    assert dmm.get_math_format() is MathFormat.PERCENT


def test_the_limit_test_follows_the_manual(visa, dmm):
    visa.replies["CALC3:LIM:FAIL?"] = "1"
    assert dmm.get_limit_test_passed() is True
    visa.replies["CALC3:LIM:FAIL?"] = "0"
    assert dmm.get_limit_test_passed() is False


def test_trigger_model(visa, dmm):
    dmm.set_trigger_count(math.inf)
    dmm.set_trigger_count(10)
    dmm.set_trigger_source(TriggerSource.BUS)
    dmm.set_sample_count(5)
    dmm.set_continuous_initiation(State.OFF)
    dmm.initiate()
    dmm.abort_trigger()
    assert visa.written[-7:] == [
        "TRIG:COUN INF",
        "TRIG:COUN 10",
        "TRIG:SOUR BUS",
        "SAMP:COUN 5",
        "INIT:CONT 0",
        "INIT:IMM",
        "ABOR",
    ]
    visa.replies["TRIG:COUN?"] = "+9.9E+37"
    assert dmm.get_trigger_count() > 1e37


def test_status_and_errors(visa, dmm):
    dmm.set_status_enable(StatusRegister.MEASUREMENT, 512)
    assert visa.written[-1] == "STAT:MEAS:ENAB 512"
    visa.replies["STAT:OPER:EVEN?"] = "+1024"
    assert dmm.get_status_event(StatusRegister.OPERATION) == 1024
    visa.replies["SYST:ERR?"] = '-222,"Parameter data out of range"'
    assert dmm.get_error() == {"code": -222, "message": "Parameter data out of range"}
    visa.replies["STAT:QUE?"] = '0,"No error"'
    assert dmm.get_next_error()["code"] == 0


def test_display(visa, dmm):
    dmm.set_display_text("HELLO")
    assert visa.written[-1] == "DISP:TEXT:DATA 'HELLO'"
    visa.replies["DISP:TEXT:DATA?"] = '"HELLO"'
    assert dmm.get_display_text() == "HELLO"


def test_system(visa, dmm):
    dmm.set_power_on_setup(PowerOnSetup.SAVED)
    dmm.press_key(Key.DC_VOLTAGE)
    dmm.set_autozero(State.OFF)
    assert visa.written[-3:] == ["SYST:POS SAV0", "SYST:KEY 2", "SYST:AZER:STAT 0"]
    visa.replies["SYST:KEY?"] = "33"
    with pytest.raises(ValueError):  # not a code that exists on the 2000
        dmm.get_last_key()
    visa.replies["SYST:KEY?"] = "16"
    assert dmm.get_last_key() is Key.TEMPERATURE
    visa.replies["SYST:FRSW?"] = "1"
    assert dmm.get_front_inputs_selected() is True


def test_preset_waits_for_completion(visa, dmm):
    dmm.preset()
    assert visa.written[-1] == "SYST:PRES"
    assert visa.queried[-1] == "*OPC?"


def test_common_commands(visa, dmm):
    dmm.save_setup()
    dmm.recall_setup()
    dmm.wait_to_continue()
    visa.replies["*OPT?"] = "200X-SCAN"
    assert visa.written[-3:] == ["*SAV 0", "*RCL 0", "*WAI"]
    assert dmm.get_options() == "200X-SCAN"
