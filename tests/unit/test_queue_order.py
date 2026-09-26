"""Putting a queued task at a given place, and duplicating one (milestone 11)."""

import asyncio
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment, Task
from pyacquisition.core.task_manager.task_manager import TaskManager


@dataclass
class Hold(Task):
    """Hold the temperature."""

    kelvin: float = 4.2
    notes: list = field(default_factory=list)


@dataclass
class Counted(Task):
    """Keeps a count that isn't an input, set as it runs."""

    kelvin: float = 1.0
    count: int = field(default=0, init=False)


def manager_with(*kelvins):
    manager = TaskManager()
    for kelvin in kelvins:
        manager.add_task(Hold(kelvin))
    return manager


def kelvins(manager):
    return [task.kelvin for task in manager._task_queue._queue]


def ids(manager):
    return [task._id for task in manager._task_queue._queue]


# -------------------------------------------------------------- placing
@pytest.mark.parametrize(
    "start, to, order",
    [
        (0, 2, [2, 3, 1, 4, 5]),
        (4, 0, [5, 1, 2, 3, 4]),
        (1, 3, [1, 3, 4, 2, 5]),
        (3, 1, [1, 4, 2, 3, 5]),
    ],
)
def test_a_task_is_put_at_the_place_given(start, to, order):
    manager = manager_with(1, 2, 3, 4, 5)

    assert manager.place_queued_task(ids(manager)[start], to) is True
    assert kelvins(manager) == order


def test_a_place_past_either_end_is_that_end():
    manager = manager_with(1, 2, 3)

    manager.place_queued_task(ids(manager)[0], 99)
    assert kelvins(manager) == [2, 3, 1]
    manager.place_queued_task(ids(manager)[2], -5)
    assert kelvins(manager) == [1, 2, 3]


def test_a_task_already_there_is_not_moved():
    manager = manager_with(1, 2, 3)

    assert manager.place_queued_task(ids(manager)[1], 1) is False
    assert kelvins(manager) == [1, 2, 3]


def test_a_task_no_longer_queued_is_not_moved():
    manager = manager_with(1, 2)

    assert manager.place_queued_task("gone", 0) is False
    assert kelvins(manager) == [1, 2]


# -------------------------------------------------------------- duplicating
def test_a_copy_goes_straight_after_the_original():
    manager = manager_with(1, 2, 3)
    original = ids(manager)[1]

    copy = manager.duplicate_queued_task(original)

    assert kelvins(manager) == [1, 2, 2, 3]
    assert ids(manager)[2] == copy
    assert copy != original  # a task of its own


def test_a_copy_is_a_separate_task_with_the_same_inputs():
    manager = manager_with(1)
    (original,) = manager._task_queue._queue

    manager.duplicate_queued_task(original._id)

    first, second = manager._task_queue._queue
    assert second is not first
    assert second == first  # dataclass equality: the same inputs
    assert second.kelvin == 1


def test_a_copy_of_the_running_task_runs_next():
    manager = manager_with(1, 2)
    running = Hold(9)
    manager._current_task = running

    manager.duplicate_queued_task(running._id)

    assert kelvins(manager) == [9, 1, 2]


def test_a_task_no_longer_queued_is_not_copied():
    manager = manager_with(1)

    assert manager.duplicate_queued_task("gone") is None
    assert kelvins(manager) == [1]


def test_what_is_not_an_input_starts_afresh_in_the_copy():
    manager = TaskManager()
    original = Counted(kelvin=3)
    original.count = 5
    manager.add_task(original)

    manager.duplicate_queued_task(original._id)

    copy = manager._task_queue._queue[1]
    assert (copy.kelvin, copy.count) == (3, 0)


# -------------------------------------------------------------- the endpoints
@pytest.fixture
def served(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    manager = experiment.add_task_manager("control")
    for task_manager in experiment.task_managers.values():
        task_manager._register_endpoints(experiment._api_server)
    return experiment, manager, TestClient(experiment._api_server.app)


def test_placing_through_the_api(served):
    experiment, manager, client = served
    for kelvin in (1, 2, 3):
        manager.add_task(Hold(kelvin))

    response = client.get(
        "/managers/control/place_queued_task",
        params={"task_id": ids(manager)[2], "index": 0},
    )

    assert response.json()["moved"] is True
    assert kelvins(manager) == [3, 1, 2]


def test_duplicating_through_the_api(served):
    experiment, manager, client = served
    experiment._task_manager.add_task(Hold(7))
    main = experiment._task_manager

    response = client.get("/task_manager/duplicate_queued_task", params={"task_id": ids(main)[0]})

    assert response.json()["id"] == ids(main)[1]
    assert kelvins(main) == [7, 7]


def test_a_task_that_cannot_be_copied_is_a_clear_error(served, monkeypatch):
    experiment, _, client = served
    experiment._task_manager.add_task(Hold(1))

    def refuse(task_id):
        raise TypeError("it has no inputs to copy")

    monkeypatch.setattr(experiment._task_manager, "duplicate_queued_task", refuse)

    response = client.get(
        "/task_manager/duplicate_queued_task",
        params={"task_id": ids(experiment._task_manager)[0]},
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith("That task can't be copied")


def test_the_order_shown_is_the_order_they_run_in(tmp_path):
    """After placing and duplicating, the tasks run in the order the queue shows."""
    ran = []

    @dataclass
    class Note(Task):
        """Notes that it ran."""

        label: str = ""

        async def run(self, experiment=None):
            ran.append(self.label)

    async def scenario():
        manager = TaskManager()
        for label in "abcde":
            manager.add_task(Note(label))
        queue = manager._task_queue._queue
        manager.place_queued_task(queue[4]._id, 0)  # e a b c d
        manager.duplicate_queued_task(queue[2]._id)  # e a b b c d
        manager.place_queued_task(queue[5]._id, 1)  # e d a b b c
        shown = [t.label for t in queue]
        runner = asyncio.create_task(manager.run(experiment=None))
        while len(ran) < 6:
            await asyncio.sleep(0.01)
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=2)
        return shown

    shown = asyncio.run(scenario())
    assert shown == list("edabbc")
    assert ran == shown


def test_a_task_queued_while_paused_waits_until_resumed():
    """Pausing an idle task manager must hold the next task queued, even though
    its loop was already waiting on the queue when it was paused."""
    started = []

    @dataclass
    class Note(Task):
        """Notes that it started."""

        async def run(self, experiment=None):
            started.append(True)

    async def scenario():
        manager = TaskManager()
        runner = asyncio.create_task(manager.run(experiment=None))
        await asyncio.sleep(0.05)  # waiting on the queue now
        manager.pause()
        manager.add_task(Note())
        await asyncio.sleep(0.4)
        held = (list(started), len(manager._task_queue._queue), manager.current_task())
        manager.resume()
        for _ in range(100):
            if started:
                break
            await asyncio.sleep(0.01)
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=2)
        return held

    held = asyncio.run(scenario())
    assert held == ([], 1, None)
    assert started == [True]
