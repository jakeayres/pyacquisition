import asyncio
import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pyacquisition import Task

task_module = importlib.import_module("pyacquisition.core.task_manager.task")


def test_task_name():
    class ExampleTask(Task):
        pass

    task = ExampleTask()
    assert task.name == "ExampleTask", "The name property should return the class name."


@pytest.mark.asyncio
async def test_task_pause_resume():
    class ExampleTask(Task):
        async def run(self, experiment=None):
            yield "Step 1"
            yield "Step 2"

    task = ExampleTask()
    task.pause()
    assert not task._pause_event.is_set(), "Task should be paused."
    task.resume()
    assert task._pause_event.is_set(), "Task should be resumed."


@pytest.mark.asyncio
async def test_task_abort():
    class ExampleTask(Task):
        async def run(self, experiment=None):
            yield "Step 1"

    task = ExampleTask()
    task.abort()
    assert task._abort_event.is_set(), "Task should be aborted."
    assert task._pause_event.is_set(), "Pause event should be set when aborted."


@pytest.mark.asyncio
async def test_task_start():
    class ExampleTask(Task):
        async def setup(self, experiment=None):
            self.setup_called = True

        async def run(self, experiment=None):
            yield "Running step"

        async def teardown(self, experiment=None):
            self.teardown_called = True

    task = ExampleTask()
    task.setup_called = False
    task.teardown_called = False
    await task.start()
    assert task.setup_called, "Setup should be called during start."
    assert task.teardown_called, "Teardown should be called after start."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def spin(cycles: int = 50):
    """Give other tasks on the event loop a chance to run, without real waiting."""
    for _ in range(cycles):
        await asyncio.sleep(0)


def steps_of(log: list, label: str) -> list:
    """The 'label:<n>' step entries in a shared log (excludes setup/teardown)."""
    return [
        entry
        for entry in log
        if entry.startswith(f"{label}:") and entry.split(":")[1].isdigit()
    ]


@dataclass
class Recorder(Task):
    """Leaf task that records its lifecycle in a shared log.

    `hook` is called with the step index each time a step is produced, so a test
    can pause or abort from *inside* the task at a precise point.
    """

    label: str = "task"
    steps: int = 2
    log: list = field(default_factory=list)
    hook: Callable[[int], None] | None = None

    async def setup(self, experiment=None):
        self.log.append(f"{self.label}:setup")

    async def run(self, experiment=None):
        self.experiment_seen = experiment
        for i in range(self.steps):
            self.log.append(f"{self.label}:{i}")
            if self.hook:
                self.hook(i)
            yield f"{self.label} step {i}"

    async def teardown(self, experiment=None):
        self.log.append(f"{self.label}:teardown")


@dataclass
class Failing(Recorder):
    """Recorder that raises after producing its steps."""

    async def run(self, experiment=None):
        async for step in super().run(experiment=experiment):
            yield step
        raise RuntimeError("boom")


@dataclass
class Composite(Task):
    """Runs its children one after another, each through run_subtask()."""

    label: str = "comp"
    children: list = field(default_factory=list)
    log: list = field(default_factory=list)

    async def setup(self, experiment=None):
        self.log.append(f"{self.label}:setup")

    async def run(self, experiment=None):
        for child in self.children:
            await self.run_subtask(child)
            yield None

    async def teardown(self, experiment=None):
        self.log.append(f"{self.label}:teardown")


# ---------------------------------------------------------------------------
# Base Task: state and display
# ---------------------------------------------------------------------------


def test_task_initial_state():
    task = Task()
    assert task._pause_event.is_set(), "A new task should not be paused."
    assert not task._abort_event.is_set(), "A new task should not be aborted."
    assert task._is_paused is False
    assert task._status == "running"


def test_description_and_parameters_default_to_none():
    task = Task()
    assert task.description is None
    assert task.parameters is None


def test_display_dict_defaults():
    class ExampleTask(Task):
        pass

    assert ExampleTask().display_dict() == {
        "name": "ExampleTask",
        "description": None,
        "parameters": None,
    }


def test_display_dict_uses_overridden_description_and_parameters():
    @dataclass
    class MoveStage(Task):
        position: float = 1.5

        @property
        def description(self):
            return f"Move to {self.position}"

        @property
        def parameters(self):
            return {"position": self.position}

    assert MoveStage(position=2.0).display_dict() == {
        "name": "MoveStage",
        "description": "Move to 2.0",
        "parameters": {"position": 2.0},
    }


@pytest.mark.asyncio
async def test_run_must_be_overridden():
    with pytest.raises(NotImplementedError):
        await Task().run()


# ---------------------------------------------------------------------------
# Base Task: start() lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_runs_setup_steps_and_teardown_in_order():
    task = Recorder(label="r", steps=3)
    await task.start()
    assert task.log == ["r:setup", "r:0", "r:1", "r:2", "r:teardown"]


@pytest.mark.asyncio
async def test_start_passes_experiment_to_all_hooks():
    seen = {}

    class ExampleTask(Task):
        async def setup(self, experiment=None):
            seen["setup"] = experiment

        async def run(self, experiment=None):
            seen["run"] = experiment
            yield "step"

        async def teardown(self, experiment=None):
            seen["teardown"] = experiment

    experiment = object()
    await ExampleTask().start(experiment=experiment)
    assert seen == {"setup": experiment, "run": experiment, "teardown": experiment}


@pytest.mark.asyncio
async def test_start_logs_steps_but_not_empty_steps(monkeypatch):
    class ExampleTask(Task):
        async def run(self, experiment=None):
            yield "one"
            yield None
            yield "two"

    mock_logger = Mock()
    monkeypatch.setattr(task_module, "logger", mock_logger)

    await ExampleTask().start()

    messages = [call.args[0] for call in mock_logger.info.call_args_list]
    assert messages == [
        "[ExampleTask] Starting task.",
        "[ExampleTask] one",
        "[ExampleTask] two",
        "[ExampleTask] Task completed.",
    ]


@pytest.mark.asyncio
async def test_error_in_run_is_contained_and_teardown_still_runs():
    task = Failing(label="bad", steps=1)
    await task.start()  # must not raise
    assert task.log == ["bad:setup", "bad:0", "bad:teardown"]


@pytest.mark.asyncio
async def test_error_in_setup_skips_run_but_runs_teardown():
    class ExampleTask(Recorder):
        async def setup(self, experiment=None):
            raise RuntimeError("setup failed")

    task = ExampleTask(label="r")
    await task.start()  # must not raise
    assert task.log == ["r:teardown"], "run() must not start after a failed setup."


@pytest.mark.asyncio
async def test_start_without_run_override_does_not_raise():
    class ExampleTask(Task):
        async def teardown(self, experiment=None):
            self.torn_down = True

    task = ExampleTask()
    await task.start()
    assert task.torn_down


# ---------------------------------------------------------------------------
# Base Task: pause / resume / abort while running
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_abort_from_within_run_stops_after_current_step():
    task = Recorder(label="r", steps=5)
    task.hook = lambda i: task.abort() if i == 1 else None

    await task.start()

    assert task.log == ["r:setup", "r:0", "r:1", "r:teardown"]


@pytest.mark.asyncio
async def test_pause_blocks_between_steps_until_resumed():
    task = Recorder(label="r", steps=3)
    task.pause()

    running = asyncio.create_task(task.start())
    await spin()

    assert task.log == ["r:setup", "r:0"], "Only the first step runs before the pause."
    assert not running.done(), "The task should be waiting while paused."

    task.resume()
    await asyncio.wait_for(running, timeout=1)
    assert task.log == ["r:setup", "r:0", "r:1", "r:2", "r:teardown"]


@pytest.mark.asyncio
async def test_abort_while_paused_unblocks_and_stops():
    task = Recorder(label="r", steps=3)
    task.pause()

    running = asyncio.create_task(task.start())
    await spin()
    assert not running.done()

    task.abort()
    await asyncio.wait_for(running, timeout=1)

    assert task.log == ["r:setup", "r:0", "r:teardown"]


@pytest.mark.asyncio
async def test_task_can_be_restarted_after_abort():
    task = Recorder(label="r", steps=3)
    task.hook = lambda i: task.abort()
    await task.start()
    assert steps_of(task.log, "r") == ["r:0"]

    task.hook = None
    task.log.clear()
    await task.start()

    assert task.log == ["r:setup", "r:0", "r:1", "r:2", "r:teardown"]


# ---------------------------------------------------------------------------
# API endpoint registration
# ---------------------------------------------------------------------------


@dataclass
class MoveStage(Task):
    """Move the stage to a position.

    A longer description that is not shown.
    """

    position: float = 1.5
    steps: int = 3
    enabled: bool = False
    axis: str = "x"


def make_experiment():
    app = FastAPI()
    experiment = SimpleNamespace(
        _api_server=SimpleNamespace(app=app), _task_manager=Mock()
    )
    return experiment, app


def query_parameters(app, path):
    operation = app.openapi()["paths"][path]["get"]
    return {p["name"]: p["schema"]["type"] for p in operation.get("parameters", [])}


def test_register_endpoints_uses_lowercased_class_name_as_path():
    experiment, app = make_experiment()
    MoveStage.register_endpoints(experiment)
    assert list(app.openapi()["paths"]) == ["/tasks/movestage"]


def test_register_endpoints_label_sets_path():
    experiment, app = make_experiment()
    MoveStage.register_endpoints(experiment, label="Move The Stage")
    assert list(app.openapi()["paths"]) == ["/tasks/move_the_stage"]


def test_register_endpoints_exposes_fields_as_typed_query_parameters():
    experiment, app = make_experiment()
    MoveStage.register_endpoints(experiment)
    assert query_parameters(app, "/tasks/movestage") == {
        "position": "number",
        "steps": "integer",
        "enabled": "boolean",
        "axis": "string",
    }


def test_register_endpoints_uses_first_docstring_line_as_description():
    experiment, app = make_experiment()
    MoveStage.register_endpoints(experiment)
    operation = app.openapi()["paths"]["/tasks/movestage"]["get"]
    assert operation["description"] == "Move the stage to a position."


def test_register_endpoints_hides_fixed_kwargs():
    experiment, app = make_experiment()
    MoveStage.register_endpoints(experiment, axis="y")
    assert set(query_parameters(app, "/tasks/movestage")) == {
        "position",
        "steps",
        "enabled",
    }


def test_calling_endpoint_queues_task_with_converted_arguments():
    experiment, app = make_experiment()
    MoveStage.register_endpoints(experiment, axis="y")

    response = TestClient(app).get(
        "/tasks/movestage",
        params={"position": "2.5", "steps": "4", "enabled": "true"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 200, "message": "MoveStage added"}
    experiment._task_manager.add_task.assert_called_once()
    queued = experiment._task_manager.add_task.call_args.args[0]
    assert isinstance(queued, MoveStage)
    assert queued == MoveStage(position=2.5, steps=4, enabled=True, axis="y")


def test_each_endpoint_call_queues_a_new_task_instance():
    experiment, app = make_experiment()
    MoveStage.register_endpoints(experiment)
    client = TestClient(app)
    params = {"position": "1", "steps": "1", "enabled": "false", "axis": "x"}

    client.get("/tasks/movestage", params=params)
    client.get("/tasks/movestage", params=params)

    calls = experiment._task_manager.add_task.call_args_list
    assert calls[0].args[0] is not calls[1].args[0]


# ---------------------------------------------------------------------------
# Composition: run_subtask()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subtask_runs_full_lifecycle_in_order():
    log = []
    parent = Composite(children=[Recorder("a", 2, log), Recorder("b", 1, log)], log=log)

    await parent.start()

    assert log == [
        "comp:setup",
        "a:setup",
        "a:0",
        "a:1",
        "a:teardown",
        "b:setup",
        "b:0",
        "b:teardown",
        "comp:teardown",
    ]


@pytest.mark.asyncio
async def test_subtasks_can_be_nested():
    log = []
    inner = Composite(label="inner", children=[Recorder("x", 1, log)], log=log)
    outer = Composite(label="outer", children=[Recorder("a", 1, log), inner], log=log)

    await outer.start()

    assert log == [
        "outer:setup",
        "a:setup",
        "a:0",
        "a:teardown",
        "inner:setup",
        "x:setup",
        "x:0",
        "x:teardown",
        "inner:teardown",
        "outer:teardown",
    ]


@pytest.mark.asyncio
async def test_subtask_receives_the_experiment_the_parent_was_started_with():
    log = []
    child = Recorder("a", 1, log)
    experiment = object()

    await Composite(children=[child], log=log).start(experiment=experiment)

    assert child.experiment_seen is experiment


@pytest.mark.asyncio
async def test_subtask_experiment_can_be_given_explicitly():
    child = Recorder("a", 1)
    explicit = object()

    class ExampleTask(Task):
        async def run(self, experiment=None):
            await self.run_subtask(child, explicit)
            yield None

    await ExampleTask().start(experiment=object())

    assert child.experiment_seen is explicit


@pytest.mark.asyncio
async def test_subtask_steps_are_logged_under_the_subtasks_name(monkeypatch):
    mock_logger = Mock()
    monkeypatch.setattr(task_module, "logger", mock_logger)

    await Composite(children=[Recorder("a", 1)]).start()

    messages = [call.args[0] for call in mock_logger.info.call_args_list]
    assert "[Recorder] Starting subtask of [Composite]." in messages
    assert "[Recorder] a step 0" in messages
    assert "[Recorder] Subtask completed." in messages


@pytest.mark.asyncio
async def test_subtask_is_not_left_active_after_it_finishes():
    child = Recorder("a", 1)
    parent = Composite(children=[child])

    await parent.start()
    parent.pause()  # must not reach the finished subtask

    assert parent._active_subtask is None
    assert child._pause_event.is_set()


@pytest.mark.asyncio
async def test_a_previously_aborted_subtask_can_be_run():
    log = []
    child = Recorder("a", 2, log)
    child.abort()

    await Composite(children=[child], log=log).start()

    assert steps_of(log, "a") == ["a:0", "a:1"]


# --- abort ---


@pytest.mark.asyncio
async def test_aborting_parent_stops_running_subtask_and_skips_the_rest():
    log = []
    parent = Composite(log=log)
    parent.children = [
        Recorder("a", 50, log, hook=lambda i: parent.abort() if i == 1 else None),
        Recorder("b", 3, log),
    ]

    await asyncio.wait_for(parent.start(), timeout=5)

    assert log == [
        "comp:setup",
        "a:setup",
        "a:0",
        "a:1",
        "a:teardown",  # the subtask still cleans up
        "comp:teardown",
    ]


@pytest.mark.asyncio
async def test_aborting_parent_stops_nested_subtask():
    log = []
    inner = Composite(label="inner", log=log)
    outer = Composite(label="outer", children=[inner], log=log)
    inner.children = [
        Recorder("x", 50, log, hook=lambda i: outer.abort() if i == 1 else None)
    ]

    await asyncio.wait_for(outer.start(), timeout=5)

    assert log == [
        "outer:setup",
        "inner:setup",
        "x:setup",
        "x:0",
        "x:1",
        "x:teardown",
        "inner:teardown",
        "outer:teardown",
    ]


@pytest.mark.asyncio
async def test_aborting_a_subtask_directly_aborts_the_parent():
    log = []
    child = Recorder("a", 5, log)
    child.hook = lambda i: child.abort() if i == 0 else None

    await Composite(children=[child, Recorder("b", 3, log)], log=log).start()

    assert log == ["comp:setup", "a:setup", "a:0", "a:teardown", "comp:teardown"]


@pytest.mark.asyncio
async def test_subtask_does_not_begin_if_parent_is_already_aborted():
    child = Recorder("a", 2)

    class ExampleTask(Task):
        async def run(self, experiment=None):
            self.abort()
            await self.run_subtask(child)
            yield "unreachable"

    await ExampleTask().start()

    assert child.log == []


# --- pause ---


@pytest.mark.asyncio
async def test_pausing_parent_holds_running_subtask_until_resumed():
    log = []
    parent = Composite(log=log)
    parent.children = [
        Recorder("a", 4, log, hook=lambda i: parent.pause() if i == 1 else None)
    ]

    running = asyncio.create_task(parent.start())
    await spin()

    assert steps_of(log, "a") == ["a:0", "a:1"]
    assert not running.done()

    parent.resume()
    await asyncio.wait_for(running, timeout=1)
    assert steps_of(log, "a") == ["a:0", "a:1", "a:2", "a:3"]
    assert log[-2:] == ["a:teardown", "comp:teardown"]


@pytest.mark.asyncio
async def test_pausing_parent_holds_nested_subtask_until_resumed():
    log = []
    inner = Composite(label="inner", log=log)
    outer = Composite(label="outer", children=[inner], log=log)
    inner.children = [
        Recorder("x", 4, log, hook=lambda i: outer.pause() if i == 1 else None)
    ]

    running = asyncio.create_task(outer.start())
    await spin()

    assert steps_of(log, "x") == ["x:0", "x:1"]
    assert not running.done()

    outer.resume()
    await asyncio.wait_for(running, timeout=1)
    assert steps_of(log, "x") == ["x:0", "x:1", "x:2", "x:3"]


@pytest.mark.asyncio
async def test_subtask_does_not_begin_while_parent_is_paused():
    log = []
    parent = Composite(children=[Recorder("a", 1, log)], log=log)
    parent.pause()

    running = asyncio.create_task(parent.start())
    await spin()

    assert log == ["comp:setup"]
    assert not running.done()

    parent.resume()
    await asyncio.wait_for(running, timeout=1)
    assert log == ["comp:setup", "a:setup", "a:0", "a:teardown", "comp:teardown"]


@pytest.mark.asyncio
async def test_aborting_a_paused_parent_stops_running_subtask():
    log = []
    parent = Composite(log=log)
    parent.children = [
        Recorder("a", 50, log, hook=lambda i: parent.pause() if i == 1 else None)
    ]

    running = asyncio.create_task(parent.start())
    await spin()
    assert not running.done()

    parent.abort()
    await asyncio.wait_for(running, timeout=1)

    assert steps_of(log, "a") == ["a:0", "a:1"], "No further steps after the abort."
    assert log[-2:] == ["a:teardown", "comp:teardown"]


# --- errors ---


@pytest.mark.asyncio
async def test_subtask_error_stops_parent_but_subtask_still_tears_down():
    log = []
    parent = Composite(
        children=[Failing("bad", 1, log), Recorder("after", 1, log)], log=log
    )

    await parent.start()  # start() contains the error

    assert log == [
        "comp:setup",
        "bad:setup",
        "bad:0",
        "bad:teardown",
        "comp:teardown",
    ]


@pytest.mark.asyncio
async def test_subtask_setup_error_still_tears_down_and_stops_parent():
    log = []

    class SetupFails(Recorder):
        async def setup(self, experiment=None):
            raise RuntimeError("setup failed")

    parent = Composite(
        children=[SetupFails("bad", 1, log), Recorder("after", 1, log)], log=log
    )

    await parent.start()

    assert log == ["comp:setup", "bad:teardown", "comp:teardown"]


@pytest.mark.asyncio
async def test_parent_can_catch_a_subtask_error_and_carry_on():
    log = []
    failing = Failing("bad", 1, log)
    after = Recorder("after", 1, log)

    class Recovers(Task):
        async def run(self, experiment=None):
            try:
                await self.run_subtask(failing)
            except RuntimeError:
                self.recovered = True
            await self.run_subtask(after)
            yield None

    task = Recovers()
    await task.start()

    assert task.recovered
    assert log == [
        "bad:setup",
        "bad:0",
        "bad:teardown",
        "after:setup",
        "after:0",
        "after:teardown",
    ]
