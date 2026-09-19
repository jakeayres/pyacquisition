"""Running subtasks at the same time: run_subtasks() and alongside()."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from pyacquisition import Task

LONG = 10_000  # far more steps than any test lets a task reach


async def spin(cycles: int = 50):
    """Give other tasks on the event loop a chance to run, without real waiting."""
    for _ in range(cycles):
        await asyncio.sleep(0)


def steps(log: list, label: str) -> int:
    """How many steps of `label` are in a shared log."""
    return len(
        [e for e in log if e.startswith(f"{label}:") and e.split(":")[1].isdigit()]
    )


@dataclass
class Ticker(Task):
    """A leaf task that awaits between steps, so that tasks really take turns.

    `hook` is called with the step index, so a test can pause, abort or fail from
    inside the task at a precise point. `fail_at` raises an error at that step.
    """

    label: str = "t"
    count: int = 3
    log: list = field(default_factory=list)
    hook: Callable[[int], None] | None = None
    fail_at: int | None = None

    async def setup(self, experiment=None):
        self.log.append(f"{self.label}:setup")

    async def run(self, experiment=None):
        for i in range(self.count):
            self.log.append(f"{self.label}:{i}")
            if self.hook:
                self.hook(i)
            if self.fail_at == i:
                raise RuntimeError(f"{self.label} boom")
            yield None
            await asyncio.sleep(0)

    async def teardown(self, experiment=None):
        self.log.append(f"{self.label}:teardown")


@dataclass
class Nest(Task):
    """Runs one child through run_subtask(), to add a level of nesting."""

    child: Task = None

    async def run(self, experiment=None):
        await self.run_subtask(self.child)
        yield None


def start(task):
    return asyncio.create_task(task.start())


# ---------------------------------------------------------------------------
# run_subtasks()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_subtasks_runs_all_of_them_at_the_same_time():
    log = []
    a, b = Ticker("a", 3, log), Ticker("b", 3, log)

    class Together(Task):
        async def run(self, experiment=None):
            await self.run_subtasks(a, b)
            yield None

    parent = Together()
    await asyncio.wait_for(parent.start(), timeout=5)

    assert steps(log, "a") == 3 and steps(log, "b") == 3
    assert "a:teardown" in log and "b:teardown" in log
    assert log.index("b:0") < log.index("a:2"), "They should take turns."
    assert parent._active_subtasks == []


@pytest.mark.asyncio
async def test_run_subtasks_with_nothing_to_run_returns():
    class Together(Task):
        async def run(self, experiment=None):
            await self.run_subtasks()
            self.done = True
            yield None

    parent = Together()
    await asyncio.wait_for(parent.start(), timeout=5)
    assert parent.done


@pytest.mark.asyncio
async def test_run_subtasks_gives_the_subtasks_the_experiment():
    experiment = object()
    seen = []

    class Sees(Task):
        async def run(self, experiment=None):
            seen.append(experiment)
            yield None

    class Together(Task):
        async def run(self, experiment=None):
            await self.run_subtasks(Sees(), Sees())
            yield None

    await Together().start(experiment=experiment)
    assert seen == [experiment, experiment]


@pytest.mark.asyncio
async def test_run_subtasks_rejects_the_same_task_twice():
    child = Ticker("a")
    errors = []

    class Together(Task):
        async def run(self, experiment=None):
            try:
                await self.run_subtasks(child, child)
            except ValueError as e:
                errors.append(e)
            yield None

    parent = Together()
    await asyncio.wait_for(parent.start(), timeout=5)

    assert len(errors) == 1
    assert child.log == [], "Nothing should have started."
    assert parent._active_subtasks == []


@pytest.mark.asyncio
async def test_tasks_that_are_equal_but_not_the_same_can_run_together():
    """Tasks are dataclasses, so two with the same fields compare equal."""
    log = []
    a, b = Ticker("x", 3, log), Ticker("x", 3, log)
    assert a == b and a is not b

    class Together(Task):
        async def run(self, experiment=None):
            await self.run_subtasks(a, b)
            yield None

    parent = Together()
    await asyncio.wait_for(parent.start(), timeout=5)

    assert steps(log, "x") == 6
    assert parent._active_subtasks == []


@pytest.mark.asyncio
async def test_run_subtasks_does_not_begin_if_parent_is_already_aborted():
    child = Ticker("a")

    class Together(Task):
        async def run(self, experiment=None):
            self.abort()
            await self.run_subtasks(child)
            yield "unreachable"

    await Together().start()
    assert child.log == []


# --- failure ---


@pytest.mark.asyncio
async def test_an_error_in_one_subtask_stops_the_others_and_is_raised():
    log = []
    bad = Ticker("bad", 5, log, fail_at=1)
    long = Ticker("long", LONG, log)
    caught = []

    class Together(Task):
        async def run(self, experiment=None):
            try:
                await self.run_subtasks(bad, long)
            except RuntimeError as e:
                caught.append(e)
            yield None

        async def teardown(self, experiment=None):
            log.append("parent:teardown")

    parent = Together()
    await asyncio.wait_for(parent.start(), timeout=5)

    assert [str(e) for e in caught] == ["bad boom"]
    assert steps(log, "long") < 20, "The other subtask should have been stopped."
    assert "bad:teardown" in log and "long:teardown" in log
    assert log[-1] == "parent:teardown"
    assert parent._active_subtasks == []

    stopped_at = steps(log, "long")
    await spin()
    assert steps(log, "long") == stopped_at, "Nothing should still be running."


@pytest.mark.asyncio
async def test_aborting_one_subtask_directly_aborts_the_parent_and_the_others():
    log = []
    a = Ticker("a", LONG, log)
    a.hook = lambda i: a.abort() if i == 1 else None
    long = Ticker("long", LONG, log)
    reached = []

    class Together(Task):
        async def run(self, experiment=None):
            await self.run_subtasks(a, long)
            reached.append("after")
            yield None

    parent = Together()
    await asyncio.wait_for(parent.start(), timeout=5)

    assert reached == [], "The rest of run() should be skipped."
    assert steps(log, "a") == 2
    assert steps(log, "long") < 20
    assert "a:teardown" in log and "long:teardown" in log
    assert parent._active_subtasks == []


@pytest.mark.asyncio
async def test_the_parent_can_carry_on_after_an_error_in_run_subtasks():
    log = []
    after = Ticker("after", 2, log)

    class Recovers(Task):
        async def run(self, experiment=None):
            try:
                await self.run_subtasks(
                    Ticker("bad", 5, log, fail_at=0), Ticker("x", LONG, log)
                )
            except RuntimeError:
                pass
            await self.run_subtask(after)
            yield None

    await asyncio.wait_for(Recovers().start(), timeout=5)
    assert steps(log, "after") == 2


# --- abort and pause ---


@pytest.mark.asyncio
async def test_aborting_the_parent_stops_every_subtask():
    log = []
    a, b = Ticker("a", LONG, log), Ticker("b", LONG, log)

    class Together(Task):
        async def run(self, experiment=None):
            await self.run_subtasks(a, b)
            yield None

    parent = Together()
    running = start(parent)
    await spin()
    parent.abort()
    await asyncio.wait_for(running, timeout=5)

    assert "a:teardown" in log and "b:teardown" in log
    assert parent._active_subtasks == []
    a_steps, b_steps = steps(log, "a"), steps(log, "b")
    await spin()
    assert (steps(log, "a"), steps(log, "b")) == (a_steps, b_steps)


@pytest.mark.asyncio
async def test_pausing_the_parent_pauses_every_subtask_until_resumed():
    log = []
    a, b = Ticker("a", LONG, log), Ticker("b", LONG, log)

    class Together(Task):
        async def run(self, experiment=None):
            await self.run_subtasks(a, b)
            yield None

    parent = Together()
    running = start(parent)
    await spin()

    parent.pause()
    await spin()
    held = (steps(log, "a"), steps(log, "b"))
    await spin()
    assert (steps(log, "a"), steps(log, "b")) == held, "Both should be held."

    parent.resume()
    await spin()
    assert steps(log, "a") > held[0] and steps(log, "b") > held[1]

    parent.abort()
    await asyncio.wait_for(running, timeout=5)


@pytest.mark.asyncio
async def test_pause_and_abort_reach_subtasks_nested_under_parallel_ones():
    """Every branch must be reached, not only the one that started last."""
    log = []
    branches = [Nest(child=Ticker(label, LONG, log)) for label in ("x", "y")]

    class Together(Task):
        async def run(self, experiment=None):
            await self.run_subtasks(*branches)
            yield None

    parent = Together()
    running = start(parent)
    await spin()

    parent.pause()
    await spin()
    held = (steps(log, "x"), steps(log, "y"))
    await spin()
    assert (steps(log, "x"), steps(log, "y")) == held, "Both should be held."

    parent.resume()
    await spin()
    assert steps(log, "x") > held[0] and steps(log, "y") > held[1]

    parent.abort()
    await asyncio.wait_for(running, timeout=5)

    assert "x:teardown" in log and "y:teardown" in log
    stopped = (steps(log, "x"), steps(log, "y"))
    await spin()
    assert (steps(log, "x"), steps(log, "y")) == stopped, (
        "Nothing should be left running."
    )
    assert parent._active_subtasks == []


# ---------------------------------------------------------------------------
# alongside()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alongside_runs_in_the_background_and_stops_when_the_block_ends():
    log = []
    background = Ticker("bg", LONG, log)

    class Runs(Task):
        async def run(self, experiment=None):
            async with self.alongside(background):
                await self.run_subtask(Ticker("main", 5, log))
                yield None
            log.append("after")
            yield None

    parent = Runs()
    await asyncio.wait_for(parent.start(), timeout=5)

    assert steps(log, "bg") > 0, "It should have run during the block."
    assert log.index("bg:0") < log.index("main:4")
    assert steps(log, "bg") < 100, "It should have been stopped."
    assert log.index("bg:teardown") < log.index("after"), "The block waits for it."
    assert parent._active_subtasks == []

    stopped = steps(log, "bg")
    await spin()
    assert steps(log, "bg") == stopped


@pytest.mark.asyncio
async def test_alongside_stops_the_background_even_if_the_block_ends_at_once():
    log = []
    background = Ticker("bg", LONG, log)

    class Runs(Task):
        async def run(self, experiment=None):
            async with self.alongside(background):
                pass
            yield None

    await asyncio.wait_for(Runs().start(), timeout=5)
    assert "bg:setup" in log and log[-1] == "bg:teardown"


@pytest.mark.asyncio
async def test_alongside_can_run_several_and_stops_all_of_them():
    log = []

    class Runs(Task):
        async def run(self, experiment=None):
            async with self.alongside(Ticker("p", LONG, log), Ticker("q", LONG, log)):
                await self.run_subtask(Ticker("main", 3, log))
                yield None

    parent = Runs()
    await asyncio.wait_for(parent.start(), timeout=5)
    assert "p:teardown" in log and "q:teardown" in log
    assert parent._active_subtasks == []


@pytest.mark.asyncio
async def test_alongside_rejects_a_task_that_is_already_running():
    child = Ticker("a")
    errors = []

    class Runs(Task):
        async def run(self, experiment=None):
            async with self.alongside(child):
                try:
                    async with self.alongside(child):
                        pass
                except ValueError as e:
                    errors.append(e)
                yield None

    await asyncio.wait_for(Runs().start(), timeout=5)
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_aborting_a_background_task_directly_stops_only_that_one():
    log = []
    background = Ticker("bg", LONG, log)
    background.hook = lambda i: background.abort() if i == 1 else None
    reached = []

    class Runs(Task):
        async def run(self, experiment=None):
            async with self.alongside(background):
                await self.run_subtask(Ticker("main", 30, log))
                yield None
            reached.append("after")

    await asyncio.wait_for(Runs().start(), timeout=5)

    assert steps(log, "bg") == 2
    assert "bg:teardown" in log
    assert steps(log, "main") == 30, "The block should have carried on."
    assert reached == ["after"]


@pytest.mark.asyncio
async def test_an_error_in_a_background_task_interrupts_the_block_and_is_raised():
    log = []
    caught = []

    class Runs(Task):
        async def run(self, experiment=None):
            try:
                async with self.alongside(Ticker("bg", 5, log, fail_at=2)):
                    await self.run_subtask(Ticker("main", LONG, log))
                    yield "unreachable"
            except RuntimeError as e:
                caught.append(e)
            await self.run_subtask(Ticker("after", 2, log))  # the parent carries on
            yield None

    parent = Runs()
    await asyncio.wait_for(parent.start(), timeout=5)

    assert [str(e) for e in caught] == ["bg boom"]
    assert steps(log, "main") < 50, "The block should have been interrupted."
    assert "main:teardown" in log and "bg:teardown" in log
    assert steps(log, "after") == 2, "The failure must not leave the parent aborted."
    assert parent._active_subtasks == []


@pytest.mark.asyncio
async def test_an_unhandled_background_error_stops_the_parent():
    log = []

    class Runs(Task):
        async def run(self, experiment=None):
            async with self.alongside(Ticker("bg", 5, log, fail_at=1)):
                await self.run_subtask(Ticker("main", LONG, log))
                yield None
            log.append("after")

        async def teardown(self, experiment=None):
            log.append("parent:teardown")

    await asyncio.wait_for(Runs().start(), timeout=5)  # start() contains the error

    assert "after" not in log
    assert "main:teardown" in log and log[-1] == "parent:teardown"


@pytest.mark.asyncio
async def test_aborting_the_parent_stops_the_background_and_the_block():
    log = []

    class Runs(Task):
        async def run(self, experiment=None):
            async with self.alongside(Ticker("bg", LONG, log)):
                await self.run_subtask(Ticker("main", LONG, log))
                yield None
            log.append("after")

    parent = Runs()
    running = start(parent)
    await spin()
    parent.abort()
    await asyncio.wait_for(running, timeout=5)

    assert "bg:teardown" in log and "main:teardown" in log
    assert "after" not in log
    stopped = (steps(log, "bg"), steps(log, "main"))
    await spin()
    assert (steps(log, "bg"), steps(log, "main")) == stopped
    assert parent._active_subtasks == []


@pytest.mark.asyncio
async def test_pausing_the_parent_pauses_the_background_until_resumed():
    log = []

    class Runs(Task):
        async def run(self, experiment=None):
            async with self.alongside(Ticker("bg", LONG, log)):
                await self.run_subtask(Ticker("main", LONG, log))
                yield None

    parent = Runs()
    running = start(parent)
    await spin()

    parent.pause()
    await spin()
    held = steps(log, "bg")
    await spin()
    assert steps(log, "bg") == held

    parent.resume()
    await spin()
    assert steps(log, "bg") > held

    parent.abort()
    await asyncio.wait_for(running, timeout=5)
