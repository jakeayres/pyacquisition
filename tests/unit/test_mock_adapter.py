import pytest
from pyvisa.errors import InvalidSession, VisaIOError

from pyacquisition import Experiment
from pyacquisition.core.adapters import get_adapter
from pyacquisition.core.adapters.mock import MockResource, MockResourceManager
from pyacquisition.instruments import Keithley_6221, Lakeshore_350
from pyacquisition.instruments.keithley.keithley_6221 import State, WaveFunction
from pyacquisition.instruments.lakeshore.lakeshore_350 import OutputChannel


@pytest.fixture
def resource():
    return MockResource("mock::1")


# -------------------------------------------------------------- pyvisa contract
def test_query_returns_a_string_and_write_returns_a_byte_count(resource):
    assert resource.write("SOUR:CURR 1e-3") == len("SOUR:CURR 1e-3")
    assert resource.query("SOUR:CURR?") == "1e-3"


def test_write_counts_the_termination(resource):
    resource.write_termination = "\n"
    assert resource.write("*CLS") == 5


def test_read_without_a_pending_query_times_out(resource):
    resource.write("SOUR:CURR 1e-3")  # a setter leaves nothing to read
    with pytest.raises(VisaIOError):
        resource.read()


def test_replies_are_read_in_the_order_asked(resource):
    resource.write("*IDN?")
    resource.write("*OPC?")
    assert resource.read() == "MOCK,mock::1,0,0"
    assert resource.read() == "1"


def test_clear_discards_unread_replies(resource):
    resource.write("*OPC?")
    resource.clear()
    with pytest.raises(VisaIOError):
        resource.read()


def test_closed_resource_refuses_io(resource):
    resource.close()
    with pytest.raises(InvalidSession):
        resource.write("*CLS")
    with pytest.raises(InvalidSession):
        resource.read()


def test_context_manager_closes(resource):
    with resource as r:
        assert r.opened
    assert not resource.opened


def test_attributes_are_set_like_pyvisa_does():
    r = MockResource("x", timeout=5000, read_termination="\r", query_delay=0.1)
    assert (r.timeout, r.read_termination, r.query_delay) == (5000, "\r", 0.1)


def test_writes_are_recorded(resource):
    resource.write("*CLS")
    resource.query("*IDN?")
    assert resource.written == ["*CLS", "*IDN?"]


# -------------------------------------------------------------- replies
def test_a_getter_returns_what_its_setter_wrote(resource):
    resource.write("SETP 1,2.50")
    assert resource.query("SETP? 1") == "2.50"


def test_channels_are_remembered_separately(resource):
    resource.write("SETP 1,2.50")
    resource.write("SETP 2,9.00")
    assert resource.query("SETP? 1") == "2.50"
    assert resource.query("SETP? 2") == "9.00"


def test_multi_value_setter_returns_the_remainder_after_its_channel(resource):
    resource.write("RAMP 1,1,0.500")
    assert resource.query("RAMP? 1") == "1,0.500"


def test_headers_and_case_are_not_significant(resource):
    resource.write("sour:curr   1e-3")
    assert resource.query("SOUR:CURR?") == "1e-3"


def test_unset_queries_get_the_default(resource):
    assert resource.query("KRDG? A") == "0"
    assert MockResource("x", default_reply="1.5").query("KRDG? A") == "1.5"


def test_builtin_replies(resource):
    assert resource.query("*IDN?") == "MOCK,mock::1,0,0"
    assert resource.query("*OPC?") == "1"
    assert resource.query("SYST:ERR?") == '0,"No error"'


def test_reset_forgets_what_was_written(resource):
    resource.write("SOUR:CURR 1e-3")
    resource.write("*RST")
    assert resource.query("SOUR:CURR?") == "0"


def test_configured_reply_beats_remembered_state():
    r = MockResource("x", responses={"SOUR:CURR?": 5e-3})
    r.write("SOUR:CURR 1e-3")
    assert r.query("SOUR:CURR?") == "0.005"


def test_a_full_query_beats_its_header():
    r = MockResource("x", responses={"KRDG?": "1", "KRDG? B": "2"})
    assert r.query("KRDG? A") == "1"
    assert r.query("krdg?  b") == "2"


def test_a_list_of_replies_is_stepped_through_and_holds_the_last():
    r = MockResource("x", responses={"KRDG? A": [4.0, 4.1, 4.2]})
    assert [r.query("KRDG? A") for _ in range(5)] == ["4.0", "4.1", "4.2", "4.2", "4.2"]


def test_a_callable_reply_gets_the_query():
    r = MockResource("x", responses={"KRDG?": lambda q: f"echo {q}"})
    assert r.query("KRDG? A") == "echo KRDG? A"


def test_respond_can_change_a_reply_later(resource):
    resource.respond("*IDN?", "ACME,1,2,3")
    assert resource.query("*IDN?") == "ACME,1,2,3"


# -------------------------------------------------------------- manager
def test_the_manager_lists_any_resource_as_available():
    manager = MockResourceManager()
    assert "GPIB0::7::INSTR" in manager.list_resources()
    assert "anything at all" in manager.list_resources()


def test_the_manager_opens_with_experiment_style_arguments():
    manager = MockResourceManager()
    resource = manager.open_resource("r", timeout=5000, responses={"*IDN?": "X"})
    assert resource.timeout == 5000
    assert resource.query("*IDN?") == "X"
    assert list(manager.list_resources()) == ["r"]


def test_closing_the_manager_closes_its_resources():
    manager = MockResourceManager()
    resource = manager.open_resource("r")
    manager.close()
    assert not resource.opened
    assert list(manager.list_resources()) == []


def test_the_adapter_is_registered_by_name():
    assert isinstance(get_adapter("mock"), MockResourceManager)


def test_experiment_opens_a_mock_resource_that_was_never_listed():
    resource = Experiment._open_resource(
        get_adapter("mock"), "GPIB0::7::INSTR", timeout=5000
    )
    assert resource is not None
    assert resource.query("*IDN?") == "MOCK,GPIB0::7::INSTR,0,0"


# -------------------------------------------------------------- with instruments
def test_a_hardware_instrument_round_trips_against_the_mock():
    k = Keithley_6221("k", MockResource("mock"))

    k.set_current(1.5e-6)
    k.set_output_state(State.ON)
    k.set_wave_function(WaveFunction.SQUARE)

    assert k.get_current() == pytest.approx(1.5e-6)
    assert k.get_output_state() is State.ON
    assert k.get_wave_function() is WaveFunction.SQUARE


def test_lakeshore_channel_getters_use_the_channel():
    lake = Lakeshore_350("lake", MockResource("mock"))
    lake.set_setpoint(OutputChannel.OUTPUT_1, 4.2)
    lake.set_setpoint(OutputChannel.OUTPUT_2, 77.0)
    assert lake.get_setpoint(OutputChannel.OUTPUT_1) == pytest.approx(4.2)
    assert lake.get_setpoint(OutputChannel.OUTPUT_2) == pytest.approx(77.0)


def test_instruments_are_configured_from_a_config_with_the_mock_adapter(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    config = {
        "instruments": {
            "current": {
                "instrument": "Keithley_6221",
                "adapter": "mock",
                "resource": "GPIB0::12::INSTR",
                "args": {
                    "responses": {"*IDN?": "KEITHLEY INSTRUMENTS INC.,MODEL 6221,1,D03"}
                },
            },
            "temperature": {
                "instrument": "Lakeshore_350",
                "adapter": "mock",
                "resource": "GPIB0::15::INSTR",
            },
        }
    }

    Experiment._configure_instruments(experiment, config)

    assert set(experiment.instruments) == {"current", "temperature"}
    assert experiment.instruments["current"].identify().startswith("KEITHLEY")
    assert experiment.instruments["temperature"].identify() == (
        "MOCK,GPIB0::15::INSTR,0,0"
    )


def test_instrument_metadata_reports_the_resource_name():
    k = Keithley_6221("k", MockResource("GPIB0::12::INSTR"))
    assert k.metadata == {
        "id": "k",
        "class": "Keithley_6221",
        "address": "GPIB0::12::INSTR",
    }
