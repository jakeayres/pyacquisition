"""Usage › Hold a temperature with PID (docs/usage/pid.md): each version of
hold.py makes its experiment, the PID runs on a queue of its own and holds the
furnace, what it does is recorded, and the Controls instrument changes it, as the
page says. The furnace is simulated step by step, so the tests don't wait for it."""

import asyncio
import importlib.util
import math
import sys
from pathlib import Path

import pytest

from pyacquisition.tasks import PID
from pyacquisition.tasks.pid import PIDController

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "pid"


@pytest.fixture
def furnace_module(monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    sys.modules.pop("furnace", None)
    import furnace

    return furnace


def hold(version: int, tmp_path):
    spec = importlib.util.spec_from_file_location(f"pid_hold_{version}", HERE / f"hold_{version}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    experiment = module.Hold(root_path=str(tmp_path), gui=False)
    experiment.setup()
    return module, experiment


def the_pid(experiment) -> PID:
    (task,) = experiment.task_managers["control"]._task_queue._queue
    return task


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_each_version_measures_the_furnace(version, tmp_path, furnace_module):
    _, experiment = hold(version, tmp_path)
    assert experiment.measurements["temperature"].unit == "°C"
    assert experiment.measurements["temperature"].run() == pytest.approx(20.0, abs=0.1)


def test_the_pid_is_on_a_queue_of_its_own_and_starts_with_the_experiment(tmp_path, furnace_module):
    _, experiment = hold(2, tmp_path)
    assert set(experiment.task_managers) == {"main", "control"}
    assert list(experiment.task_managers["main"]._task_queue._queue) == []
    pid = the_pid(experiment)
    furnace = experiment.instruments["furnace"]
    assert (pid.setpoint, pid.kp, pid.ki, pid.output_min, pid.output_max) == (60.0, 5.0, 0.5, 0.0, 100.0)
    assert pid.read == furnace.temperature and pid.write == furnace.set_power
    assert pid.final_output == 0.0  # the heater off when it ends


def test_its_power_and_setpoint_are_recorded(tmp_path, furnace_module):
    _, experiment = hold(3, tmp_path)
    pid = the_pid(experiment)
    power = experiment.measurements["power"]
    assert power.unit == "%"
    assert power.run() == pid.output == 0.0  # before its first cycle
    assert math.isnan(pid.process_value)  # nothing read yet
    pid.setpoint = 70.0
    assert experiment.measurements["setpoint"].run() == 70.0  # read each time


def test_the_controls_change_the_pid(tmp_path, furnace_module):
    _, experiment = hold(4, tmp_path)
    pid = the_pid(experiment)
    controls = experiment.instruments["pid"]
    assert controls.name == "PID Controls"
    assert sorted(controls.queries) == ["get_setpoint"]  # and identify, under Other
    assert sorted(controls.commands) == ["set_gains", "set_setpoint"]
    controls.set_setpoint(80.0)
    controls.set_gains(8.0, 1.0)
    assert (pid.setpoint, pid.kp, pid.ki) == (80.0, 8.0, 1.0)
    assert controls.get_setpoint() == 80.0


def furnace_under(kp, ki, setpoints, seconds):
    """The furnace's model, a second at a time, under the PID's own controller."""
    controller = PIDController(kp=kp, ki=ki, output_min=0.0, output_max=100.0, max_dt=5.0)
    temperature, power, trace = 20.0, 0.0, []
    for second in range(seconds):
        power = controller.update(setpoints(second), temperature, 1.0)
        for _ in range(10):
            temperature += 0.1 * (20.0 + 0.8 * power - temperature) / 20.0
        trace.append((temperature, power))
    return trace


def test_the_gains_settle_the_furnace_at_60_in_about_30_s_at_half_power():
    trace = furnace_under(5.0, 0.5, lambda s: 60.0, 90)
    assert abs(trace[29][0] - 60.0) < 0.5
    assert trace[-1][0] == pytest.approx(60.0, abs=0.05)
    assert trace[-1][1] == pytest.approx(50.0, abs=0.5)


def test_and_at_80_in_about_25_s_at_three_quarters_power():
    trace = furnace_under(5.0, 0.5, lambda s: 60.0 if s < 90 else 80.0, 180)
    assert abs(trace[90 + 25][0] - 80.0) < 0.6
    assert trace[-1][1] == pytest.approx(75.0, abs=0.5)


@pytest.mark.asyncio
async def test_a_pid_whose_write_keeps_failing_stops_after_five_cycles(tmp_path, furnace_module):
    _, experiment = hold(2, tmp_path)
    pid = the_pid(experiment)
    pid.period = 0.01

    def broken(percent):
        raise TimeoutError("the power supply didn't answer")

    pid.write = broken
    await asyncio.wait_for(pid.start(experiment), 10)
    assert pid.outcome == "failed"


def test_a_value_instead_of_the_query_is_refused(furnace_module):
    furnace = furnace_module.Furnace("furnace")
    with pytest.raises(Exception, match="read and write must be functions"):
        PID(read=furnace.temperature(), write=furnace.set_power, setpoint=60.0)
