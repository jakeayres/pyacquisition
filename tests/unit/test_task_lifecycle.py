"""Pause, resume and abort of a task: hooks, cancellation, outcomes and the toolkit."""

import asyncio
from dataclasses import dataclass, field
from unittest.mock import Mock

import pytest

from pyacquisition import Task
from pyacquisition.core.task_manager import task as task_module
from pyacquisition.core.task_manager.task_manager import TaskManager


async def spin(cycles: int = 50):
    """Give other tasks on the event loop a chance to run, without real waiting."""
    for _ in range(cycles):
        await asyncio.sleep(0)


async def until(condition, timeout: float = 2.0):
    """Waits for something to become true."""
    end = asyncio.get_running_loop().time() + timeout
    while not condition():
        assert asyncio.get_running_loop().time() < end, "timed out"
        await asyncio.sleep(0.01)


@dataclass
class Sleeper(Task):
    """Sleeps with `self.sleep`, and records its lifecycle."""

    seconds: float = 3600
    events: list = field(default_factory=list)

    async def setup(self, experiment=None):
        self.events.append("setup")

    async def run(self, experiment=None):
        self.events.append("run")
        await self.sleep(self.seconds)
        self.events.append("woke")

    async def teardown(self, experiment=None):
        self.events.append("teardown")


@dataclass
class Hooked(Task):
    """Records its hooks, and waits."""

    events: list = field(default_factory=list)
    label: str = "t"

    async def run(self, experiment=None):
        self.events.append(f"{self.label}:run")
        await self.checkpoint()
        await self.sleep(3600)

    def on_pause(self, experiment=None):
        self.events.append(f"{self.label}:pause")

    def on_resume(self, experiment=None):
        self.events.append(f"{self.label}:resume")

    async def teardown(self, experiment=None):
        self.events.append(f"{self.label}:teardown")


# ----------------------------------------------------------------- abort
@pytest.mark.asyncio
async def test_abort_ends_a_long_sleep_at_once_and_tears_down():
    task = Sleeper()
    running = asyncio.create_task(task.start())
    await spin()
    assert task.events == ["setup", "run"]

    task.abort()
    await asyncio.wait_for(running, timeout=1)

    assert task.events == ["setup", "run", "teardown"]
    assert task.outcome == "aborted"


@pytest.mark.asyncio
async def test_abort_interrupts_a_plain_asyncio_sleep_too():
    events = []

    class Raw(Task):
        async def run(self, experiment=None):
            await asyncio.sleep(3600)

        async def teardown(self, experiment=None):
            events.append("teardown")

    task = Raw()
    running = asyncio.create_task(task.start())
    await spin()
    task.abort()
    await asyncio.wait_for(running, timeout=1)

    assert events == ["teardown"]
    assert task.outcome == "aborted"


@pytest.mark.asyncio
async def test_abort_reaches_a_wait_deep_in_a_helper():
    events = []

    class Deep(Task):
        async def helper(self):
            await self.sleep(3600)
            events.append("helper finished")

        async def run(self, experiment=None):
            await self.helper()

    task = Deep()
    running = asyncio.create_task(task.start())
    await spin()
    task.abort()
    await asyncio.wait_for(running, timeout=1)

    assert events == []
    assert task.outcome == "aborted"


@pytest.mark.asyncio
async def test_a_second_abort_does_not_interrupt_the_teardown():
    events = []

    class SlowTeardown(Task):
        async def run(self, experiment=None):
            await self.sleep(3600)

        async def teardown(self, experiment=None):
            events.append("teardown began")
            await asyncio.sleep(0.1)
            events.append("teardown finished")

    task = SlowTeardown()
    running = asyncio.create_task(task.start())
    await spin()
    task.abort()
    await until(lambda: events)
    task.abort()  # a second click on Abort
    await asyncio.wait_for(running, timeout=1)

    assert events == ["teardown began", "teardown finished"]


@pytest.mark.asyncio
async def test_the_teardown_can_wait_even_though_the_task_was_aborted_and_paused():
    events = []

    class Cleans(Task):
        async def run(self, experiment=None):
            await self.sleep(3600)

        async def teardown(self, experiment=None):
            await self.sleep(0.05)  # a checkpoint that must not be held up
            await self.checkpoint()
            events.append("cleaned up")

    task = Cleans()
    running = asyncio.create_task(task.start())
    await spin()
    # what the task manager does to a task that it aborts
    task.abort()
    task.pause()
    await asyncio.wait_for(running, timeout=1)

    assert events == ["cleaned up"]


@pytest.mark.asyncio
async def test_cancelling_whatever_runs_the_task_still_tears_it_down():
    task = Sleeper()
    running = asyncio.create_task(task.start())
    await spin()

    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running

    assert task.events == ["setup", "run", "teardown"]
    assert task.outcome == "aborted"


@pytest.mark.asyncio
async def test_a_generator_task_cleans_up_before_its_teardown_after_an_abort():
    events = []

    class Legacy(Task):
        async def run(self, experiment=None):
            try:
                yield "step"
                await asyncio.sleep(3600)
            finally:
                events.append("generator cleanup")

        async def teardown(self, experiment=None):
            events.append("teardown")

    task = Legacy()
    running = asyncio.create_task(task.start())
    await spin()
    task.abort()
    await asyncio.wait_for(running, timeout=1)

    assert events == ["generator cleanup", "teardown"]


@pytest.mark.asyncio
async def test_a_generator_task_held_at_a_checkpoint_cleans_up_on_abort():
    events = []

    class Legacy(Task):
        async def run(self, experiment=None):
            try:
                yield "step"
                yield "never"
            finally:
                events.append("generator cleanup")

        async def teardown(self, experiment=None):
            events.append("teardown")

    task = Legacy()
    running = asyncio.create_task(task.start())
    await spin()
    task.pause()  # holds it at the checkpoint after the first yield
    await spin()
    task.abort()
    await asyncio.wait_for(running, timeout=1)

    assert events == ["generator cleanup", "teardown"]


# ----------------------------------------------------------------- pause
@pytest.mark.asyncio
async def test_a_pause_freezes_a_sleep_so_only_running_time_counts():
    task = Sleeper(seconds=0.4)
    loop = asyncio.get_running_loop()
    running = asyncio.create_task(task.start())
    await asyncio.sleep(0.15)

    task.pause()
    await asyncio.sleep(0.6)  # far longer than what is left
    assert not running.done(), "the time must not pass while paused"

    resumed = loop.time()
    task.resume()
    await asyncio.wait_for(running, timeout=2)

    assert loop.time() - resumed >= 0.15, "the rest of the sleep was still to do"
    assert task.events == ["setup", "run", "woke", "teardown"]


@pytest.mark.asyncio
async def test_code_after_a_wait_does_not_run_while_paused():
    events = []

    class Steps(Task):
        async def run(self, experiment=None):
            await self.sleep(0.05)
            events.append("after the sleep")

    task = Steps()
    running = asyncio.create_task(task.start())
    await spin()
    task.pause()
    await asyncio.sleep(0.2)
    assert events == []

    task.resume()
    await asyncio.wait_for(running, timeout=1)
    assert events == ["after the sleep"]


@pytest.mark.asyncio
async def test_a_paused_task_can_be_aborted():
    task = Sleeper()
    running = asyncio.create_task(task.start())
    await spin()
    task.pause()
    await spin()

    task.abort()
    await asyncio.wait_for(running, timeout=1)

    assert task.events == ["setup", "run", "teardown"]
    assert task.outcome == "aborted"


# ----------------------------------------------------------------- hooks
@pytest.mark.asyncio
async def test_pause_and_resume_call_their_hooks_at_once_with_the_experiment():
    experiment = object()
    seen = []

    class Recording(Hooked):
        def on_pause(self, experiment=None):
            seen.append(("pause", experiment))

        def on_resume(self, experiment=None):
            seen.append(("resume", experiment))

    task = Recording()
    running = asyncio.create_task(task.start(experiment=experiment))
    await spin()

    task.pause()
    assert seen == [("pause", experiment)], "called by pause(), not at a checkpoint"
    task.resume()
    assert seen == [("pause", experiment), ("resume", experiment)]

    task.abort()
    await asyncio.wait_for(running, timeout=1)


@pytest.mark.asyncio
async def test_the_pause_hook_runs_even_while_the_task_waits_in_plain_asyncio():
    events = []

    class Raw(Task):
        async def run(self, experiment=None):
            await asyncio.sleep(3600)

        def on_pause(self, experiment=None):
            events.append("hold")

    task = Raw()
    running = asyncio.create_task(task.start())
    await spin()
    task.pause()

    assert events == ["hold"]
    task.abort()
    await asyncio.wait_for(running, timeout=1)


@pytest.mark.asyncio
async def test_the_task_carries_on_only_after_on_resume_has_run():
    events = []

    class Checks(Task):
        async def run(self, experiment=None):
            await self.sleep(3600)
            events.append("carried on")

        def on_pause(self, experiment=None):
            events.append("pause")

        def on_resume(self, experiment=None):
            events.append("resume")

    task = Checks()
    running = asyncio.create_task(task.start())
    await spin()
    task.pause()
    task.resume()
    await spin()

    assert events == ["pause", "resume"]
    task.abort()
    await asyncio.wait_for(running, timeout=1)


@pytest.mark.asyncio
async def test_the_wait_is_not_released_until_the_resume_hook_is_done():
    """A `wait_until` must not look at the hardware before `on_resume` has sent it on
    its way, or a magnet that was held would look as if it had arrived."""
    state = {"moving": True}
    checks = []

    class Ramp(Task):
        async def run(self, experiment=None):
            await self.wait_until(
                lambda: checks.append(state["moving"]) or not state["moving"],
                poll=0.01,
            )

        def on_pause(self, experiment=None):
            state["moving"] = False  # held: it looks as if it has arrived

        def on_resume(self, experiment=None):
            state["moving"] = True  # sent on its way again

    task = Ramp()
    running = asyncio.create_task(task.start())
    await asyncio.sleep(0.05)
    task.pause()
    await asyncio.sleep(0.05)
    task.resume()
    await asyncio.sleep(0.1)

    assert not running.done(), "it looked at the magnet while it was held"
    assert False not in checks, "the condition was checked while the magnet was held"

    state["moving"] = False
    await asyncio.wait_for(running, timeout=1)


@pytest.mark.asyncio
async def test_the_hooks_are_called_once_for_each_pause():
    task = Hooked()
    running = asyncio.create_task(task.start())
    await spin()

    task.pause()
    task.pause()  # already paused
    task.resume()
    task.resume()  # already running
    task.pause()
    task.resume()

    assert task.events == ["t:run", "t:pause", "t:resume", "t:pause", "t:resume"]
    task.abort()
    await asyncio.wait_for(running, timeout=1)


@pytest.mark.asyncio
async def test_a_pause_before_the_task_runs_calls_no_hooks():
    task = Hooked()
    task.pause()
    task.resume()
    assert task.events == []


@pytest.mark.asyncio
async def test_a_task_paused_during_its_setup_is_held_before_it_runs():
    class SlowSetup(Hooked):
        async def setup(self, experiment=None):
            await asyncio.sleep(0.1)
            self.events.append("setup done")

    task = SlowSetup()
    running = asyncio.create_task(task.start())
    await spin()
    task.pause()
    await asyncio.sleep(0.3)
    assert task.events == ["setup done"], "run() has not begun"

    task.resume()
    await spin()
    assert task.events == ["setup done", "t:run"], "and no hook, as it was not running"
    task.abort()
    await asyncio.wait_for(running, timeout=1)


@pytest.mark.asyncio
async def test_aborting_a_paused_task_does_not_call_on_resume():
    task = Hooked()
    running = asyncio.create_task(task.start())
    await spin()
    task.pause()
    task.abort()
    await asyncio.wait_for(running, timeout=1)

    assert task.events == ["t:run", "t:pause", "t:teardown"]


@pytest.mark.asyncio
async def test_hooks_reach_running_subtasks_innermost_first_when_pausing():
    events = []
    child = Hooked(events, "child")

    @dataclass
    class Parent(Hooked):
        async def run(self, experiment=None):
            await self.run_subtask(child)

    parent = Parent(events, "parent")
    running = asyncio.create_task(parent.start())
    await spin()

    parent.pause()
    assert events[-2:] == ["child:pause", "parent:pause"]
    parent.resume()
    assert events[-2:] == ["parent:resume", "child:resume"]

    parent.abort()
    await asyncio.wait_for(running, timeout=1)


@pytest.mark.asyncio
async def test_a_failing_pause_hook_fails_the_task_and_tears_it_down():
    class Bad(Hooked):
        def on_pause(self, experiment=None):
            raise OSError("cannot hold")

    task = Bad()
    running = asyncio.create_task(task.start())
    await spin()
    task.pause()
    await asyncio.wait_for(running, timeout=1)

    assert task.outcome == "failed"
    assert isinstance(task.failure, OSError)
    assert task.events == ["t:run", "t:teardown"]


@pytest.mark.asyncio
async def test_a_failing_resume_hook_stops_the_task_instead_of_carrying_on():
    events = []

    class Bad(Task):
        async def run(self, experiment=None):
            await self.sleep(3600)
            events.append("carried on")

        def on_resume(self, experiment=None):
            raise ValueError("system not normal")

        async def teardown(self, experiment=None):
            events.append("teardown")

    task = Bad()
    running = asyncio.create_task(task.start())
    await spin()
    task.pause()
    task.resume()
    await asyncio.wait_for(running, timeout=1)

    assert events == ["teardown"]
    assert task.outcome == "failed"
    assert str(task.failure) == "system not normal"


@pytest.mark.asyncio
async def test_a_failing_hook_in_a_subtask_is_raised_in_the_parent():
    events = []

    class Bad(Hooked):
        def on_pause(self, experiment=None):
            raise OSError("cannot hold")

    @dataclass
    class Parent(Task):
        async def run(self, experiment=None):
            try:
                await self.run_subtask(Bad(events))
            except OSError:
                events.append("parent caught it")

    parent = Parent()
    running = asyncio.create_task(parent.start())
    await spin()
    parent.pause()
    await asyncio.wait_for(running, timeout=1)

    assert events == ["t:run", "t:teardown", "parent caught it"]
    assert parent.outcome == "completed"


# -------------------------------------------------------------- outcomes
@pytest.mark.asyncio
async def test_the_outcome_says_how_the_task_ended():
    class Fine(Task):
        async def run(self, experiment=None):
            pass

    class Boom(Task):
        async def run(self, experiment=None):
            raise RuntimeError("boom")

    fine, boom = Fine(), Boom()
    assert fine.outcome is None

    await fine.start()
    await boom.start()

    assert fine.outcome == "completed" and fine.failure is None
    assert boom.outcome == "failed"
    assert isinstance(boom.failure, RuntimeError)


@pytest.mark.asyncio
async def test_an_error_in_the_teardown_fails_a_task_that_had_finished():
    class BadTeardown(Task):
        async def run(self, experiment=None):
            pass

        async def teardown(self, experiment=None):
            raise RuntimeError("could not make it safe")

    task = BadTeardown()
    await task.start()

    assert task.outcome == "failed"
    assert str(task.failure) == "could not make it safe"


@pytest.mark.asyncio
async def test_an_error_in_the_teardown_does_not_hide_the_error_that_came_first():
    class BothFail(Task):
        async def run(self, experiment=None):
            raise RuntimeError("first")

        async def teardown(self, experiment=None):
            raise RuntimeError("second")

    task = BothFail()
    await task.start()

    assert str(task.failure) == "first"


@pytest.mark.asyncio
async def test_a_task_that_is_started_again_forgets_its_last_outcome():
    task = Sleeper(seconds=0)
    task.abort()
    await task.start()
    assert task.outcome == "completed"


@pytest.mark.asyncio
async def test_a_failure_is_logged_as_an_error(monkeypatch):
    mock_logger = Mock()
    monkeypatch.setattr(task_module, "logger", mock_logger)

    class Boom(Task):
        async def run(self, experiment=None):
            raise RuntimeError("boom")

    await Boom().start()

    messages = [call.args[0] for call in mock_logger.error.call_args_list]
    assert messages == ["[Boom] Task failed: RuntimeError: boom"]


# ------------------------------------------------------------ the toolkit
@pytest.mark.asyncio
async def test_log_writes_under_the_name_of_the_task(monkeypatch):
    mock_logger = Mock()
    monkeypatch.setattr(task_module, "logger", mock_logger)

    class Talks(Task):
        async def run(self, experiment=None):
            self.log("hello")
            self.log("careful", level="warning")

    await Talks().start()

    mock_logger.info.assert_any_call("[Talks] hello")
    mock_logger.warning.assert_called_once_with("[Talks] careful")


@pytest.mark.asyncio
async def test_wait_until_polls_until_the_condition_holds():
    calls = []

    class Waits(Task):
        async def run(self, experiment=None):
            await self.wait_until(lambda: len(calls.append(1) or calls) >= 3, poll=0.01)
            calls.append("done")

    await Waits().start()

    assert calls == [1, 1, 1, "done"]


@pytest.mark.asyncio
async def test_wait_until_takes_an_async_condition():
    state = {"n": 0}

    async def ready():
        state["n"] += 1
        return state["n"] >= 2

    class Waits(Task):
        async def run(self, experiment=None):
            await self.wait_until(ready, poll=0.01)

    task = Waits()
    await task.start()

    assert task.outcome == "completed" and state["n"] == 2


@pytest.mark.asyncio
async def test_wait_until_gives_up_after_the_timeout():
    class Waits(Task):
        async def run(self, experiment=None):
            await self.wait_until(
                lambda: False, poll=0.01, timeout=0.05, what="the field to settle"
            )

    task = Waits()
    await task.start()

    assert task.outcome == "failed"
    assert isinstance(task.failure, TimeoutError)
    assert "the field to settle" in str(task.failure)


@pytest.mark.asyncio
async def test_wait_until_does_not_check_the_condition_while_paused():
    checks = []

    class Waits(Task):
        async def run(self, experiment=None):
            await self.wait_until(lambda: checks.append(1) and False, poll=0.02)

    task = Waits()
    running = asyncio.create_task(task.start())
    await asyncio.sleep(0.1)
    task.pause()
    await asyncio.sleep(0.05)
    before = len(checks)
    await asyncio.sleep(0.2)

    assert len(checks) == before

    task.abort()
    await asyncio.wait_for(running, timeout=1)


@pytest.mark.asyncio
async def test_paused_time_does_not_count_towards_the_timeout():
    class Waits(Task):
        async def run(self, experiment=None):
            await self.wait_until(lambda: False, poll=0.02, timeout=0.3)

    task = Waits()
    running = asyncio.create_task(task.start())
    await asyncio.sleep(0.1)
    task.pause()
    await asyncio.sleep(0.5)  # longer than the whole timeout
    assert not running.done()

    task.resume()
    await asyncio.wait_for(running, timeout=2)
    assert task.outcome == "failed" and isinstance(task.failure, TimeoutError)


def test_expect_passes_a_match_and_logs_it(monkeypatch):
    mock_logger = Mock()
    monkeypatch.setattr(task_module, "logger", mock_logger)

    class Check(Task):
        pass

    assert Check().expect(5, 5, "Ramp rate") == 5
    mock_logger.info.assert_called_once_with("[Check] Ramp rate: 5 OK")


def test_expect_raises_on_a_mismatch_naming_both_values():
    from enum import Enum

    class Activity(Enum):
        HOLD = 0
        TO_SETPOINT = 1

    with pytest.raises(ValueError, match="Activity: expected HOLD, got TO_SETPOINT"):
        Task().expect(Activity.TO_SETPOINT, Activity.HOLD, "Activity")


def test_expect_accepts_a_tolerance():
    task = Task()
    task.expect(1.0004, 1.0, "Field", tolerance=0.001)
    with pytest.raises(ValueError):
        task.expect(1.01, 1.0, "Field", tolerance=0.001)
    with pytest.raises(ValueError):
        task.expect(1.0004, 1.0, "Field")  # exact by default


# --------------------------------------------------------------- subtasks
@pytest.mark.asyncio
async def test_aborting_the_parent_ends_concurrent_subtasks_at_once():
    events = []

    @dataclass
    class Parent(Task):
        async def run(self, experiment=None):
            await self.run_subtasks(Sleeper(events=events), Sleeper(events=events))

    parent = Parent()
    running = asyncio.create_task(parent.start())
    await spin()
    parent.abort()
    await asyncio.wait_for(running, timeout=1)

    assert events.count("teardown") == 2
    assert "woke" not in events


@pytest.mark.asyncio
async def test_a_parent_that_carries_on_after_a_background_failure_can_still_be_aborted():
    events = []

    class Fails(Task):
        async def run(self, experiment=None):
            await self.sleep(0.01)
            raise RuntimeError("background failed")

    class Carries(Task):
        async def run(self, experiment=None):
            try:
                async with self.alongside(Fails()):
                    await self.sleep(3600)
            except RuntimeError:
                events.append("caught")
            await self.sleep(3600)

        async def teardown(self, experiment=None):
            events.append("teardown")

    task = Carries()
    running = asyncio.create_task(task.start())
    await until(lambda: "caught" in events)
    task.abort()
    await asyncio.wait_for(running, timeout=1)

    assert events == ["caught", "teardown"]
    assert task.outcome == "aborted"


# ---------------------------------------------------------------- display
def test_the_description_defaults_to_the_first_line_of_the_docstring():
    @dataclass
    class MoveStage(Task):
        """Move the stage to a position.

        More that is not shown.
        """

        position: float = 1.5

    assert MoveStage().description == "Move the stage to a position."


def test_no_docstring_means_no_description():
    @dataclass
    class Bare(Task):
        position: float = 1.5

    assert Bare().description is None
    assert Task().description is None


def test_the_parameters_default_to_the_inputs():
    @dataclass
    class MoveStage(Task):
        position: float = 1.5
        axis: str = "x"

    assert MoveStage(position=2.0).parameters == {"position": 2.0, "axis": "x"}


def test_a_description_and_parameters_can_still_be_overridden():
    @dataclass
    class MoveStage(Task):
        """Not used."""

        position: float = 1.5

        @property
        def description(self):
            return "custom"

        @property
        def parameters(self):
            return {"only": 1}

    assert MoveStage().display_dict() == {
        "name": "MoveStage",
        "description": "custom",
        "parameters": {"only": 1},
    }


# ---------------------------------------------------------- the task manager
@dataclass
class Marker(Task):
    events: list = field(default_factory=list)
    label: str = "m"

    async def run(self, experiment=None):
        self.events.append(self.label)


@dataclass
class Boom(Marker):
    async def run(self, experiment=None):
        self.events.append(self.label)
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_a_failed_task_pauses_the_queue_until_it_is_resumed():
    events = []
    manager = TaskManager()
    manager.add_task(Boom(events, "boom"))
    manager.add_task(Marker(events, "next"))
    runner = asyncio.create_task(manager.run(experiment=None))
    try:
        await until(lambda: events)
        await asyncio.sleep(0.4)

        assert events == ["boom"], "the task behind it must not start"
        state = manager.state()
        assert state["status"] == "Paused"
        assert state["last_result"] == {
            "name": "Boom",
            "outcome": "failed",
            "error": "RuntimeError: boom",
        }

        manager.resume()
        await until(lambda: len(events) == 2)
        assert events == ["boom", "next"]
        await until(lambda: manager.state()["last_result"]["outcome"] == "completed")
        assert manager.state()["status"] == "Running"
    finally:
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=3)


@pytest.mark.asyncio
async def test_a_task_that_completes_leaves_the_queue_running():
    events = []
    manager = TaskManager()
    manager.add_task(Marker(events, "one"))
    manager.add_task(Marker(events, "two"))
    runner = asyncio.create_task(manager.run(experiment=None))
    try:
        await until(lambda: len(events) == 2)
        assert manager.state()["status"] == "Running"
        assert manager.state()["last_result"]["outcome"] == "completed"
    finally:
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=3)


@pytest.mark.asyncio
async def test_an_aborted_task_is_reported_as_aborted():
    task = Sleeper()
    manager = TaskManager()
    manager.add_task(task)
    runner = asyncio.create_task(manager.run(experiment=None))
    try:
        await until(lambda: "run" in task.events)
        manager.abort()
        await until(lambda: manager.state()["last_result"] is not None)

        assert manager.state()["last_result"]["outcome"] == "aborted"
        assert task.events == ["setup", "run", "teardown"]
        assert manager.state()["status"] == "Paused"
    finally:
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=3)


@pytest.mark.asyncio
async def test_shutting_down_a_running_task_manager_tears_the_task_down():
    task = Sleeper()
    manager = TaskManager()
    manager.add_task(task)
    runner = asyncio.create_task(manager.run(experiment=None))
    await until(lambda: "run" in task.events)

    await manager.shutdown()
    await asyncio.wait_for(runner, timeout=3)

    assert task.events == ["setup", "run", "teardown"]
