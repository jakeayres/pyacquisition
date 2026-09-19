"""An experiment with several task managers, each running its own queue."""

import asyncio
from dataclasses import dataclass, field
from unittest.mock import ANY

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment, Measurement, Task
from pyacquisition.core.task_manager.task_manager import TaskManager
from pyacquisition.instruments.software import Clock

LONG = 10_000  # far more steps than any test lets a task reach


@dataclass
class Hold(Task):
    """Hold the temperature."""

    kelvin: float = 4.2


@dataclass
class Ticker(Task):
    """Takes a step every 50 ms, and records its lifecycle in a shared log."""

    label: str = "t"
    count: int = 3
    log: list = field(default_factory=list)

    async def setup(self, experiment=None):
        self.log.append(f"{self.label}:setup")

    async def run(self, experiment=None):
        for i in range(self.count):
            self.log.append(f"{self.label}:{i}")
            yield None
            await asyncio.sleep(0.05)

    async def teardown(self, experiment=None):
        self.log.append(f"{self.label}:teardown")


@pytest.fixture
def experiment(tmp_path):
    return Experiment(root_path=str(tmp_path), gui=False)


def serve(experiment):
    """Registers the endpoints as running the experiment does, and returns a client."""
    for task_manager in experiment.task_managers.values():
        task_manager._register_endpoints(experiment._api_server)
    experiment._register_endpoints(experiment._api_server)
    return TestClient(experiment._api_server.app)


def paths(experiment):
    return set(experiment._api_server.app.openapi()["paths"])


# ---------------------------------------------------------------------------
# The Python API
# ---------------------------------------------------------------------------


def test_there_is_always_a_main_task_manager(experiment):
    assert list(experiment.task_managers) == ["main"]
    assert experiment.task_managers["main"] is experiment._task_manager


def test_add_task_manager_returns_it_and_lists_it(experiment):
    control = experiment.add_task_manager("control")

    assert isinstance(control, TaskManager)
    assert control.name == "control"
    assert experiment.task_managers["control"] is control
    assert list(experiment.task_managers) == ["main", "control"]


def test_task_managers_are_independent_objects(experiment):
    control = experiment.add_task_manager("control")
    other = experiment.add_task_manager("other")

    assert control is not other
    assert control is not experiment.task_managers["main"]
    assert control._task_queue is not other._task_queue


def test_the_view_is_read_only(experiment):
    with pytest.raises(TypeError):
        experiment.task_managers["x"] = TaskManager("x")


@pytest.mark.parametrize("name", ["", "a b", "a/b", "../x", "control!", None, 5])
def test_invalid_names_are_rejected(experiment, name):
    with pytest.raises(ValueError):
        experiment.add_task_manager(name)
    assert list(experiment.task_managers) == ["main"]


@pytest.mark.parametrize("name", ["main", "control"])
def test_a_name_cannot_be_used_twice(experiment, name):
    experiment.add_task_manager("control")
    with pytest.raises(ValueError):
        experiment.add_task_manager(name)


def test_register_task_on_an_unknown_manager_is_rejected(experiment):
    with pytest.raises(ValueError, match="add_task_manager"):
        experiment.register_task(Hold, manager="nope")


STANDARD = ["newfile", "waitfor", "waituntil"]


def test_every_task_manager_can_queue_the_standard_tasks(experiment):
    experiment.add_task_manager("control")
    found = paths(experiment)

    for name in STANDARD:
        assert f"/tasks/{name}" in found
        assert f"/managers/control/tasks/{name}" in found


def test_a_registered_task_can_be_queued_on_every_task_manager(experiment):
    experiment.add_task_manager("control")
    experiment.register_task(Hold)  # after the task manager was added
    found = paths(experiment)

    assert "/tasks/hold" in found
    assert "/managers/control/tasks/hold" in found


def test_a_task_manager_added_later_gets_the_tasks_already_registered(experiment):
    experiment.register_task(Hold, label="Hold Temperature")  # before it was added
    experiment.add_task_manager("control")
    found = paths(experiment)

    assert "/managers/control/tasks/hold_temperature" in found
    assert "/managers/control/tasks/newfile" in found


def test_a_task_can_be_limited_to_one_task_manager(experiment):
    experiment.add_task_manager("control")
    experiment.add_task_manager("other")
    experiment.register_task(Hold, manager="control")
    found = paths(experiment)

    assert "/managers/control/tasks/hold" in found
    assert "/tasks/hold" not in found
    assert "/managers/other/tasks/hold" not in found


def test_a_task_can_be_limited_to_several_task_managers(experiment):
    experiment.add_task_manager("control")
    experiment.add_task_manager("other")
    experiment.register_task(Hold, manager=["main", "other"])
    found = paths(experiment)

    assert "/tasks/hold" in found
    assert "/managers/other/tasks/hold" in found
    assert "/managers/control/tasks/hold" not in found


def test_a_limited_task_is_not_given_to_task_managers_added_later(experiment):
    experiment.register_task(Hold, manager="main")
    experiment.add_task_manager("control")

    assert "/managers/control/tasks/hold" not in paths(experiment)


def test_nothing_is_registered_if_one_of_the_names_is_unknown(experiment):
    experiment.add_task_manager("control")
    with pytest.raises(ValueError, match="nope"):
        experiment.register_task(Hold, manager=["control", "nope"])
    assert "/managers/control/tasks/hold" not in paths(experiment)


# ---------------------------------------------------------------------------
# The endpoints
# ---------------------------------------------------------------------------


def test_the_main_manager_keeps_its_original_paths(experiment):
    serve(experiment)
    found = paths(experiment)

    for name in [
        "pause",
        "resume",
        "abort",
        "remove_task",
        "clear_tasks",
        "status",
        "current_task",
        "task_list",
    ]:
        assert f"/task_manager/{name}" in found
    assert not any(p.startswith("/managers/main") for p in found)


def test_another_manager_gets_its_own_paths(experiment):
    experiment.add_task_manager("control")
    experiment.register_task(Hold, manager="control", label="Hold Temperature")
    serve(experiment)
    found = paths(experiment)

    for name in [
        "pause",
        "resume",
        "abort",
        "remove_task",
        "clear_tasks",
        "status",
        "current_task",
        "task_list",
    ]:
        assert f"/managers/control/{name}" in found
    assert "/managers/control/tasks/hold_temperature" in found
    assert "/tasks/hold_temperature" not in found, "It must not appear on the main one."


def test_the_other_managers_do_not_use_the_prefixes_the_gui_reads(experiment):
    """The GUI lists every path that starts with /task_manager or /tasks."""
    experiment.add_task_manager("control")
    experiment.register_task(Hold, manager="control")
    serve(experiment)

    extra = [p for p in paths(experiment) if p.startswith("/managers/")]
    assert extra
    assert not any(p.startswith(("/task_manager", "/tasks")) for p in extra)


def test_task_managers_can_be_listed(experiment):
    experiment.add_task_manager("control")
    client = serve(experiment)

    assert client.get("/managers").json() == {
        "status": 200,
        "data": ["main", "control"],
    }


def test_the_state_of_every_task_manager_is_available_in_one_call(experiment):
    control = experiment.add_task_manager("control")
    control.add_task(Hold())
    client = serve(experiment)
    client.get("/managers/control/pause")

    response = client.get("/managers/state").json()

    assert response["status"] == 200
    assert list(response["data"]) == ["main", "control"]
    assert response["data"]["main"] == {
        "status": "Running",
        "current_task": None,
        "aborting": False,
        "queue": [],
    }
    assert response["data"]["control"] == {
        "status": "Paused",
        "current_task": None,
        "aborting": False,
        "queue": [{"id": ANY, "name": "Hold", "description": None, "parameters": None}],
    }


@pytest.mark.asyncio
async def test_the_state_shows_the_running_task_and_the_queue_behind_it():
    log = []
    manager = TaskManager("control")
    manager.add_task(Ticker("first", LONG, log))
    manager.add_task(Ticker("second", 1, log))
    assert manager.state()["current_task"] is None, "Nothing is running yet."
    runner = asyncio.create_task(manager.run(experiment=None))
    try:
        await asyncio.sleep(0.3)

        state = manager.state()
        assert state["status"] == "Running"
        assert state["current_task"] == {
            "id": ANY,
            "name": "Ticker",
            "description": None,
            "parameters": None,
        }
        assert [task["name"] for task in state["queue"]] == ["Ticker"], (
            "The running task is not in the queue."
        )
    finally:
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=3)


@dataclass
class SlowSteps(Task):
    """Takes half a second over each step, so an abort takes a while to land."""

    async def run(self, experiment=None):
        while True:
            yield None
            await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_the_state_says_when_the_running_task_is_being_aborted():
    manager = TaskManager("control")
    manager.add_task(SlowSteps())
    runner = asyncio.create_task(manager.run(experiment=None))
    try:
        await asyncio.sleep(0.2)
        assert manager.state()["aborting"] is False, "It is running normally."

        manager.abort()  # the task is told to stop, and finishes at its next step

        state = manager.state()
        assert state["aborting"] is True
        assert state["current_task"]["name"] == "SlowSteps", "It has not ended yet."
        assert state["status"] == "Paused", "Abort also pauses the task manager."

        await asyncio.sleep(1.0)
        state = manager.state()
        assert state["current_task"] is None
        assert state["aborting"] is False, "Nothing is being aborted any more."
    finally:
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=3)


def test_nothing_is_being_aborted_when_nothing_is_running():
    assert TaskManager().state()["aborting"] is False


@dataclass
class Described(Task):
    """A task that shows its description and some parameters."""

    shown: object = None

    @property
    def description(self):
        return "Does a thing"

    @property
    def parameters(self):
        return self.shown


@pytest.mark.parametrize(
    "shown, expected",
    [
        (
            {"a": 1, "b": "x", "c": 2.5, "d": True, "e": None},
            {"a": 1, "b": "x", "c": 2.5, "d": True, "e": None},
        ),
        ({"nan": float("nan"), "inf": float("inf")}, {"nan": "nan", "inf": "inf"}),
        ({"object": [1, 2]}, {"object": "[1, 2]"}),
        (None, None),
    ],
)
def test_parameters_are_made_safe_to_send(shown, expected):
    manager = TaskManager()
    manager.add_task(Described(shown=shown))

    assert manager.state()["queue"] == [
        {
            "id": ANY,
            "name": "Described",
            "description": "Does a thing",
            "parameters": expected,
        }
    ]


def test_a_nan_parameter_does_not_stop_the_state_being_sent(experiment):
    """nan is not valid JSON, so it would otherwise make the whole response fail."""
    experiment._task_manager.add_task(Described(shown={"value": float("nan")}))
    client = serve(experiment)

    response = client.get("/managers/state")

    assert response.status_code == 200
    assert response.json()["data"]["main"]["queue"][0]["parameters"] == {"value": "nan"}


def test_a_task_that_cannot_describe_itself_does_not_hide_the_others():
    @dataclass
    class Broken(Task):
        @property
        def parameters(self):
            raise RuntimeError("no parameters for you")

    manager = TaskManager()
    manager.add_task(Broken())
    manager.add_task(Described(shown={"a": 1}))

    queue = manager.state()["queue"]

    assert queue[0] == {
        "id": ANY,
        "name": "Broken",
        "description": None,
        "parameters": None,
    }
    assert queue[1]["parameters"] == {"a": 1}


# ---------------------------------------------------------------------------
# Removing one task from a queue
# ---------------------------------------------------------------------------


def test_every_task_has_an_id_of_its_own():
    a, b = Hold(), Hold()

    assert a == b, (
        "Tasks with the same inputs are equal, so equality cannot tell them apart."
    )
    assert a._id != b._id


def test_the_state_carries_the_id_of_each_task():
    manager = TaskManager()
    first, second = Hold(kelvin=1.0), Hold(kelvin=2.0)
    manager.add_task(first)
    manager.add_task(second)

    assert [task["id"] for task in manager.state()["queue"]] == [first._id, second._id]


def test_removing_by_id_removes_that_task_and_keeps_the_order():
    manager = TaskManager()
    a, b, c = Hold(kelvin=1.0), Hold(kelvin=2.0), Hold(kelvin=3.0)
    for task in (a, b, c):
        manager.add_task(task)

    assert manager.remove_queued_task(b._id) is True

    assert [task._id for task in manager._task_queue._queue] == [a._id, c._id]


def test_two_equal_tasks_are_told_apart_by_id():
    manager = TaskManager()
    first, second = Hold(), Hold()
    manager.add_task(first)
    manager.add_task(second)

    manager.remove_queued_task(second._id)

    (remaining,) = manager._task_queue._queue
    assert remaining is first


def test_removing_a_task_that_is_not_queued_changes_nothing():
    manager = TaskManager()
    a = Hold()
    manager.add_task(a)

    assert manager.remove_queued_task("not an id") is False
    assert manager.remove_queued_task(Hold()._id) is False

    assert list(manager._task_queue._queue) == [a]


def test_a_task_can_only_be_removed_once():
    manager = TaskManager()
    task = Hold()
    manager.add_task(task)

    assert manager.remove_queued_task(task._id) is True
    assert manager.remove_queued_task(task._id) is False


@pytest.mark.asyncio
async def test_removing_by_id_is_not_fooled_by_the_queue_moving_on():
    """The interface shows the queue as it was a moment ago. By then the task at the
    front may have started, so a position would now point at the wrong task."""
    log = []
    manager = TaskManager()
    running = Ticker("running", LONG, log)
    b, c = Ticker("b", 1, log), Ticker("c", 1, log)
    for task in (running, b, c):
        manager.add_task(task)
    seen_by_the_interface = [running._id, b._id, c._id]  # b was at position 1
    runner = asyncio.create_task(manager.run(experiment=None))
    try:
        await asyncio.sleep(0.3)  # `running` has started, so the queue is now [b, c]

        manager.remove_queued_task(seen_by_the_interface[1])

        assert [task._id for task in manager._task_queue._queue] == [c._id], (
            "b should be gone. Position 1 is now c, which is what would have gone."
        )
    finally:
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=3)


@pytest.mark.asyncio
async def test_a_task_that_is_running_cannot_be_removed_from_the_queue():
    log = []
    manager = TaskManager()
    running = Ticker("running", LONG, log)
    manager.add_task(running)
    runner = asyncio.create_task(manager.run(experiment=None))
    try:
        await asyncio.sleep(0.3)

        assert manager.remove_queued_task(running._id) is False

        assert manager.state()["current_task"]["id"] == running._id
        assert "running:teardown" not in log, "It must carry on."
    finally:
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=3)


def test_the_endpoint_removes_a_task_by_id(experiment):
    control = experiment.add_task_manager("control")
    keep, remove = Hold(kelvin=1.0), Hold(kelvin=2.0)
    control.add_task(keep)
    control.add_task(remove)
    client = serve(experiment)

    response = client.get(
        "/managers/control/remove_queued_task", params={"task_id": remove._id}
    )

    assert response.status_code == 200
    assert response.json()["removed"] is True
    assert list(control._task_queue._queue) == [keep]


def test_the_endpoint_removes_from_the_main_manager_at_its_original_path(experiment):
    task = Hold()
    experiment._task_manager.add_task(task)
    client = serve(experiment)

    response = client.get(
        "/task_manager/remove_queued_task", params={"task_id": task._id}
    )

    assert response.json()["removed"] is True
    assert experiment._task_manager._task_queue.empty()


def test_the_endpoint_only_touches_the_task_manager_it_was_sent_to(experiment):
    control = experiment.add_task_manager("control")
    main_task, control_task = Hold(), Hold()
    experiment._task_manager.add_task(main_task)
    control.add_task(control_task)
    client = serve(experiment)

    client.get(
        "/managers/control/remove_queued_task", params={"task_id": main_task._id}
    )

    assert list(experiment._task_manager._task_queue._queue) == [main_task]
    assert list(control._task_queue._queue) == [control_task]


def test_the_endpoint_says_when_the_task_is_no_longer_queued(experiment):
    client = serve(experiment)

    response = client.get(
        "/task_manager/remove_queued_task", params={"task_id": "gone"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["removed"] is False
    assert "no longer" in body["message"]


def test_the_endpoint_needs_a_task_id(experiment):
    client = serve(experiment)
    assert client.get("/task_manager/remove_queued_task").status_code == 422


def test_the_endpoint_is_hidden_so_it_is_not_an_entry_in_the_menu(experiment):
    experiment.add_task_manager("control")
    serve(experiment)

    found = paths(experiment)

    assert "/task_manager/remove_queued_task" not in found
    assert "/managers/control/remove_queued_task" not in found
    assert "/task_manager/remove_task" in found, (
        "The removal by position is still there."
    )


# ---------------------------------------------------------------------------
# Moving a task along a queue
# ---------------------------------------------------------------------------


def queued(*tasks):
    manager = TaskManager()
    for task in tasks:
        manager.add_task(task)
    return manager


def order(manager):
    return [task._id for task in manager._task_queue._queue]


def test_a_task_can_be_moved_up_and_down():
    a, b, c = Hold(kelvin=1.0), Hold(kelvin=2.0), Hold(kelvin=3.0)
    manager = queued(a, b, c)

    assert manager.move_queued_task(b._id, "up") is True
    assert order(manager) == [b._id, a._id, c._id]

    assert manager.move_queued_task(b._id, "down") is True
    assert order(manager) == [a._id, b._id, c._id]

    assert manager.move_queued_task(a._id, "down") is True
    assert order(manager) == [b._id, a._id, c._id]


def test_moving_a_task_leaves_the_others_in_order():
    tasks = [Hold(kelvin=float(i)) for i in range(5)]
    manager = queued(*tasks)

    manager.move_queued_task(tasks[2]._id, "up")

    expected = [tasks[0], tasks[2], tasks[1], tasks[3], tasks[4]]
    assert order(manager) == [t._id for t in expected]


def test_the_first_task_cannot_move_up_into_the_running_tasks_place():
    a, b = Hold(kelvin=1.0), Hold(kelvin=2.0)
    manager = queued(a, b)

    assert manager.move_queued_task(a._id, "up") is False

    assert order(manager) == [a._id, b._id]


def test_the_last_task_cannot_move_down():
    a, b = Hold(kelvin=1.0), Hold(kelvin=2.0)
    manager = queued(a, b)

    assert manager.move_queued_task(b._id, "down") is False

    assert order(manager) == [a._id, b._id]


def test_a_task_on_its_own_cannot_move_either_way():
    only = Hold()
    manager = queued(only)

    assert manager.move_queued_task(only._id, "up") is False
    assert manager.move_queued_task(only._id, "down") is False
    assert order(manager) == [only._id]


def test_a_task_moved_up_again_and_again_stops_at_the_front():
    tasks = [Hold(kelvin=float(i)) for i in range(4)]
    manager = queued(*tasks)

    results = [manager.move_queued_task(tasks[3]._id, "up") for _ in range(6)]

    assert results == [True, True, True, False, False, False]
    assert order(manager)[0] == tasks[3]._id


def test_a_task_that_is_not_queued_cannot_be_moved():
    a = Hold()
    manager = queued(a)

    assert manager.move_queued_task("not an id", "down") is False
    assert order(manager) == [a._id]


def test_an_unknown_direction_is_rejected_and_changes_nothing():
    a, b = Hold(kelvin=1.0), Hold(kelvin=2.0)
    manager = queued(a, b)

    with pytest.raises(ValueError):
        manager.move_queued_task(a._id, "sideways")

    assert order(manager) == [a._id, b._id]


def test_equal_tasks_are_told_apart_when_moving():
    first, second = Hold(), Hold()
    assert first == second
    manager = queued(first, second)

    manager.move_queued_task(second._id, "up")

    assert manager._task_queue._queue[0] is second
    assert manager._task_queue._queue[1] is first


@pytest.mark.asyncio
async def test_moving_by_id_is_not_fooled_by_the_queue_moving_on():
    """The interface saw [running, b, c, d], with c at position 2. By the time it
    asks, `running` has started, so position 2 is d. Moving by id is still right."""
    log = []
    running = Ticker("running", LONG, log)
    b, c, d = Ticker("b", 1, log), Ticker("c", 1, log), Ticker("d", 1, log)
    manager = queued(running, b, c, d)
    runner = asyncio.create_task(manager.run(experiment=None))
    try:
        await asyncio.sleep(0.3)  # `running` has started, so the queue is [b, c, d]

        manager.move_queued_task(c._id, "up")

        assert order(manager) == [c._id, b._id, d._id]
    finally:
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=3)


@pytest.mark.asyncio
async def test_the_running_task_cannot_be_moved():
    log = []
    running, waiting = Ticker("running", LONG, log), Ticker("waiting", 1, log)
    manager = queued(running, waiting)
    runner = asyncio.create_task(manager.run(experiment=None))
    try:
        await asyncio.sleep(0.3)

        assert manager.move_queued_task(running._id, "down") is False

        assert manager.state()["current_task"]["id"] == running._id
        assert order(manager) == [waiting._id]
    finally:
        await manager.shutdown()
        await asyncio.wait_for(runner, timeout=3)


def move(client, path, task, direction):
    return client.get(path, params={"task_id": task._id, "direction": direction})


def test_the_endpoint_moves_a_task(experiment):
    control = experiment.add_task_manager("control")
    a, b = Hold(kelvin=1.0), Hold(kelvin=2.0)
    control.add_task(a)
    control.add_task(b)
    client = serve(experiment)

    response = move(client, "/managers/control/move_queued_task", b, "up")

    assert response.status_code == 200
    assert response.json()["moved"] is True
    assert order(control) == [b._id, a._id]


def test_the_endpoint_moves_a_task_in_the_main_manager_at_its_original_path(experiment):
    a, b = Hold(kelvin=1.0), Hold(kelvin=2.0)
    experiment._task_manager.add_task(a)
    experiment._task_manager.add_task(b)
    client = serve(experiment)

    move(client, "/task_manager/move_queued_task", a, "down")

    assert order(experiment._task_manager) == [b._id, a._id]


def test_the_endpoint_only_touches_the_task_manager_it_was_sent_to(experiment):
    control = experiment.add_task_manager("control")
    m1, m2 = Hold(kelvin=1.0), Hold(kelvin=2.0)
    experiment._task_manager.add_task(m1)
    experiment._task_manager.add_task(m2)
    control.add_task(Hold())
    client = serve(experiment)

    move(client, "/managers/control/move_queued_task", m2, "up")

    assert order(experiment._task_manager) == [m1._id, m2._id], "That task is on main."


def test_the_endpoint_says_when_a_task_could_not_be_moved(experiment):
    only = Hold()
    experiment._task_manager.add_task(only)
    client = serve(experiment)

    at_the_end = move(client, "/task_manager/move_queued_task", only, "up").json()
    unknown = client.get(
        "/task_manager/move_queued_task", params={"task_id": "gone", "direction": "up"}
    ).json()

    assert at_the_end["moved"] is False and unknown["moved"] is False
    assert "could not" in at_the_end["message"]


@pytest.mark.parametrize("direction", ["sideways", "", "UP"])
def test_the_endpoint_rejects_an_unknown_direction(experiment, direction):
    task = Hold()
    experiment._task_manager.add_task(task)
    client = serve(experiment)

    response = move(client, "/task_manager/move_queued_task", task, direction)

    assert response.status_code == 422


def test_the_endpoint_needs_a_task_id_and_a_direction(experiment):
    client = serve(experiment)
    assert client.get("/task_manager/move_queued_task").status_code == 422
    partial = client.get("/task_manager/move_queued_task", params={"task_id": "x"})
    assert partial.status_code == 422


def test_moving_is_hidden_so_it_is_not_an_entry_in_the_menu(experiment):
    experiment.add_task_manager("control")
    serve(experiment)

    found = paths(experiment)

    assert "/task_manager/move_queued_task" not in found
    assert "/managers/control/move_queued_task" not in found


def test_registering_a_task_on_a_manager_queues_it_there_only(experiment):
    control = experiment.add_task_manager("control")
    experiment.register_task(Hold, manager="control")
    client = serve(experiment)

    response = client.get("/managers/control/tasks/hold", params={"kelvin": "5"})

    assert response.json() == {"status": 200, "message": "Hold added"}
    assert list(control._task_queue._queue) == [Hold(kelvin=5.0)]
    assert experiment._task_manager._task_queue.empty()
    assert client.get("/managers/control/task_list").json()["data"] == [
        {"name": "Hold", "description": None, "parameters": None}
    ]
    assert client.get("/task_manager/task_list").json()["data"] == []


def test_a_registered_task_is_queued_on_the_task_manager_it_was_sent_to(experiment):
    control = experiment.add_task_manager("control")
    experiment.register_task(Hold)
    client = serve(experiment)

    params = {"kelvin": "1"}  # the endpoints require every input, defaults or not
    assert client.get("/tasks/hold", params=params).status_code == 200
    assert client.get("/managers/control/tasks/hold", params=params).status_code == 200
    assert client.get("/managers/control/tasks/hold", params=params).status_code == 200

    assert experiment._task_manager._task_queue.qsize() == 1
    assert control._task_queue.qsize() == 2


def test_control_endpoints_only_affect_their_own_manager(experiment):
    control = experiment.add_task_manager("control")
    client = serve(experiment)

    client.get("/managers/control/pause")

    assert client.get("/managers/control/status").json()["data"] == "Paused"
    assert client.get("/task_manager/status").json()["data"] == "Running"
    assert not control._pause_event.is_set()
    assert experiment._task_manager._pause_event.is_set()

    client.get("/managers/control/resume")
    assert client.get("/managers/control/status").json()["data"] == "Running"


def test_clearing_one_queue_leaves_the_other(experiment):
    control = experiment.add_task_manager("control")
    control.add_task(Hold())
    experiment._task_manager.add_task(Hold())
    client = serve(experiment)

    client.get("/managers/control/clear_tasks")

    assert control._task_queue.empty()
    assert experiment._task_manager._task_queue.qsize() == 1


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_managers_run_their_queues_at_the_same_time(tmp_path):
    """A task that never ends must not hold up the main queue, and is stopped
    when the experiment shuts down."""
    log = []

    class TwoQueues(Experiment):
        def setup(self):
            clock = Clock("clock")
            self.add_instrument(clock)
            self.add_measurement(Measurement("time", clock.timestamp_ms))

            control = self.add_task_manager("control")
            control.add_task(Ticker("control", LONG, log))
            self.task_managers["main"].add_task(Ticker("first", 6, log))
            self.task_managers["main"].add_task(Ticker("second", 3, log))

    experiment = TwoQueues(
        root_path=str(tmp_path),
        api_server_port=8126,
        measurement_period=0.05,
        gui=False,
    )

    async def stop_when_the_main_queue_is_done():
        for _ in range(400):  # up to 20 s, however slow the machine is
            if "second:teardown" in log:
                break
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.3)  # the endless task carries on for a while longer
        experiment._shutdown_event.set()

    await asyncio.wait_for(
        asyncio.gather(experiment._run(), stop_when_the_main_queue_is_done()),
        timeout=40,
    )

    assert "second:teardown" in log, "The main queue should not be held up."
    assert log.index("first:teardown") < log.index("second:setup"), "One at a time."
    assert log.index("control:1") < log.index("first:teardown"), "At the same time."
    assert "control:teardown" in log, "Shutting down should stop the endless task."
    control_steps = [e for e in log if e.startswith("control:") and e[8:].isdigit()]
    assert len(control_steps) > 6, "It should have kept going after the main queue."
