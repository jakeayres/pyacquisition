"""Usage › Write a software instrument (docs/usage/software_instrument.md): each
version of thermometer.py and lab.py runs, and does what the page says."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "software_instrument"
GETTING_STARTED = ROOT / "examples" / "getting_started"


def load(name: str, monkeypatch=None):
    """An example file as a module of its own name, so that it can't be mistaken for
    Getting Started's lab_1.py and the rest. lab.py's `import thermometer` is the
    finished driver's."""
    if monkeypatch is not None:
        monkeypatch.setitem(sys.modules, "thermometer", load("thermometer_5"))
    spec = importlib.util.spec_from_file_location(f"software_instrument_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_it_starts_from_the_end_of_getting_started():
    assert text(HERE / "lab_1.py") == text(GETTING_STARTED / "lab_6.py")


# -------------------------------------------------------------- thermometer.py
@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_each_version_makes_a_thermometer_called_thermometer(version):
    thermometer = load(f"thermometer_{version}").Thermometer("thermometer")
    assert thermometer.name == "Thermometer"
    assert thermometer.identify() == "Thermometer"  # under Other, it answers its name


def test_what_each_version_offers_in_the_instruments_tab():
    offered = {v: (sorted(t.queries), sorted(t.commands)) for v in range(1, 6)
               for t in [load(f"thermometer_{v}").Thermometer("t")]}
    assert offered == {
        1: ([], []),
        2: (["get_temperature"], []),
        3: (["get_temperature"], ["set_setpoint"]),
        4: (["get_temperature"], ["set_setpoint"]),
        5: (["get_temperature"], ["set_setpoint"]),
    }


def test_the_temperature_starts_at_300_k():
    assert load("thermometer_2").Thermometer("t").get_temperature() == 300.0


def test_each_reading_moves_the_temperature_5_percent_towards_the_setpoint():
    thermometer = load("thermometer_3").Thermometer("t")
    thermometer.set_setpoint(100.0)
    assert thermometer.get_temperature() == pytest.approx(300 - 0.05 * 200)
    for _ in range(45):  # nine seconds, at Getting Started's 0.2 s: most of the way there
        kelvin = thermometer.get_temperature()
    assert 100 < kelvin < 100 + 0.12 * 200


def test_the_sensors_are_a_code_and_a_label():
    sensor = load("thermometer_4").Sensor
    assert [(s.name, s.raw_value, s.label) for s in sensor] == [("SAMPLE", "A", "Sample"), ("STAGE", "B", "Stage")]


def test_the_stage_reads_the_setpoint_and_the_sample_follows():
    module = load("thermometer_5")
    thermometer = module.Thermometer("t")
    thermometer.set_setpoint(150.0)
    assert thermometer.get_temperature(module.Sensor.STAGE) == 150.0
    assert thermometer.get_temperature() == pytest.approx(300 - 0.05 * 150)  # the sample, by default


# -------------------------------------------------------------- lab.py
@pytest.fixture
def lab(tmp_path, monkeypatch):
    """The finished lab.py, made from Getting Started's rig, as it would run."""
    shutil.copy(GETTING_STARTED / "rig.toml", tmp_path / "rig.toml")
    monkeypatch.chdir(tmp_path)
    experiment = load("lab_2", monkeypatch).Lab.from_config("rig.toml", root_path=str(tmp_path), gui=False)
    experiment.setup()
    return experiment


def test_the_lab_has_the_thermometer_and_records_both_sensors(lab):
    assert lab.instruments["thermometer"].name == "Thermometer"
    assert {"T_sample", "T_stage"} <= set(lab.measurements)
    assert lab.measurements["T_sample"].unit == lab.measurements["T_stage"].unit == "K"
    lab.instruments["thermometer"].set_setpoint(150.0)
    assert lab.measurements["T_stage"].run() == 150.0
    assert lab.measurements["T_sample"].run() == pytest.approx(300 - 0.05 * 150)


def test_the_interface_describes_each_method_with_its_docstring_and_offers_the_sensors(lab):
    api = lab._api_server
    lab._rack._register_endpoints(api)  # the instruments' endpoints, as a run registers them
    schema = TestClient(api.app).get("/openapi.json").json()
    query = schema["paths"]["/thermometer/get_temperature"]["get"]
    command = schema["paths"]["/thermometer/set_setpoint"]["get"]
    assert query["description"] == "The temperature at a sensor, in kelvin."
    assert command["description"] == "Sets the temperature to go to, in kelvin."
    (sensor,) = query["parameters"]
    assert sensor["schema"]["default"] == "Sample"
    assert schema["components"]["schemas"]["Sensor"]["enum"] == ["Sample", "Stage"]
    (kelvin,) = command["parameters"]
    assert kelvin["required"] and kelvin["schema"]["type"] == "number"


def test_a_setpoint_that_isnt_a_number_is_refused(lab):
    api = lab._api_server
    lab._rack._register_endpoints(api)
    answer = TestClient(api.app).get("/thermometer/set_setpoint", params={"kelvin": "abc"})
    assert answer.status_code == 422
    assert "Input should be a valid number" in answer.text
