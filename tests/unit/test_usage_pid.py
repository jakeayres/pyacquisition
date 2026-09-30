"""Usage › Hold a temperature with PID (docs/usage/pid.md): each version of hold.py
makes its experiment on the simulated stage, through the real Lakeshore_350 and
SR_830 drivers; the heater is handed to the computer and turned off at the end;
the PID runs on a queue of its own, holds the thermometer's resistance, and is
recorded; and the Controls instrument changes it, as the page says. The stage runs
on a clock the tests move, so they don't wait for it."""

import asyncio
import importlib.util
import math
import random
import sys
from pathlib import Path

import pytest

from pyacquisition.tasks import PID
from pyacquisition.tasks.pid import PIDController

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "pid"
PAGE = ROOT / "docs" / "usage" / "pid.md"


class Clock:
    """Stands in for time.monotonic, for the stage: it moves when told to."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    sys.modules.pop("stage", None)
    import stage

    fake = Clock()
    monkeypatch.setattr(stage.time, "monotonic", fake)
    random.seed(1)
    return fake


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


def test_the_first_version_connects_the_two_real_drivers(tmp_path, clock):
    from pyacquisition.instruments import SR_830, Lakeshore_350

    _, experiment = hold(1, tmp_path)
    assert isinstance(experiment.instruments["lockin"], SR_830)
    assert isinstance(experiment.instruments["lakeshore"], Lakeshore_350)
    assert experiment.instruments["lockin"].get_x() == pytest.approx(1.9947e-4, rel=2e-3)


def settings(experiment) -> dict:
    """What has been written to the Lakeshore, as the stage keeps it."""
    return experiment.instruments["lakeshore"]._visa_resource.settings


@pytest.mark.parametrize("version", [2, 3, 4, 5])
def test_each_version_reads_the_cold_thermometer_through_the_lock_in(version, tmp_path, clock):
    _, experiment = hold(version, tmp_path)
    assert experiment.measurements["R"].unit == "Ω"
    assert experiment.measurements["R"].run() == pytest.approx(1994.7, abs=2)  # at 4.2 K
    assert experiment.measurements["T"].run() == pytest.approx(4.2)
    assert set(experiment.instruments) >= {"clock", "lockin", "lakeshore"}


def test_the_lock_in_drives_100_na_and_reads_it(tmp_path, clock):
    module, experiment = hold(2, tmp_path)
    assert module.EXCITATION == 100e-9
    lockin = experiment.instruments["lockin"]._visa_resource.settings
    assert float(lockin["SLVL?"]) == 1.0  # 1 V, through the 10 Mohm


@pytest.mark.parametrize("version", [3, 4, 5])
def test_the_heater_is_handed_to_the_computer_and_off_at_the_end(version, tmp_path, clock, capsys):
    _, experiment = hold(version, tmp_path)
    assert settings(experiment)["OUTMODE? 1"].split(",")[0] == "3"  # open loop
    assert settings(experiment)["RANGE? 1"] == "3"
    assert settings(experiment)["MOUT? 1"] == "0.00"
    assert experiment.measurements["heater"].unit == "%"

    experiment.teardown()
    assert settings(experiment)["RANGE? 1"] == "0"
    assert capsys.readouterr().out.strip().endswith("The heater is off.")


def test_the_pid_reads_the_resistance_and_writes_the_heater(tmp_path, clock):
    _, experiment = hold(4, tmp_path)
    assert set(experiment.task_managers) == {"main", "control"}
    assert list(experiment.task_managers["main"]._task_queue._queue) == []
    pid = the_pid(experiment)
    assert (pid.setpoint, pid.kp, pid.ki, pid.output_min, pid.output_max) == (1650.0, 1.0, 0.2, 0.0, 100.0)
    assert pid.inverted is True
    assert pid.final_output == 0.0  # the heater at 0 when it ends
    assert pid.label == "sample"

    assert pid.read() == pytest.approx(experiment.measurements["R"].run(), rel=1e-3)
    pid.write(40.0)
    assert settings(experiment)["MOUT? 1"] == "40.00"
    assert experiment.measurements["heater"].run() == 40.0


def test_its_setpoint_is_recorded(tmp_path, clock):
    _, experiment = hold(4, tmp_path)
    pid = the_pid(experiment)
    assert experiment.measurements["setpoint"].unit == "Ω"
    pid.setpoint = 1560.0
    assert experiment.measurements["setpoint"].run() == 1560.0


def test_the_controls_change_the_pid(tmp_path, clock):
    _, experiment = hold(5, tmp_path)
    pid = the_pid(experiment)
    controls = experiment.instruments["pid"]
    controls.set_setpoint(1560.0)
    controls.set_gains(0.5, 0.1)
    assert (pid.setpoint, pid.kp, pid.ki) == (1560.0, 0.5, 0.1)
    assert controls.get_setpoint() == 1560.0


def run_the_stage(experiment, clock, setpoints, seconds, inverted=True):
    """The experiment's own read and write, a second at a time, under the PID's own
    controller, with the stage's clock moved on each second."""
    pid = the_pid(experiment)
    controller = PIDController(
        kp=pid.kp, ki=pid.ki, output_min=0.0, output_max=100.0, inverted=inverted, max_dt=5.0
    )
    lakeshore = experiment.instruments["lakeshore"]
    trace = []
    for second in range(seconds):
        pid.write(controller.update(setpoints(second), pid.read(), 1.0))
        clock.now += 1.0
        trace.append((
            pid.read(),
            lakeshore.get_temperature(lakeshore.InputChannel.INPUT_A),
            lakeshore.get_heater_output(lakeshore.OutputChannel.OUTPUT_1),
        ))
    return trace


def test_it_settles_at_1650_ohms_in_about_20_s_at_8_k_and_a_third_power(tmp_path, clock):
    _, experiment = hold(4, tmp_path)
    trace = run_the_stage(experiment, clock, lambda s: 1650.0, 80)
    assert all(abs(r - 1650.0) < 3 for r, _, _ in trace[20:])
    resistance, temperature, heater = trace[-1]
    assert temperature == pytest.approx(7.97, abs=0.03)
    assert heater == pytest.approx(32, abs=2)


def test_and_at_1560_ohms_in_about_10_s_at_10_k_and_half_power(tmp_path, clock):
    _, experiment = hold(4, tmp_path)
    trace = run_the_stage(experiment, clock, lambda s: 1650.0 if s < 80 else 1560.0, 160)
    assert all(abs(r - 1560.0) < 3 for r, _, _ in trace[80 + 10:])
    resistance, temperature, heater = trace[-1]
    assert temperature == pytest.approx(10.1, abs=0.05)
    assert heater == pytest.approx(50, abs=2)


def test_without_inverted_the_heater_stays_off_and_the_sample_cold(tmp_path, clock):
    _, experiment = hold(4, tmp_path)
    trace = run_the_stage(experiment, clock, lambda s: 1650.0, 60, inverted=False)
    resistance, temperature, heater = trace[-1]
    assert heater == 0.0 and temperature == pytest.approx(4.2)
    assert "`inverted=True` is missing" in PAGE.read_text(encoding="utf-8")


def test_the_page_s_numbers_are_the_thermometer_s():
    def resistance(kelvin):
        return 1000.0 * math.exp(math.sqrt(2.0 / kelvin))

    assert resistance(4.2) == pytest.approx(1995, abs=2)
    assert resistance(7.97) == pytest.approx(1650, abs=1)
    assert resistance(10.1) == pytest.approx(1560, abs=1)


@pytest.mark.asyncio
async def test_a_pid_whose_write_keeps_failing_stops_after_five_cycles(tmp_path, clock):
    _, experiment = hold(4, tmp_path)
    pid = the_pid(experiment)
    pid.period = 0.01

    def broken(percent):
        raise TimeoutError("the Lakeshore didn't answer")

    pid.write = broken
    await asyncio.wait_for(pid.start(experiment), 10)
    assert pid.outcome == "failed"


def test_a_value_instead_of_the_function_is_refused():
    with pytest.raises(Exception, match="read and write must be functions"):
        PID(read=1650.0, write=print, setpoint=1650.0)
