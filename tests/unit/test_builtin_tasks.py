"""The tasks that come with pyacquisition, in particular the magnet sweep.

The sweep is tested against a fake power supply that can be made to misbehave, to
show that every check the task makes stops it before anything further is done.
"""

import asyncio
import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pyacquisition import Task
from pyacquisition.core.task_manager import task as task_module
from pyacquisition.instruments.oxford_instruments.mercury_ips import (
    ActivityStatus,
    ModeStatusN,
    SwitchHeaterStatus,
    SystemStatusM,
)
from pyacquisition.tasks import (
    NewFile,
    RampTemperature,
    SweepMagneticField,
    WaitFor,
    WaitUntil,
)
from pyacquisition.tasks import wait as wait_module
from pyacquisition.tasks.field_sweep import RampMagnet, RampMagnetToZero


async def spin(cycles: int = 50):
    for _ in range(cycles):
        await asyncio.sleep(0)


async def until(condition, timeout: float = 2.0):
    end = asyncio.get_running_loop().time() + timeout
    while not condition():
        assert asyncio.get_running_loop().time() < end, "timed out"
        await asyncio.sleep(0.005)


@pytest.fixture
def fast(monkeypatch):
    """Makes `self.sleep` a thousand times shorter, keeping its pause and abort."""
    real = Task.sleep

    async def quick(self, seconds):
        await real(self, seconds / 1000)

    monkeypatch.setattr(Task, "sleep", quick)


class FakeMagnet:
    """A Mercury IPS that records what it is told, and does what a real one does.

    `stuck` names commands that it ignores, `echo` adds an error to what it reads
    back, and `polls` is how many status reads a sweep takes.
    """

    def __init__(self, polls: int = 3):
        self.calls = []
        self.system = SystemStatusM.NORMAL
        self.activity = ActivityStatus.HOLD
        self.heater = SwitchHeaterStatus.OFF_AT_ZERO
        self.rate = 0.0
        self.target = 0.0
        self.polls = polls
        self.stuck = set()
        self.echo = {}
        self.on_arrival = None

    def _do(self, command, effect=None):
        self.calls.append(command)
        if command not in self.stuck and effect:
            effect()

    def hold(self):
        self._do("hold", lambda: setattr(self, "activity", ActivityStatus.HOLD))

    def to_setpoint(self):
        self._do("to_setpoint", self._start(ActivityStatus.TO_SETPOINT))

    def to_zero(self):
        self._do("to_zero", self._start(ActivityStatus.TO_ZERO))

    def _start(self, activity):
        return lambda: setattr(self, "activity", activity)

    def heater_on(self):
        self._do("heater_on", lambda: setattr(self, "heater", SwitchHeaterStatus.ON))

    def heater_off(self):
        self._do(
            "heater_off",
            lambda: setattr(self, "heater", SwitchHeaterStatus.OFF_AT_ZERO),
        )

    def set_field_sweep_rate(self, rate):
        self._do("set_rate", lambda: setattr(self, "rate", rate))

    def get_field_sweep_rate(self):
        return self.rate + self.echo.get("rate", 0.0)

    def set_target_field(self, field):
        self._do("set_target", lambda: setattr(self, "target", field))

    def get_setpoint_field(self):
        return self.target + self.echo.get("target", 0.0)

    def get_system_status(self):
        return self.system

    def get_activity_status(self):
        return self.activity

    def get_switch_heater_status(self):
        return self.heater

    def get_sweep_status(self):
        # A magnet that is on hold is at rest, arrived or not
        if self.activity not in (ActivityStatus.TO_SETPOINT, ActivityStatus.TO_ZERO):
            return ModeStatusN.REST
        if self.polls > 0:
            self.polls -= 1
            if self.polls == 0 and self.on_arrival:
                self.on_arrival()
            return ModeStatusN.SWEEPING if self.polls else ModeStatusN.REST
        return ModeStatusN.REST


@pytest.fixture
def magnet():
    return FakeMagnet()


@pytest.fixture
def experiment(magnet):
    return SimpleNamespace(instruments={"magnet": magnet}, _scribe=Mock())


def sweep(**kwargs):
    return SweepMagneticField("magnet", setpoint=1.5, ramp_rate=0.2, **kwargs)


# ------------------------------------------------------------ a whole sweep
@pytest.mark.asyncio
async def test_a_sweep_does_everything_in_order_and_ends_holding(
    fast, magnet, experiment
):
    task = sweep()
    await task.start(experiment=experiment)

    assert task.outcome == "completed", task.failure
    assert magnet.calls == [
        "hold",
        "heater_on",
        "set_rate",
        "set_target",
        "to_setpoint",
        "hold",  # the end of the first leg
        "to_zero",
        "hold",  # the end of the second leg
        "heater_off",
        "hold",  # the teardown
    ]
    assert magnet.heater is SwitchHeaterStatus.OFF_AT_ZERO
    titles = [
        call.kwargs["title"] for call in experiment._scribe.next_file.call_args_list
    ]
    assert titles == ["Field Sweep to 1.5T", "Field Sweep to 0T"]


# ------------------------------------------------ every check stops the sweep
def system_not_normal(m):
    m.system = SystemStatusM.QUENCHED


def hold_ignored(m):
    m.activity = ActivityStatus.TO_SETPOINT
    m.stuck.add("hold")


CHECKS = [
    # (what goes wrong, what it does, message, a command that must never be sent)
    ("system status at the start", system_not_normal, "System status", "heater_on"),
    ("the magnet is not on hold", hold_ignored, "Activity", "heater_on"),
    (
        "the heater does not switch on",
        lambda m: m.stuck.add("heater_on"),
        "Switch heater",
        "set_rate",
    ),
    (
        "the ramp rate reads back differently",
        lambda m: m.echo.update(rate=0.05),
        "Ramp rate",
        "set_target",
    ),
    (
        "the setpoint reads back differently",
        lambda m: m.echo.update(target=0.05),
        "Setpoint",
        "to_setpoint",
    ),
    (
        "the magnet ignores the command to go to the setpoint",
        lambda m: m.stuck.add("to_setpoint"),
        "Activity",
        "to_zero",
    ),
    (
        "the magnet ignores the command to go to zero",
        lambda m: m.stuck.add("to_zero"),
        "Activity",
        "heater_off",
    ),
    (
        "the heater does not switch off",
        lambda m: m.stuck.add("heater_off"),
        "Switch heater",
        None,
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault, apply, message, must_not_happen",
    CHECKS,
    ids=[check[0] for check in CHECKS],
)
async def test_a_failed_check_stops_the_sweep_and_leaves_the_magnet_on_hold(
    fast, magnet, experiment, fault, apply, message, must_not_happen
):
    apply(magnet)
    task = sweep()

    await task.start(experiment=experiment)

    assert task.outcome == "failed"
    assert message in str(task.failure)
    if must_not_happen:
        assert must_not_happen not in magnet.calls
    assert magnet.calls[-1] == "hold", "the teardown always holds the magnet"


@pytest.mark.asyncio
async def test_a_quench_during_the_sweep_fails_the_task_at_the_end(
    fast, magnet, experiment
):
    magnet.on_arrival = lambda: setattr(magnet, "system", SystemStatusM.QUENCHED)
    task = sweep()

    await task.start(experiment=experiment)

    assert task.outcome == "failed"
    assert "System status: expected NORMAL, got QUENCHED" in str(task.failure)


@pytest.mark.asyncio
async def test_an_abort_mid_sweep_puts_the_magnet_on_hold(fast, magnet, experiment):
    magnet.polls = 10**9  # never arrives
    task = sweep()
    running = asyncio.create_task(task.start(experiment=experiment))
    await until(lambda: "to_setpoint" in magnet.calls)

    task.abort()
    await asyncio.wait_for(running, timeout=2)

    assert task.outcome == "aborted"
    assert magnet.calls[-2:] == ["hold", "hold"], "the leg's teardown, then the sweep's"
    assert magnet.activity is ActivityStatus.HOLD


# -------------------------------------------------------- pause and resume
@pytest.mark.asyncio
async def test_pausing_holds_the_magnet_and_it_is_not_taken_to_have_arrived(
    fast, magnet, experiment
):
    magnet.polls = 10**9
    task = RampMagnet("magnet", 1.5)
    running = asyncio.create_task(task.start(experiment=experiment))
    await until(lambda: "to_setpoint" in magnet.calls)

    task.pause()
    assert magnet.calls[-1] == "hold", "held at once"
    assert magnet.activity is ActivityStatus.HOLD
    await asyncio.sleep(0.1)
    assert not running.done(), "at rest because it is held, not because it arrived"

    task.resume()
    assert magnet.calls[-1] == "to_setpoint", "sent on its way again"
    magnet.polls = 0  # now it arrives
    await asyncio.wait_for(running, timeout=2)
    assert task.outcome == "completed"


@pytest.mark.asyncio
async def test_resuming_after_a_quench_does_not_send_the_magnet_on(
    fast, magnet, experiment
):
    magnet.polls = 10**9
    task = RampMagnet("magnet", 1.5)
    running = asyncio.create_task(task.start(experiment=experiment))
    await until(lambda: "to_setpoint" in magnet.calls)
    task.pause()
    sent = magnet.calls.count("to_setpoint")

    magnet.system = SystemStatusM.QUENCHED
    task.resume()
    await asyncio.wait_for(running, timeout=2)

    assert task.outcome == "failed"
    assert "System status" in str(task.failure)
    assert magnet.calls.count("to_setpoint") == sent
    assert magnet.calls[-1] == "hold"


@pytest.mark.asyncio
async def test_pausing_the_zero_leg_resumes_it_towards_zero(fast, magnet, experiment):
    task = RampMagnetToZero("magnet")
    magnet.polls = 10**9
    running = asyncio.create_task(task.start(experiment=experiment))
    await until(lambda: "to_zero" in magnet.calls)

    task.pause()
    task.resume()

    assert magnet.calls[-3:] == ["to_zero", "hold", "to_zero"]
    magnet.polls = 0
    await asyncio.wait_for(running, timeout=2)


@pytest.mark.asyncio
async def test_pausing_the_whole_sweep_reaches_the_leg_that_is_moving(
    fast, magnet, experiment
):
    magnet.polls = 10**9
    task = sweep()
    running = asyncio.create_task(task.start(experiment=experiment))
    await until(lambda: "to_setpoint" in magnet.calls)

    task.pause()
    assert magnet.calls[-1] == "hold"
    task.resume()
    assert magnet.calls[-1] == "to_setpoint", "the leg knows where it was going"

    task.abort()
    await asyncio.wait_for(running, timeout=2)


def test_the_sweep_describes_itself():
    assert sweep().description == "Sweeping field to 1.5 T at 0.2 T/min"
    assert RampMagnetToZero("magnet").description == "Sweeping field to 0 T"
    assert sweep().parameters["setpoint"] == 1.5


# ------------------------------------------------------------------- waits
@pytest.mark.asyncio
async def test_wait_for_reports_every_five_minutes(fast, monkeypatch):
    logger = Mock()
    monkeypatch.setattr(task_module, "logger", logger)

    await WaitFor(seconds=700).start()

    messages = [call.args[0] for call in logger.info.call_args_list]
    assert "[WaitFor] Waiting for 700 seconds" in messages
    assert "[WaitFor] 0:10:00 remaining" in messages
    assert "[WaitFor] 0:05:00 remaining" in messages
    assert not any("0:00:00" in message for message in messages)


@pytest.mark.asyncio
async def test_wait_for_does_not_count_the_time_it_was_paused():
    task = WaitFor(seconds=0.3)
    loop = asyncio.get_running_loop()
    running = asyncio.create_task(task.start())
    await asyncio.sleep(0.1)

    task.pause()
    await asyncio.sleep(0.5)
    assert not running.done()

    resumed = loop.time()
    task.resume()
    await asyncio.wait_for(running, timeout=2)
    assert loop.time() - resumed >= 0.1


@pytest.mark.asyncio
async def test_wait_for_can_be_aborted_at_once():
    task = WaitFor(hours=1)
    running = asyncio.create_task(task.start())
    await spin()
    task.abort()
    await asyncio.wait_for(running, timeout=1)
    assert task.outcome == "aborted"


@pytest.mark.asyncio
async def test_wait_until_counts_down_to_the_time(monkeypatch):
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

    async def quick(self, seconds):
        await self._check_control_flags()
        clock[0] += datetime.timedelta(seconds=seconds)

    monkeypatch.setattr(Task, "sleep", quick)
    logger = Mock()
    monkeypatch.setattr(task_module, "logger", logger)

    task = WaitUntil(hour=10, minute=12)
    await task.start()

    assert task.outcome == "completed", task.failure
    messages = [call.args[0] for call in logger.info.call_args_list]
    assert "[WaitUntil] Waiting until 10:12" in messages
    assert "[WaitUntil] 0:07:00 remaining" in messages
    assert "[WaitUntil] 0:02:00 remaining" in messages
    assert clock[0] == datetime.datetime(2026, 1, 1, 10, 12, 0)


# -------------------------------------------------------- files, temperature
@pytest.mark.asyncio
async def test_new_file_starts_a_file():
    experiment = SimpleNamespace(_scribe=Mock())

    task = NewFile(file_name="4K", increment_block=True)
    await task.start(experiment=experiment)

    experiment._scribe.next_file.assert_called_once_with(title="4K", next_block=True)
    assert task.outcome == "completed"


@pytest.mark.asyncio
async def test_ramp_temperature_sets_the_ramp_and_waits_for_the_setpoint(fast):
    class Lakeshore:
        def __init__(self):
            self.calls = []
            self.readings = iter([0.5, 1.0, 1.9995, 2.0])

        def set_ramp(self, channel, state, rate):
            self.calls.append(("ramp", rate))

        def set_setpoint(self, channel, value):
            self.calls.append(("setpoint", value))

        def get_setpoint(self, channel):
            return next(self.readings)

    lakeshore = Lakeshore()
    experiment = SimpleNamespace(instruments={"ls": lakeshore})

    task = RampTemperature("ls", "OUTPUT_1", 2.0, 5.0)
    await task.start(experiment=experiment)

    assert task.outcome == "completed", task.failure
    assert lakeshore.calls == [("ramp", 5.0), ("setpoint", 2.0)]
    assert isinstance(task.description, str)
