import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from pyacquisition import Task
from pyacquisition.core.task_manager.task_manager import TaskManager


@dataclass
class Recorder(Task):
    """Task that records when it starts and finishes."""

    label: str = "task"
    steps: int = 1
    log: list = field(default_factory=list)
    hook: Callable[[int], None] | None = None

    async def run(self, experiment=None):
        self.log.append(f"{self.label}:start")
        for i in range(self.steps):
            if self.hook:
                self.hook(i)
            yield None
        self.log.append(f"{self.label}:end")

    async def teardown(self, experiment=None):
        self.log.append(f"{self.label}:teardown")


async def stop(manager, runner):
    """Shut the manager down and wait for its run() loop to return."""
    await manager.shutdown()
    await asyncio.wait_for(runner, timeout=3)


@pytest.mark.asyncio
async def test_shutdown_stops_an_idle_task_manager():
    manager = TaskManager()
    runner = asyncio.create_task(manager.run(experiment=None))
    await asyncio.sleep(0.2)

    await stop(manager, runner)


@pytest.mark.asyncio
async def test_shutdown_stops_a_paused_task_manager():
    manager = TaskManager()
    manager.pause()
    runner = asyncio.create_task(manager.run(experiment=None))
    await asyncio.sleep(0.2)

    await stop(manager, runner)


@pytest.mark.asyncio
async def test_shutdown_stops_a_task_manager_paused_by_abort():
    log = []
    manager = TaskManager()
    first = Recorder("first", steps=50, log=log)
    first.hook = lambda i: manager.abort() if i == 1 else None
    manager.add_task(first)
    manager.add_task(Recorder("second", log=log))

    runner = asyncio.create_task(manager.run(experiment=None))
    await asyncio.sleep(0.5)  # first is aborted, and the manager is now paused

    await stop(manager, runner)
    assert "second:start" not in log


@pytest.mark.asyncio
async def test_tasks_run_one_at_a_time_in_order():
    log = []
    manager = TaskManager()
    manager.add_task(Recorder("a", log=log))
    manager.add_task(Recorder("b", log=log))
    runner = asyncio.create_task(manager.run(experiment=None))

    await asyncio.sleep(0.5)
    await stop(manager, runner)

    assert log == ["a:start", "a:end", "a:teardown", "b:start", "b:end", "b:teardown"]


@pytest.mark.asyncio
async def test_abort_stops_the_running_task_and_pauses_the_queue_until_resumed():
    log = []
    manager = TaskManager()
    first = Recorder("first", steps=50, log=log)
    first.hook = lambda i: manager.abort() if i == 1 else None
    manager.add_task(first)
    manager.add_task(Recorder("second", log=log))
    runner = asyncio.create_task(manager.run(experiment=None))

    await asyncio.sleep(0.5)
    assert log == ["first:start", "first:teardown"], "The aborted task tears down."
    assert not manager._pause_event.is_set(), "Abort pauses the task manager."

    manager.resume()
    await asyncio.sleep(0.5)
    assert log[2:] == ["second:start", "second:end", "second:teardown"]

    await stop(manager, runner)
