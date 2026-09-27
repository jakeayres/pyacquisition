"""How far along a task is, and how long it has run (milestone 12)."""

import asyncio
import datetime
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pyacquisition import Task
from pyacquisition.core.task_manager.task_manager import TaskManager
from pyacquisition.tasks import RampTemperature, SweepMagneticField, WaitFor, WaitUntil
from pyacquisition.tasks import wait as wait_module
from pyacquisition.tasks.field_sweep import RampMagnet
from pyacquisition.tasks.ramps import ramp_progress
from test_builtin_tasks import FakeMagnet


@dataclass
class Steps(Task):
    """Counts its steps, then waits to be told to finish."""

    steps: int = 4

    async def run(self, experiment=None):
        for i in range(self.steps):
            self.set_progress(i, of=self.steps, note=f"step {i + 1}")
            await self.sleep(0.01)
        self.set_progress(self.steps, of=self.steps)
        await self.wait_until(lambda: getattr(self, "finish", False), poll=0.01)


async def until(condition, timeout=3.0):
    end = asyncio.get_running_loop().time() + timeout
    while not condition():
        assert asyncio.get_running_loop().time() < end, "timed out"
        await asyncio.sleep(0.005)


# -------------------------------------------------------------- the clock
def test_a_task_that_has_not_started_has_no_time_or_progress():
    task = Steps()

    assert task.elapsed is None
    assert task.progress is None
    assert task.timing() == {
        "started_at": None,
        "elapsed": None,
        "progress": None,
        "subtasks": [],
    }


@pytest.mark.asyncio
async def test_the_time_spent_paused_is_not_counted():
    task = Steps(steps=0)
    running = asyncio.create_task(task.start())
    await asyncio.sleep(0.2)

    task.pause()
    at_pause = task.elapsed
    await asyncio.sleep(0.4)
    assert task.elapsed == pytest.approx(at_pause, abs=0.02)  # stopped

    task.resume()
    await asyncio.sleep(0.2)
    assert task.elapsed == pytest.approx(0.4, abs=0.1)
    assert task.timing()["started_at"] is not None

    task.finish = True
    await asyncio.wait_for(running, timeout=2)


# -------------------------------------------------------------- progress
def test_progress_is_a_fraction_or_steps():
    task = Steps()
    task.set_progress(0.25)
    assert task.progress == {
        "fraction": 0.25,
        "step": None,
        "steps": None,
        "remaining": None,
        "note": None,
    }

    task.set_progress(3, of=12, note="point 3")
    assert task.progress["fraction"] == 0.25
    assert (task.progress["step"], task.progress["steps"]) == (3, 12)
    assert task.progress["note"] == "point 3"


def test_a_fraction_out_of_range_is_kept_within_zero_to_one():
    task = Steps()
    task.set_progress(1.4)
    assert task.progress["fraction"] == 1.0
    task.set_progress(-0.2)
    assert task.progress["fraction"] == 0.0


@pytest.mark.asyncio
async def test_the_time_remaining_counts_down_between_updates():
    task = Steps(steps=0)
    running = asyncio.create_task(task.start())
    await asyncio.sleep(0.05)

    task.set_progress(0.5, remaining=10)
    await asyncio.sleep(0.3)
    assert task.progress["remaining"] == pytest.approx(9.7, abs=0.1)

    task.finish = True
    await asyncio.wait_for(running, timeout=2)


def test_a_ramps_progress_and_time_left():
    assert ramp_progress(0, 1, 2, per_second=0.5) == (0.5, 2.0)
    assert ramp_progress(4, 3, 2, per_second=0.1) == pytest.approx((0.5, 10.0))
    assert ramp_progress(2, 2, 2, per_second=1) == (1.0, 0.0)  # nowhere to go
    assert ramp_progress(0, 1, 2, per_second=0)[1] is None


# -------------------------------------------------------------- the state
@pytest.mark.asyncio
async def test_the_state_says_how_far_along_the_running_task_is():
    manager = TaskManager()
    task = Steps(steps=4)
    manager.add_task(task)
    runner = asyncio.create_task(manager.run(experiment=None))
    await until(lambda: task.progress and task.progress["step"] == 4)

    current = manager.state()["current_task"]

    assert current["progress"]["step"] == 4 and current["progress"]["steps"] == 4
    assert current["elapsed"] > 0
    assert current["subtasks"] == []
    task.finish = True
    await manager.shutdown()
    await asyncio.wait_for(runner, timeout=2)


def test_a_task_that_cannot_say_how_far_along_it_is_still_shows():
    manager = TaskManager()

    class Broken(Steps):
        def timing(self):
            raise RuntimeError("no idea")

    manager._current_task = Broken()
    current = manager.state()["current_task"]

    assert current["name"] == "Broken"
    assert current["progress"] is None


# -------------------------------------------------------------- the built-in tasks
@pytest.mark.asyncio
async def test_wait_for_counts_its_time_down(monkeypatch):
    monkeypatch.setattr(wait_module, "TICK", 0.05)
    task = WaitFor(seconds=1)
    running = asyncio.create_task(task.start())
    await asyncio.sleep(0.5)

    progress = task.progress
    assert 0.3 < progress["fraction"] < 0.7
    assert progress["remaining"] == pytest.approx(1 - progress["fraction"], abs=0.1)

    await asyncio.wait_for(running, timeout=2)
    assert task.progress["fraction"] == 1.0


@pytest.mark.asyncio
async def test_wait_until_follows_the_clock(monkeypatch):
    clock = [datetime.datetime(2026, 1, 1, 10, 0, 0)]

    class FakeDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0]

    monkeypatch.setattr(
        wait_module,
        "datetime",
        SimpleNamespace(datetime=FakeDatetime, timedelta=datetime.timedelta),
    )
    seen = []

    async def quick(self, seconds):
        await self._check_control_flags()
        clock[0] += datetime.timedelta(seconds=seconds)
        seen.append(self.progress["fraction"])

    monkeypatch.setattr(Task, "sleep", quick)

    task = WaitUntil(hour=10, minute=10)
    await task.start()

    assert seen[0] == 0.0
    assert seen == sorted(seen)
    assert task.progress == {
        "fraction": 1.0,
        "step": None,
        "steps": None,
        "remaining": 0.0,
        "note": None,
    }


@pytest.mark.asyncio
async def test_ramp_temperature_follows_the_setpoint(monkeypatch):
    async def quick(self, seconds):
        await self._check_control_flags()

    monkeypatch.setattr(Task, "sleep", quick)
    seen = []

    class Lakeshore:
        readings = iter([0.0, 1.0, 1.5, 2.0])  # first, where it ramps from

        def set_ramp(self, channel, state, rate):
            pass

        def set_setpoint(self, channel, value):
            pass

        def get_setpoint(self, channel):
            return next(self.readings)

    task = RampTemperature("ls", "OUTPUT_1", setpoint=2.0, ramp_rate=6.0)
    real = task.set_progress

    def record(*args, **kwargs):
        real(*args, **kwargs)
        seen.append(dict(task.progress))

    task.set_progress = record
    await task.start(experiment=SimpleNamespace(instruments={"ls": Lakeshore()}))

    assert task.outcome == "completed", task.failure
    # Half way at 1 K, with 1 K left at 6 K a minute: ten seconds.
    assert seen[0]["fraction"] == 0.5
    assert seen[0]["remaining"] == pytest.approx(10.0, abs=0.1)
    assert seen[0]["note"] == "Setpoint 1 K"
    assert seen[-1]["fraction"] == 1.0


class MovingMagnet(FakeMagnet):
    """A fake magnet whose field moves to its target as the sweep is polled."""

    def __init__(self):
        super().__init__(polls=4)
        self.field = 0.0

    def get_output_field(self):
        if self.activity.name == "TO_SETPOINT":
            self.field = min(self.target, self.field + self.target / 4)
        return self.field


@pytest.mark.asyncio
async def test_a_magnet_sweep_follows_the_field(monkeypatch):
    async def quick(self, seconds):
        await self._check_control_flags()

    monkeypatch.setattr(Task, "sleep", quick)
    magnet = MovingMagnet()
    magnet.rate = 0.5  # tesla a minute
    seen = []

    task = RampMagnet("magnet", setpoint=2.0)
    real = task.set_progress

    def record(*args, **kwargs):
        real(*args, **kwargs)
        seen.append(dict(task.progress))

    task.set_progress = record
    await task.start(experiment=SimpleNamespace(instruments={"magnet": magnet}))

    assert task.outcome == "completed", task.failure
    fractions = [p["fraction"] for p in seen]
    assert fractions == sorted(fractions) and fractions[-1] == 1.0
    # It started from 0.5 T (the first reading), and is at 1 T: a third of the
    # way, with 1 T left at half a tesla a minute.
    assert seen[0]["fraction"] == pytest.approx(1 / 3)
    assert seen[0]["remaining"] == pytest.approx(1.0 / (0.5 / 60))
    assert seen[0]["note"] == "1 T"


@pytest.mark.asyncio
async def test_a_whole_field_sweep_counts_its_stages_and_shows_the_leg(monkeypatch):
    real_sleep = Task.sleep

    async def quick(self, seconds):
        await real_sleep(self, seconds / 1000)

    monkeypatch.setattr(Task, "sleep", quick)
    magnet = MovingMagnet()
    magnet.polls = 10**9  # sweeps until told
    experiment = SimpleNamespace(instruments={"magnet": magnet}, _scribe=Mock())
    task = SweepMagneticField("magnet", setpoint=1.0, ramp_rate=0.5)
    running = asyncio.create_task(task.start(experiment=experiment))

    await until(lambda: task.progress and task.progress["step"] == 2 and task._active_subtasks)
    await until(lambda: task.timing()["subtasks"][0]["name"] == "RampMagnet")
    timing = task.timing()
    assert timing["progress"]["steps"] == 5
    assert timing["progress"]["note"] == "Sweeping to 1 T"

    magnet.polls = 0  # arrive
    await asyncio.wait_for(running, timeout=5)
    assert task.outcome == "completed", task.failure
    assert task.progress["step"] == 5
