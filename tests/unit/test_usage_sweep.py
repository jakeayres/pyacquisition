"""Usage › Sweep a temperature (docs/usage/sweep.md): each version of sample.py
makes its experiment, and Sweep goes to each temperature with a file for each,
stops when the interlock trips, and skips a temperature it can't reach, as the
page says. It runs on a fast simulated cryostat, so the tests take seconds."""

import asyncio
import dataclasses
import importlib.util
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fake_rig import REPLIES, open_fakes

from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel, OutputChannel

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "sweep"
SIMULATED = ROOT / "examples" / "simulated_rig"
FORM_TYPES = (int, float, str, bool)


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.fixture
def simulated(monkeypatch):
    """The stand-in cryostat, for the task's logic to run against in these tests
    only, and the lock-in and Lakeshore over a fake connection, for sample.py."""
    open_fakes(monkeypatch, REPLIES)
    monkeypatch.syspath_prepend(str(SIMULATED))
    sys.modules.pop("simulated", None)
    import simulated

    return simulated


def module(version: int):
    spec = importlib.util.spec_from_file_location(f"sweep_sample_{version}", HERE / f"sample_{version}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def a_lab(simulated, kelvin=20.0):
    """A stand-in experiment whose cryostat follows its setpoint in 50 ms, and whose
    files are only noted."""
    cryostat = simulated.SimulatedCryostat("cryostat", temperature=kelvin, lag=0.05)
    return SimpleNamespace(instruments={"cryostat": cryostat}, _scribe=MagicMock())


def files(lab) -> list:
    return [call.kwargs["title"] for call in lab._scribe.next_file.call_args_list]


def fast(module, monkeypatch, rate=6000.0):
    """SetTemperature ramping at `rate` K/min, 6000 by default, so the sweep takes a
    moment."""
    original = module.SetTemperature.__init__

    def init(self, kelvin, rate=rate, tolerance=0.05):
        original(self, kelvin, rate, tolerance)

    monkeypatch.setattr(module.SetTemperature, "__init__", init)


def test_it_starts_from_the_end_of_write_a_task():
    assert text(HERE / "sample_1.py") == text(ROOT / "examples" / "usage" / "write_task" / "sample_7.py")


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_each_version_sets_up(version, tmp_path, simulated):
    experiment = module(version).Sample(root_path=str(tmp_path), gui=False)
    experiment.setup()
    assert list(experiment.measurements) == ["time", "x", "y", "T"]


@pytest.mark.parametrize("version", [2, 3, 4, 5])
def test_the_sweep_s_inputs_can_be_shown_in_a_form(version, simulated):
    fields = dataclasses.fields(module(version).Sweep)
    assert [(f.name, f.type) for f in fields] == [
        ("start_kelvin", float), ("stop_kelvin", float), ("step", float), ("dwell", int)
    ]
    assert all(f.type in FORM_TYPES for f in fields)


@pytest.mark.asyncio
@pytest.mark.parametrize("version", [2, 3, 4])
async def test_the_sweep_goes_to_each_temperature_with_a_file_for_each(version, simulated, monkeypatch):
    loaded = module(version)
    fast(loaded, monkeypatch)
    lab = a_lab(simulated)
    sweep = loaded.Sweep(10.0, 14.0, step=2.0, dwell=0)
    assert sweep.description == "Sweep from 10.0 to 14.0 K"
    await asyncio.wait_for(sweep.start(lab), 30)
    assert sweep.outcome == "completed", sweep.failure
    assert files(lab) == ["10 K", "12 K", "14 K"]
    assert sweep.progress["step"] == sweep.progress["steps"] == 3
    assert abs(lab.instruments["cryostat"].get_temperature(InputChannel.INPUT_A) - 14.0) < 0.06


@pytest.mark.asyncio
async def test_a_sweep_can_go_down(simulated, monkeypatch):
    loaded = module(4)
    fast(loaded, monkeypatch)
    lab = a_lab(simulated)
    await asyncio.wait_for(loaded.Sweep(14.0, 10.0, step=2.0, dwell=0).start(lab), 30)
    assert files(lab) == ["14 K", "12 K", "10 K"]


@pytest.mark.asyncio
async def test_the_interlock_stops_the_sweep_above_25_k_and_the_cryostat_is_held(simulated, monkeypatch):
    loaded = module(3)
    fast(loaded, monkeypatch, rate=60.0)  # 1 K/s, so the interlock sees 25 K
    lab = a_lab(simulated, kelvin=24.0)
    cryostat = lab.instruments["cryostat"]
    sweep = loaded.Sweep(24.0, 30.0, step=3.0, dwell=0)
    await asyncio.wait_for(sweep.start(lab), 60)
    assert sweep.outcome == "failed"
    assert isinstance(sweep.failure, RuntimeError)
    found = re.fullmatch(r"The sample is at (\d+\.\d\d) K: too warm", str(sweep.failure))
    assert found and 25.0 <= float(found.group(1)) < 26.2  # checked every second, at 1 K a second (and rounded)
    assert cryostat._target == pytest.approx(cryostat.get_setpoint(OutputChannel.OUTPUT_1))  # held there


@pytest.mark.asyncio
async def test_the_interlock_on_its_own(simulated):
    lab = a_lab(simulated, kelvin=30.0)
    interlock = module(3).Interlock(limit=25.0)
    await asyncio.wait_for(interlock.start(lab), 10)
    assert interlock.outcome == "failed"
    assert re.fullmatch(r"The sample is at (29\.99|30\.00|30\.01) K: too warm", str(interlock.failure))


@pytest.mark.asyncio
async def test_a_temperature_that_takes_too_long_is_skipped(simulated, monkeypatch):
    loaded = module(4)
    fast(loaded, monkeypatch)
    real_run = loaded.SetTemperature.run

    async def run(self, experiment):
        if self.kelvin == 12.0:
            raise TimeoutError("not there after an hour")
        await real_run(self, experiment)

    monkeypatch.setattr(loaded.SetTemperature, "run", run)
    logged = []
    monkeypatch.setattr(loaded.Sweep, "log", lambda self, message, level="info": logged.append((level, message)))
    lab = a_lab(simulated)
    sweep = loaded.Sweep(10.0, 14.0, step=2.0, dwell=0)
    await asyncio.wait_for(sweep.start(lab), 30)
    assert sweep.outcome == "completed"
    assert files(lab) == ["10 K", "14 K"]
    assert ("warning", "12 K took too long: skipped") in logged


@pytest.mark.asyncio
async def test_another_error_still_stops_the_sweep(simulated, monkeypatch):
    loaded = module(4)
    fast(loaded, monkeypatch)

    async def run(self, experiment):
        raise ConnectionError("the cryostat stopped answering")

    monkeypatch.setattr(loaded.SetTemperature, "run", run)
    sweep = loaded.Sweep(10.0, 14.0, step=2.0, dwell=0)
    await asyncio.wait_for(sweep.start(a_lab(simulated)), 30)
    assert sweep.outcome == "failed" and isinstance(sweep.failure, ConnectionError)


@pytest.mark.asyncio
async def test_a_step_of_0_fails_at_once(simulated):
    sweep = module(5).Sweep(10.0, 14.0, step=0.0, dwell=0)
    await asyncio.wait_for(sweep.start(a_lab(simulated)), 10)
    assert sweep.outcome == "failed" and str(sweep.failure) == "float division by zero"


def test_it_is_registered_as_sweep(tmp_path, simulated):
    experiment = module(5).Sample(root_path=str(tmp_path), gui=False)
    experiment.setup()
    routes = {route.path for route in experiment._api_server.app.routes}
    assert {"/tasks/sweep", "/tasks/set_temperature"} <= routes
