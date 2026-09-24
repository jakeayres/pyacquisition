"""Hardware instruments open their own connection from an address."""

from unittest.mock import MagicMock

import pytest

from pyacquisition import Experiment
from pyacquisition.core.adapters.mock import MockResource
from pyacquisition.core.instrument import SoftwareInstrument
from pyacquisition.instruments import Clock, Keithley_6221


# -------------------------------------------------------------- opening
def test_an_address_is_opened_with_the_named_adapter():
    k = Keithley_6221(
        "k",
        "GPIB0::12::INSTR",
        adapter="mock",
        responses={"*IDN?": "KEITHLEY,6221"},
    )
    assert k.identify() == "KEITHLEY,6221"
    assert k.metadata["address"] == "GPIB0::12::INSTR"


def test_pyvisa_is_the_default_adapter(monkeypatch):
    manager = MagicMock()
    monkeypatch.setattr("pyacquisition.core.adapters.pyvisa.ResourceManager", manager)

    k = Keithley_6221("k", "GPIB0::12::INSTR", timeout=1000)

    manager.return_value.open_resource.assert_called_once_with(
        "GPIB0::12::INSTR", timeout=1000
    )
    assert k._visa_resource is manager.return_value.open_resource.return_value


def test_the_timeout_defaults_to_five_seconds():
    k = Keithley_6221("k", "GPIB0::12::INSTR", adapter="mock")
    assert k._visa_resource.timeout == 5000


def test_a_resource_that_is_already_open_still_works():
    resource = MockResource("GPIB0::12::INSTR")
    k = Keithley_6221("k", resource)
    assert k._visa_resource is resource


@pytest.mark.parametrize("options", [{"adapter": "mock"}, {"timeout": 1000}])
def test_options_for_opening_are_refused_with_an_open_resource(options):
    with pytest.raises(TypeError, match="already open"):
        Keithley_6221("k", MockResource("r"), **options)


def test_an_unknown_adapter_is_a_value_error():
    with pytest.raises(ValueError, match="nope"):
        Keithley_6221("k", "GPIB0::12::INSTR", adapter="nope")


def test_an_address_that_cannot_be_opened_says_so(monkeypatch):
    manager = MagicMock()
    manager.return_value.open_resource.side_effect = OSError("no such device")
    manager.return_value.list_resources.return_value = ("GPIB0::7::INSTR",)
    monkeypatch.setattr("pyacquisition.core.adapters.pyvisa.ResourceManager", manager)

    with pytest.raises(ConnectionError) as error:
        Keithley_6221("k", "GPIB0::12::INSTR")

    message = str(error.value)
    assert "GPIB0::12::INSTR" in message
    assert "no such device" in message
    assert "Available resources: GPIB0::7::INSTR." in message


def test_the_error_survives_an_adapter_that_cannot_list(monkeypatch):
    manager = MagicMock()
    manager.return_value.open_resource.side_effect = OSError("no such device")
    manager.return_value.list_resources.side_effect = RuntimeError("no VISA library")
    monkeypatch.setattr("pyacquisition.core.adapters.pyvisa.ResourceManager", manager)

    with pytest.raises(ConnectionError, match="no such device"):
        Keithley_6221("k", "GPIB0::12::INSTR")


# -------------------------------------------------------------- closing
def test_an_instrument_closes_the_resource_it_opened():
    k = Keithley_6221("k", "GPIB0::12::INSTR", adapter="mock")
    resource = k._visa_resource
    k.close()
    assert not resource.opened


def test_an_instrument_leaves_a_resource_it_was_given():
    resource = MockResource("GPIB0::12::INSTR")
    Keithley_6221("k", resource).close()
    assert resource.opened


def test_closing_twice_is_harmless():
    resource = MagicMock()
    resource.close = MagicMock()
    k = Keithley_6221("k", "GPIB0::12::INSTR", adapter="mock")
    k._visa_resource = resource
    k.close()
    k.close()
    resource.close.assert_called_once()


def test_a_software_instrument_can_be_closed_too():
    Clock("clock").close()


# -------------------------------------------------------------- the experiment
@pytest.fixture
def experiment(tmp_path):
    return Experiment(root_path=str(tmp_path), gui=False)


def test_the_experiment_closes_what_its_instruments_opened(experiment):
    opened = Keithley_6221("opened", "GPIB0::12::INSTR", adapter="mock")
    given = Keithley_6221("given", MockResource("GPIB0::7::INSTR"))
    for instrument in (opened, given, Clock("clock")):
        experiment.add_instrument(instrument)

    experiment._close_instruments()

    assert not opened._visa_resource.opened
    assert given._visa_resource.opened


def test_one_instrument_failing_to_close_does_not_stop_the_rest(experiment):
    class Stubborn(SoftwareInstrument):
        def close(self):
            raise OSError("stuck")

    later = Keithley_6221("later", "GPIB0::12::INSTR", adapter="mock")
    experiment.add_instrument(Stubborn("stubborn"))
    experiment.add_instrument(later)

    experiment._close_instruments()

    assert not later._visa_resource.opened


# -------------------------------------------------------------- from a config
def test_a_config_instrument_that_cannot_be_reached_is_skipped(experiment):
    config = {
        "instruments": {
            "here": {
                "instrument": "Keithley_6221",
                "adapter": "mock",
                "resource": "GPIB0::12::INSTR",
            },
            "broken": {
                "instrument": "Keithley_6221",
                "adapter": "prologix",
                "resource": "not an address",
            },
            "no_address": {"instrument": "Keithley_6221", "adapter": "mock"},
        }
    }

    Experiment._configure_instruments(experiment, config)

    assert set(experiment.instruments) == {"here"}


def test_a_config_timeout_replaces_the_default(experiment):
    config = {
        "instruments": {
            "k": {
                "instrument": "Keithley_6221",
                "adapter": "mock",
                "resource": "GPIB0::12::INSTR",
                "args": {"timeout": 1234},
            }
        }
    }

    Experiment._configure_instruments(experiment, config)

    assert experiment.instruments["k"]._visa_resource.timeout == 1234
