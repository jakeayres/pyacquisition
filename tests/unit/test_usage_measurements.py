"""Usage › Tune your measurements (docs/usage/measurements.md): each version of
sample.py makes its experiment on the simulated cryostat, and its measurements
have the units, arguments and pace the page says."""

import importlib.util
import sys
from pathlib import Path

import pytest

from pyacquisition import Measurement
from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel, OutputChannel

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "measurements"
SIMULATED = ROOT / "examples" / "simulated_rig"


@pytest.fixture
def simulated(monkeypatch):
    monkeypatch.syspath_prepend(str(SIMULATED))
    sys.modules.pop("simulated", None)
    import simulated

    return simulated


def sample(version: int, tmp_path, simulated):
    spec = importlib.util.spec_from_file_location(f"measurements_sample_{version}", HERE / f"sample_{version}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    experiment = module.Sample(root_path=str(tmp_path), gui=False)
    experiment.setup()
    return experiment


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_each_version_measures_the_time_and_the_lock_in(version, tmp_path, simulated):
    experiment = sample(version, tmp_path, simulated)
    assert set(experiment.instruments) == {"clock", "cryostat", "lockin"}
    assert list(experiment.measurements)[:3] == ["time", "x", "y"]
    assert experiment.measurements["x"].run() == pytest.approx(0.0, abs=1e-4)  # 20 K: above the transition


def test_the_units_are_seconds_and_volts(tmp_path, simulated):
    measurements = sample(2, tmp_path, simulated).measurements
    assert [(m.unit) for m in measurements.values()] == ["s", "V", "V"]


def test_the_temperature_is_read_from_input_a_in_kelvin(tmp_path, simulated):
    temperature = sample(3, tmp_path, simulated).measurements["T"]
    assert temperature.unit == "K"
    assert temperature._kwargs == {"input_channel": InputChannel.INPUT_A}
    assert temperature.run() == pytest.approx(20.0, abs=0.05)


@pytest.mark.parametrize("text", ["INPUT_A", "Input A", "input a"])
def test_the_choice_can_be_given_as_text(text, simulated):
    cryostat = simulated.SimulatedCryostat("cryostat")
    measurement = Measurement("T", cryostat.get_temperature, input_channel=text)
    assert measurement._kwargs == {"input_channel": InputChannel.INPUT_A}


def test_text_that_names_no_member_lists_those_that_exist(simulated):
    cryostat = simulated.SimulatedCryostat("cryostat")
    with pytest.raises(ValueError, match=r"^`input_channel`: 'INPUT_Z' is not one of INPUT_A, INPUT_B, INPUT_C, INPUT_D$"):
        Measurement("T", cryostat.get_temperature, input_channel="INPUT_Z")


def test_an_argument_the_query_doesnt_take_is_named(simulated):
    cryostat = simulated.SimulatedCryostat("cryostat")
    with pytest.raises(ValueError, match=r"^Invalid keyword argument 'channel' for function 'get_temperature'\.$"):
        Measurement("T", cryostat.get_temperature, channel=InputChannel.INPUT_A)


def test_the_setpoint_is_read_on_every_tenth_cycle_and_repeated_between(tmp_path, simulated, monkeypatch):
    reads = []
    original = simulated.SimulatedCryostat.get_setpoint

    def counted(self, output_channel):
        reads.append(output_channel)
        return original(self, output_channel)

    monkeypatch.setattr(simulated.SimulatedCryostat, "get_setpoint", counted)
    experiment = sample(4, tmp_path, simulated)
    setpoint = experiment.measurements["setpoint"]
    assert setpoint.unit == "K"
    values = []
    for cycle in range(21):
        if cycle == 3:
            experiment.instruments["cryostat"].set_setpoint(OutputChannel.OUTPUT_1, 10.0)
        values.append(setpoint.run())
    assert len(reads) == 3  # cycles 1, 11 and 21
    assert values[:10] == [20.0] * 10  # the change on cycle 4 isn't read until cycle 11
    assert values[10:20] == [10.0] * 10


def test_a_failed_measurement_repeats_its_last_value_or_has_none():
    answers = iter([1.5, TimeoutError("no answer")])

    def query():
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    measurement = Measurement("x", query)
    assert measurement.run() == 1.5
    assert measurement.run() == 1.5  # failed, so the last value again

    def never():
        raise TimeoutError("no answer")

    assert Measurement("y", never).run() is None  # an empty field in the file


def test_a_measurement_given_the_answer_instead_of_the_query_is_refused(simulated):
    lockin = simulated.SimulatedLockin("lockin", simulated.SimulatedCryostat("cryostat"))
    with pytest.raises(TypeError, match="is not a callable object"):
        Measurement("x", lockin.get_x())
