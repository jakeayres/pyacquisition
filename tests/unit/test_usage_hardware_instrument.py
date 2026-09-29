"""Usage › Write a hardware instrument (docs/usage/hardware_instrument.md): each
version of keithley_2400.py and lab.py runs over `mock`, sends the messages the
page says, and parses the replies as a 2400 gives them."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pyacquisition.core import config_check

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "hardware_instrument"
GETTING_STARTED = ROOT / "examples" / "getting_started"
READING = "+1.000000E+00,+1.021450E-06,+9.910000E+37,+2.515590E+03,+2.150800E+04"


def load(name: str, monkeypatch=None):
    """An example file as a module of its own name. lab.py's `import keithley_2400`
    is the finished driver's."""
    if monkeypatch is not None:
        monkeypatch.setitem(sys.modules, "keithley_2400", load("keithley_2400_5"))
    spec = importlib.util.spec_from_file_location(f"hardware_instrument_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def smu(version: int, **responses):
    return load(f"keithley_2400_{version}").Keithley_2400(
        "smu", "GPIB0::24::INSTR", adapter="mock", responses=responses or None
    )


def test_it_starts_from_the_end_of_getting_started():
    assert text(HERE / "lab_1.py") == text(GETTING_STARTED / "lab_6.py")


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_each_version_is_a_keithley_2400_that_identifies_itself(version):
    driver = smu(version)
    assert driver.name == "Keithley 2400"
    assert driver.identify() == "MOCK,GPIB0::24::INSTR,0,0"  # *IDN?, stripped
    assert driver._visa_resource.written[-1] == "*IDN?"


def test_what_each_version_offers_in_the_instruments_tab():
    offered = {v: (sorted(d.queries), sorted(d.commands)) for v in range(1, 6) for d in [smu(v)]}
    assert offered == {
        1: (["identify"], []),
        2: (["get_current", "identify"], []),
        3: (["get_current", "get_voltage", "identify"], ["set_voltage"]),
        4: (["get_current", "get_voltage", "identify"], ["set_output", "set_voltage"]),
        5: (["get_current", "get_voltage", "identify"], ["set_output", "set_terminals", "set_voltage"]),
    }


def test_the_current_is_the_second_of_the_five_numbers_read_answers():
    driver = smu(2, **{":READ?": READING})
    assert driver.get_current() == 1.02145e-06
    assert driver._visa_resource.written == [":READ?"]


def test_with_no_reply_to_read_the_query_has_no_second_number():
    with pytest.raises(IndexError, match="list index out of range"):
        smu(2).get_current()


def test_the_voltage_is_sent_and_the_mock_gives_it_back():
    driver = smu(3)
    driver.set_voltage(1.5)
    assert driver._visa_resource.written == [":SOUR:VOLT 1.5"]
    assert driver.get_voltage() == 1.5
    assert driver._visa_resource.written[-1] == ":SOUR:VOLT?"


def test_the_output_is_turned_on_and_off():
    driver = smu(4)
    driver.set_output(True)
    driver.set_output(False)
    assert driver._visa_resource.written == [":OUTP ON", ":OUTP OFF"]


def test_the_terminals_are_sent_by_their_codes_and_shown_by_their_labels():
    module = load("keithley_2400_5")
    assert [(t.name, t.raw_value, t.label) for t in module.Terminals] == [
        ("FRONT", "FRON", "Front"), ("REAR", "REAR", "Rear")
    ]
    driver = module.Keithley_2400("smu", "GPIB0::24::INSTR", adapter="mock")
    driver.set_terminals(module.Terminals.REAR)
    assert driver._visa_resource.written == [":ROUT:TERM REAR"]


# -------------------------------------------------------------- lab.py
@pytest.fixture
def lab(tmp_path, monkeypatch):
    shutil.copy(GETTING_STARTED / "rig.toml", tmp_path / "rig.toml")
    monkeypatch.chdir(tmp_path)
    experiment = load("lab_2", monkeypatch).Lab.from_config("rig.toml", root_path=str(tmp_path), gui=False)
    experiment.setup()
    return experiment


def test_the_lab_s_reading_is_a_2400_s(lab):
    assert load("lab_2").READING == READING


def test_setup_makes_the_2400_on_mock_turns_it_on_at_0_v_and_records_the_current(lab):
    driver = lab.instruments["smu"]
    assert driver.name == "Keithley 2400"
    assert driver._visa_resource.resource_name == "GPIB0::24::INSTR"
    assert driver._visa_resource.written == [":SOUR:VOLT 0.0", ":OUTP ON"]
    current = lab.measurements["current"]
    assert current.unit == "A"
    assert current.run() == 1.02145e-06


def test_teardown_turns_the_output_off(lab, capsys):
    lab.teardown()
    assert lab.instruments["smu"]._visa_resource.written[-1] == ":OUTP OFF"
    assert "The 2400's output is off." in capsys.readouterr().out


def test_the_interface_offers_a_checkbox_and_the_terminals_labels(lab):
    api = lab._api_server
    lab._rack._register_endpoints(api)
    client = TestClient(api.app)
    schema = client.get("/openapi.json").json()
    (on,) = schema["paths"]["/smu/set_output"]["get"]["parameters"]
    assert on["schema"]["type"] == "boolean"
    assert schema["components"]["schemas"]["Terminals"]["enum"] == ["Front", "Rear"]
    client.get("/smu/set_voltage", params={"volts": 1.5})
    assert client.get("/smu/get_voltage").json()["data"] == 1.5


def test_a_driver_of_your_own_cant_be_named_in_a_config_file(tmp_path):
    rig = tmp_path / "rig.toml"
    rig.write_text('[instruments.smu]\ninstrument = "Keithley_2400"\nadapter = "mock"\n'
                   'resource = "GPIB0::24::INSTR"\n', encoding="utf-8")
    with pytest.raises(config_check.ConfigError) as error:
        config_check.load(str(rig))
    assert "Instrument 'smu': there is no driver called 'Keithley_2400' (did you mean 'Keithley_2000'?)." in str(error.value)


def test_a_driver_given_no_address_says_so():
    driver = load("keithley_2400_5").Keithley_2400
    with pytest.raises(TypeError, match=r"missing 1 required positional argument: 'resource'"):
        driver("smu", adapter="mock")
