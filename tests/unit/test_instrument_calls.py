"""An instrument's query or command queued like a task (core/task_manager/
instrument_call.py): the endpoints on each task manager, running the call, its
value in the last result, and saving and loading it in a sequence."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment
from pyacquisition.core.instrument import BaseEnum, SoftwareInstrument, mark_command, mark_query
from pyacquisition.core.task_manager.instrument_call import InstrumentCall


class Mode(BaseEnum):
    FAST = ("f", "Fast mode")
    SLOW = ("s", "Slow mode")


class Probe(SoftwareInstrument):
    """A fake instrument: a query with an enum input, and a command."""

    name = "Probe"

    def __init__(self, uid):
        super().__init__(uid)
        self.sent = []

    @mark_query
    def read_level(self, channel: int = 1, mode: Mode = Mode.FAST) -> float:
        """Read a channel's level."""
        return channel * 10 + (0.5 if mode is Mode.SLOW else 0.0)

    @mark_command
    def set_level(self, level: float) -> None:
        """Set the level."""
        self.sent.append(level)


def make_experiment(tmp_path, *, probe=True, manager_first=False):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    if manager_first:
        experiment.add_task_manager("control")
    if probe:
        experiment.add_instrument(Probe("probe"))
    if not manager_first:
        experiment.add_task_manager("control")
    api = experiment._api_server
    experiment._register_endpoints(api)
    experiment._rack._register_endpoints(api)
    for manager in experiment._task_managers.values():
        manager._register_endpoints(api)
    experiment._register_instrument_calls()
    return experiment


@pytest.fixture
def experiment(tmp_path):
    return make_experiment(tmp_path)


@pytest.fixture
def client(experiment):
    return TestClient(experiment._api_server.app)


@pytest.fixture
def logged(monkeypatch):
    """What queued calls log."""
    messages = []
    original = InstrumentCall.log

    def log(self, message, level="info"):
        messages.append(message)
        original(self, message, level)

    monkeypatch.setattr(InstrumentCall, "log", log)
    return messages


def queue_of(experiment, manager="main"):
    return list(experiment._task_managers[manager]._task_queue._queue)


def run(experiment, task, manager="main"):
    """Runs a queued task as its task manager would, and gives its last result."""
    asyncio.run(task.start(experiment=experiment))
    task_manager = experiment._task_managers[manager]
    task_manager._finished(task)
    return task_manager.state()["last_result"]


# ------------------------------------------------------------ the endpoints
def test_a_query_is_queued_on_the_main_task_manager(experiment, client):
    response = client.get("/task_manager/call/probe/read_level", params={"channel": 2})

    assert response.status_code == 200
    assert response.json()["message"] == "probe.read_level queued"
    (task,) = queue_of(experiment)
    assert isinstance(task, InstrumentCall)
    assert (task.name, task.arguments) == ("probe.read_level", {"channel": 2, "mode": Mode.FAST})
    assert queue_of(experiment, "control") == []


def test_a_command_is_queued_on_another_task_manager(experiment, client):
    response = client.get("/managers/control/call/probe/set_level", params={"level": 4.5})

    assert response.status_code == 200
    (task,) = queue_of(experiment, "control")
    assert task.arguments == {"level": 4.5}
    assert queue_of(experiment) == []


def test_a_wrong_input_is_refused_and_nothing_is_queued(experiment, client):
    assert client.get("/task_manager/call/probe/read_level", params={"channel": "abc"}).status_code == 422
    assert client.get("/task_manager/call/probe/set_level").status_code == 422  # level is needed
    assert client.get("/task_manager/call/probe/read_level", params={"mode": "Warp"}).status_code == 422
    assert queue_of(experiment) == []


def test_the_queue_shows_the_call_with_its_inputs(experiment, client):
    client.get("/task_manager/call/probe/read_level", params={"channel": 3, "mode": "Slow mode"})

    (shown,) = experiment._task_managers["main"].state()["queue"]
    assert shown["name"] == "probe.read_level"
    assert shown["description"] == "probe.read_level(channel=3, mode=SLOW)"
    assert shown["parameters"] == {"channel": 3, "mode": "SLOW"}


@pytest.mark.parametrize("manager_first", [False, True])
def test_every_task_manager_gets_the_endpoints_whichever_is_added_first(tmp_path, manager_first):
    experiment = make_experiment(tmp_path, manager_first=manager_first)
    paths = TestClient(experiment._api_server.app).get("/openapi.json").json()["paths"]

    for prefix in ("/task_manager", "/managers/control"):
        for method in ("read_level", "set_level", "identify"):
            assert f"{prefix}/call/probe/{method}" in paths


def test_the_endpoints_are_neither_tasks_nor_the_instruments_own(client):
    paths = client.get("/openapi.json").json()["paths"]

    call = paths["/task_manager/call/probe/read_level"]["get"]
    assert call["tags"] == ["Task Manager"]
    assert paths["/managers/control/call/probe/set_level"]["get"]["tags"] == ["Task Manager: control"]
    assert not [p for p in paths if p.startswith("/tasks/") and "/call/" in p]
    # The Instruments tab lists the paths under /probe/: they are as they were.
    assert sorted(p for p in paths if p.startswith("/probe/")) == [
        "/probe/commands/",
        "/probe/identify",
        "/probe/queries/",
        "/probe/read_level",
        "/probe/set_level",
    ]
    # The form is the instrument's own: the same inputs.
    own = paths["/probe/read_level"]["get"]["parameters"]
    assert [p["name"] for p in call["parameters"]] == [p["name"] for p in own]


# ------------------------------------------------------------ running it
def test_a_queued_query_reads_logs_and_keeps_its_value(experiment, client, logged):
    client.get("/task_manager/call/probe/read_level", params={"channel": 2, "mode": "Slow mode"})
    (task,) = queue_of(experiment)

    result = run(experiment, task)

    assert result["name"] == "probe.read_level"
    assert result["outcome"] == "completed"
    assert result["value"] == 20.5
    assert any("probe.read_level(channel=2, mode=SLOW) → 20.5" in m for m in logged)


def test_a_queued_command_sends_and_logs(experiment, client, logged):
    client.get("/task_manager/call/probe/set_level", params={"level": 4.5})
    (task,) = queue_of(experiment)

    result = run(experiment, task)

    assert experiment.instruments["probe"].sent == [4.5]
    assert result["value"] is None
    assert any("probe.set_level(level=4.5) sent" in m for m in logged)


def test_a_task_that_reads_nothing_has_no_value(experiment):
    manager = experiment._task_managers["main"]

    class Plain:
        name = "Plain"
        outcome = "completed"
        failure = None

    manager._finished(Plain())

    assert manager.state()["last_result"]["value"] is None


# ------------------------------------------------------------ sequences
def test_a_queued_call_is_saved_and_loaded_again(experiment, client):
    client.get("/task_manager/call/probe/read_level", params={"channel": 3, "mode": "Slow mode"})
    manager = experiment._task_managers["main"]

    entries, skipped = manager.saveable()

    assert skipped == []
    assert entries == [
        {"task": "call:probe.read_level", "name": "probe.read_level",
         "parameters": {"channel": 3, "mode": "SLOW"}}
    ]
    manager._task_queue._queue.clear()
    assert manager.queue_saved(entries) == 1
    (task,) = queue_of(experiment)
    assert run(experiment, task)["value"] == 30.5  # the enum made again from its name


def test_a_call_whose_instrument_is_gone_cant_be_loaded(experiment, client, tmp_path):
    client.get("/task_manager/call/probe/set_level", params={"level": 1})
    entries, _ = experiment._task_managers["main"].saveable()
    elsewhere = make_experiment(tmp_path / "elsewhere", probe=False)

    with pytest.raises(ValueError, match="1. probe.set_level: can't be queued here"):
        elsewhere._task_managers["main"].queue_saved(entries)


def test_a_saved_call_with_an_input_it_no_longer_has_says_so(experiment):
    entries = [{"task": "call:probe.set_level", "name": "probe.set_level",
                "parameters": {"level": 1, "volume": 11}}]

    with pytest.raises(ValueError, match="probe.set_level takes no input called volume"):
        experiment._task_managers["main"].queue_saved(entries)


def test_a_duplicated_call_is_the_same_call(experiment, client):
    client.get("/task_manager/call/probe/set_level", params={"level": 2})
    manager = experiment._task_managers["main"]
    (task,) = queue_of(experiment)

    assert manager.duplicate_queued_task(task._id) is not None

    first, second = queue_of(experiment)
    assert (second.name, second.arguments) == (first.name, first.arguments)
    assert second._queued_with == first._queued_with
    assert second._id != first._id
