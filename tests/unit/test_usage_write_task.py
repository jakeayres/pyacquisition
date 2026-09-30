"""Usage › Write a task (docs/usage/write_task.md): each version of sample.py makes
its experiment, and SetTemperature goes to the temperature, shows its progress,
refuses one out of range, and holds the cryostat when paused or ended, as the page
says. It runs on a fast simulated cryostat, so the tests take a second."""

import asyncio
import dataclasses
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel, OutputChannel

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "write_task"
SIMULATED = ROOT / "examples" / "simulated_rig"
FORM_TYPES = (int, float, str, bool)


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.fixture
def simulated(monkeypatch):
    monkeypatch.syspath_prepend(str(SIMULATED))
    sys.modules.pop("simulated", None)
    import simulated

    return simulated


def module(version: int):
    spec = importlib.util.spec_from_file_location(f"write_task_sample_{version}", HERE / f"sample_{version}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def a_lab(simulated, kelvin=20.0):
    """A stand-in experiment whose cryostat follows its setpoint in 50 ms."""
    return SimpleNamespace(instruments={"cryostat": simulated.SimulatedCryostat("cryostat", temperature=kelvin, lag=0.05)})


def test_it_starts_from_tune_your_measurements_third_step():
    assert text(HERE / "sample_1.py") == text(ROOT / "examples" / "usage" / "measurements" / "sample_3.py")


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5, 6, 7])
def test_each_version_sets_up(version, tmp_path, simulated):
    experiment = module(version).Sample(root_path=str(tmp_path), gui=False)
    experiment.setup()
    assert list(experiment.measurements) == ["time", "x", "y", "T"]


@pytest.mark.parametrize("version", [2, 3, 4, 5, 6, 7])
def test_its_inputs_can_be_shown_in_a_form(version, simulated):
    fields = dataclasses.fields(module(version).SetTemperature)
    assert all(field.type in FORM_TYPES for field in fields)
    assert [field.name for field in fields] == (["kelvin", "rate"] if version == 2 else ["kelvin", "rate", "tolerance"])


@pytest.mark.asyncio
async def test_the_first_version_ramps_to_the_setpoint(simulated):
    lab = a_lab(simulated)
    task = module(2).SetTemperature(10.0)
    await task.start(lab)
    assert task.outcome == "completed"
    assert lab.instruments["cryostat"]._target == 10.0 and lab.instruments["cryostat"]._ramp_rate == 30.0


@pytest.mark.asyncio
async def test_it_waits_until_the_sample_is_within_the_tolerance(simulated):
    lab = a_lab(simulated)
    task = module(3).SetTemperature(10.0, rate=6000.0)
    await asyncio.wait_for(task.start(lab), 30)
    assert task.outcome == "completed"
    assert abs(lab.instruments["cryostat"].get_temperature(InputChannel.INPUT_A) - 10.0) < 0.06


@pytest.mark.asyncio
async def test_it_shows_its_progress_and_what_it_is_doing(simulated):
    lab = a_lab(simulated)
    task = module(4).SetTemperature(10.0, rate=6000.0)
    assert task.description == "Go to 10.0 K"
    await asyncio.wait_for(task.start(lab), 30)
    assert task.progress["fraction"] == pytest.approx(1.0, abs=0.01)
    assert task.progress["note"].endswith(" K")


def test_it_refuses_a_temperature_out_of_range_as_it_is_made(simulated):
    task = module(5).SetTemperature
    with pytest.raises(ValueError, match=r"^500\.0 K is out of range: 1\.5 to 300 K\.$"):
        task(500.0)
    assert task(300.0).kelvin == 300.0


def test_the_form_refuses_it_with_that_message(tmp_path, simulated):
    experiment = module(7).Sample(root_path=str(tmp_path), gui=False)
    experiment.setup()
    client = TestClient(experiment._api_server.app)
    refused = client.get("/tasks/set_temperature", params={"kelvin": 500})
    assert refused.status_code == 422
    assert refused.json() == {"detail": "500.0 K is out of range: 1.5 to 300 K."}
    assert client.get("/tasks/set_temperature", params={"kelvin": 10}).status_code == 200


@pytest.mark.asyncio
async def test_pausing_holds_the_setpoint_and_resuming_ramps_on(simulated):
    lab = a_lab(simulated)
    cryostat = lab.instruments["cryostat"]
    task = module(6).SetTemperature(10.0, rate=60.0)
    running = asyncio.ensure_future(task.start(lab))
    await asyncio.sleep(1.0)  # a second of a 10 K ramp at 1 K/s
    task.pause()
    held = cryostat.get_setpoint(OutputChannel.OUTPUT_1)
    assert 18.0 < held < 20.0 and cryostat._target == held
    await asyncio.sleep(0.5)
    assert cryostat.get_setpoint(OutputChannel.OUTPUT_1) == pytest.approx(held)  # it doesn't ramp on
    task.resume()
    assert cryostat._target == 10.0
    task.abort()
    await asyncio.wait_for(running, 10)
    assert task.outcome == "aborted"
    assert cryostat._target == pytest.approx(cryostat.get_setpoint(OutputChannel.OUTPUT_1))  # teardown held it


def test_it_is_registered_as_set_temperature(tmp_path, simulated):
    experiment = module(7).Sample(root_path=str(tmp_path), gui=False)
    experiment.setup()
    routes = {route.path for route in experiment._api_server.app.routes}
    assert "/tasks/set_temperature" in routes


def test_an_input_named_like_a_task_s_own_breaks_it(simulated):
    """The page's warning: a field called `start` hides `Task.start`."""
    source = text(HERE / "sample_7.py").replace("    kelvin: float\n", "    kelvin: float\n    start: float = 0.0\n")
    namespace = {}
    exec(compile(source.replace('if __name__ == "__main__":', "if False:"), "sample.py", "exec"), namespace)
    task = namespace["SetTemperature"](10.0)
    with pytest.raises(TypeError, match="'float' object is not callable"):
        task.start(None)
