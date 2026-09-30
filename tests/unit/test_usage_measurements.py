"""Usage › Tune your measurements (docs/usage/measurements.md): each version of
sample.py makes its experiment with the real SR_830 and Lakeshore_350 at their
addresses (over the fake connection of fake_rig.py), and its measurements have
the units, arguments and pace the page says."""

import importlib.util
from pathlib import Path

import pytest
from fake_rig import LAKESHORE, LOCKIN, REPLIES, open_fakes

from pyacquisition import Measurement
from pyacquisition.instruments import Lakeshore_350

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "measurements"
InputChannel, OutputChannel = Lakeshore_350.InputChannel, Lakeshore_350.OutputChannel


@pytest.fixture
def rig(monkeypatch):
    return open_fakes(monkeypatch, REPLIES)


def sample(version: int, tmp_path):
    spec = importlib.util.spec_from_file_location(f"measurements_sample_{version}", HERE / f"sample_{version}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    experiment = module.Sample(root_path=str(tmp_path), gui=False)
    experiment.setup()
    return experiment


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_each_version_opens_the_instruments_and_measures_the_lock_in(version, tmp_path, rig):
    experiment = sample(version, tmp_path)
    assert set(rig) == {LOCKIN, LAKESHORE}
    assert set(experiment.instruments) == {"clock", "cryostat", "lockin"}
    assert list(experiment.measurements)[:3] == ["time", "x", "y"]
    assert experiment.measurements["x"].run() == pytest.approx(1.2e-4)  # OUTP? 1


def test_the_units_are_seconds_and_volts(tmp_path, rig):
    measurements = sample(2, tmp_path).measurements
    assert [(m.unit) for m in measurements.values()] == ["s", "V", "V"]


def test_the_temperature_is_read_from_input_a_in_kelvin(tmp_path, rig):
    temperature = sample(3, tmp_path).measurements["T"]
    assert temperature.unit == "K"
    assert temperature._kwargs == {"input_channel": InputChannel.INPUT_A}
    assert temperature.run() == 20.0  # KRDG? A


@pytest.mark.parametrize("text", ["INPUT_A", "Input A", "input a"])
def test_the_choice_can_be_given_as_text(text, rig):
    cryostat = Lakeshore_350("cryostat", LAKESHORE)
    measurement = Measurement("T", cryostat.get_temperature, input_channel=text)
    assert measurement._kwargs == {"input_channel": InputChannel.INPUT_A}


def test_text_that_names_no_member_lists_those_that_exist(rig):
    cryostat = Lakeshore_350("cryostat", LAKESHORE)
    with pytest.raises(ValueError, match=r"^`input_channel`: 'INPUT_Z' is not one of INPUT_A, INPUT_B, INPUT_C, INPUT_D$"):
        Measurement("T", cryostat.get_temperature, input_channel="INPUT_Z")


def test_an_argument_the_query_doesnt_take_is_named(rig):
    cryostat = Lakeshore_350("cryostat", LAKESHORE)
    with pytest.raises(ValueError, match=r"^Invalid keyword argument 'channel' for function 'get_temperature'\.$"):
        Measurement("T", cryostat.get_temperature, channel=InputChannel.INPUT_A)


def test_the_setpoint_is_read_on_every_tenth_cycle_and_repeated_between(tmp_path, rig):
    experiment = sample(4, tmp_path)
    lakeshore = rig[LAKESHORE]
    setpoint = experiment.measurements["setpoint"]
    assert setpoint.unit == "K"
    values = []
    for cycle in range(21):
        if cycle == 3:
            experiment.instruments["cryostat"].set_setpoint(OutputChannel.OUTPUT_1, 10.0)
        values.append(setpoint.run())
    queries = [m for m in lakeshore.written if m.startswith("SETP ")]
    assert queries == ["SETP 1,10"]
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


def test_a_measurement_given_the_answer_instead_of_the_query_is_refused(rig):
    from pyacquisition.instruments import SR_830

    lockin = SR_830("lockin", LOCKIN)
    with pytest.raises(TypeError, match="is not a callable object"):
        Measurement("x", lockin.get_x())
