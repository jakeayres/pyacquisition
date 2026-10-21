"""Tasks made wrongly, aborted at the wrong moment, or given what a form can't
show: each is refused with a message that says what to do, or handled, rather than
stopping the experiment, cutting a teardown short, or losing data."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment, Task
from pyacquisition.core.task_manager import task as task_module
from pyacquisition.core.task_manager.task_manager import TaskManager
from pyacquisition.tasks import PID, NewFile


@dataclass
class Steps(Task):
    """Takes a few steps."""

    count: int = 3

    async def run(self, experiment):
        for _ in range(self.count):
            await self.sleep(0.01)


@dataclass
class SlowTeardown(Task):
    """Takes three steps to leave things safe."""

    torn: list = field(default_factory=list)

    async def run(self, experiment):
        pass

    async def teardown(self, experiment):
        for step in range(3):
            await self.sleep(0.01)
            self.torn.append(step)


@dataclass
class NoSuper(Task):
    """Checks its inputs, but forgets `super().__post_init__()`."""

    points: int = 2

    def __post_init__(self):
        if self.points < 2:
            raise ValueError("Points must be 2 or more.")

    async def run(self, experiment):
        pass


def experiment_with_endpoints(tmp_path) -> Experiment:
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    api = experiment._api_server
    experiment._register_endpoints(api)
    for manager in experiment.task_managers.values():
        manager._register_endpoints(api)
    return experiment


# ------------------------------------------------------------------ checkpoint()
@pytest.mark.asyncio
async def test_a_checkpoint_gives_the_rest_a_turn_and_lets_a_pause_in():
    @dataclass
    class Busy(Task):
        done: int = 0

        async def run(self, experiment):
            for step in range(1000):
                self.done = step
                await self.checkpoint()

    busy = Busy()
    seen = []

    async def the_rest():  # the rack and the interface, taking their turns
        while True:
            seen.append(busy.done)
            await asyncio.sleep(0)

    rest = asyncio.create_task(the_rest())
    runner = asyncio.create_task(busy.start())
    while busy.done < 10:
        await asyncio.sleep(0)
    busy.pause()
    held = busy.done
    for _ in range(50):
        await asyncio.sleep(0)
    assert held < 100 and busy.done == held  # held mid-loop, where the pause came
    assert len(set(seen)) > 5  # the rest had turns while the loop ran
    busy.abort()
    await asyncio.wait_for(runner, 5)
    rest.cancel()
    assert busy.outcome == "aborted"


# ------------------------------------------------------- a subtask, as it ended
@pytest.mark.asyncio
async def test_a_subtask_is_logged_and_kept_as_it_ended(monkeypatch):
    logged = Mock()
    monkeypatch.setattr(task_module, "logger", logged)

    @dataclass
    class Fails(Task):
        async def run(self, experiment):
            raise RuntimeError("It broke.")

    @dataclass
    class Parent(Task):
        children: list = field(default_factory=lambda: [Fails(), Steps(count=1000)])

        async def run(self, experiment):
            try:
                await self.run_subtask(self.children[0])
            except RuntimeError:
                pass
            await self.run_subtask(self.children[1])

    parent = Parent()
    runner = asyncio.create_task(parent.start())
    await asyncio.sleep(0.1)
    parent.abort()
    await asyncio.wait_for(runner, 5)
    messages = [call.args[0] for call in logged.info.call_args_list]
    assert "[Fails] Subtask failed." in messages
    assert "[Steps] Subtask aborted." in messages
    assert not any(message.endswith("Subtask completed.") for message in messages)
    fails, steps = parent.children
    assert (fails.outcome, str(fails.failure)) == ("failed", "It broke.")
    assert steps.outcome == "aborted"


# --------------------------------------------- an abort during a teardown waits
@pytest.mark.asyncio
async def test_an_abort_during_a_teardown_lets_it_finish():
    task = SlowTeardown()
    runner = asyncio.create_task(task.start())
    while not task.torn:
        await asyncio.sleep(0.001)
    task.abort()
    await asyncio.wait_for(runner, 5)
    assert task.torn == [0, 1, 2]
    assert task.outcome == "completed"  # its run had ended before the abort


@pytest.mark.asyncio
async def test_an_abort_during_a_failed_task_s_teardown_keeps_its_failure():
    @dataclass
    class Fails(SlowTeardown):
        async def run(self, experiment):
            raise RuntimeError("It broke.")

    task = Fails()
    runner = asyncio.create_task(task.start())
    while not task.torn:
        await asyncio.sleep(0.001)
    task.abort()
    await asyncio.wait_for(runner, 5)
    assert task.torn == [0, 1, 2]
    assert (task.outcome, str(task.failure)) == ("failed", "It broke.")


@pytest.mark.asyncio
async def test_an_abort_during_a_subtask_s_teardown_stops_the_task_after_it():
    @dataclass
    class Parent(Task):
        child: SlowTeardown = field(default_factory=SlowTeardown)
        after: bool = False

        async def run(self, experiment):
            await self.run_subtask(self.child)
            self.after = True

    parent = Parent()
    runner = asyncio.create_task(parent.start())
    while not parent.child.torn:
        await asyncio.sleep(0.001)
    parent.abort()
    await asyncio.wait_for(runner, 5)
    assert parent.child.torn == [0, 1, 2]  # the subtask's teardown ran to its end
    assert parent.after is False  # and the task stopped there
    assert parent.outcome == "aborted"


@pytest.mark.asyncio
async def test_stopping_the_queue_during_a_teardown_lets_it_finish():
    manager = TaskManager()
    task = SlowTeardown()
    manager.add_task(task)
    loop = asyncio.create_task(manager.run(None))
    while not task.torn:
        await asyncio.sleep(0.001)
    await manager.shutdown()
    await asyncio.wait_for(loop, 5)
    assert task.torn == [0, 1, 2]


# ------------------------------------------------------------ made wrongly
def test_queueing_a_class_says_to_make_a_task():
    with pytest.raises(TypeError) as refused:
        TaskManager().add_task(Steps)
    assert str(refused.value) == "Steps is a class: give a task made from it, such as Steps()."


def test_queueing_something_else_is_refused():
    with pytest.raises(TypeError, match="isn't a task"):
        TaskManager().add_task("Steps")


def test_a_task_without_super_post_init_is_refused_as_it_is_queued():
    with pytest.raises(TypeError) as refused:
        TaskManager().add_task(NoSuper())
    assert str(refused.value) == "NoSuper.__post_init__() must call super().__post_init__() first."


def test_the_form_shows_why_a_task_without_super_post_init_is_refused(tmp_path):
    experiment = experiment_with_endpoints(tmp_path)
    experiment.register_task(NoSuper)
    answer = TestClient(experiment._api_server.app).get("/tasks/nosuper")
    assert answer.status_code == 422
    assert answer.json()["detail"] == "NoSuper.__post_init__() must call super().__post_init__() first."
    assert experiment.task_managers["main"].state()["queue"] == []


@pytest.mark.asyncio
async def test_a_subtask_given_as_a_class_fails_its_task_with_the_message():
    @dataclass
    class Parent(Task):
        async def run(self, experiment):
            await self.run_subtask(Steps)

    parent = Parent()
    await parent.start()
    assert parent.outcome == "failed"
    assert str(parent.failure) == "Steps is a class: give a task made from it, such as Steps()."


# --------------------------------------------------------------- one label each
def test_a_second_task_under_the_same_label_is_refused(tmp_path):
    experiment = experiment_with_endpoints(tmp_path)
    experiment.register_task(Steps, label="Quick", count=1)
    with pytest.raises(ValueError) as refused:
        experiment.register_task(Steps, label="Quick", count=5)
    assert str(refused.value) == (
        "A task is already registered as 'Quick' (/tasks/quick): give this one a label of its own."
    )
    # The refused one isn't kept for queues added later, which take the first
    experiment.add_task_manager("other")
    assert [kwargs for task, kwargs in experiment._shared_tasks if task is Steps] == [{"label": "Quick", "count": 1}]


def test_a_label_of_its_own_is_registered_beside_the_first(tmp_path):
    experiment = experiment_with_endpoints(tmp_path)
    experiment.register_task(Steps, label="Quick", count=1)
    experiment.register_task(Steps, label="Long", count=5)
    paths = TestClient(experiment._api_server.app).get("/openapi.json").json()["paths"]
    assert {"/tasks/quick", "/tasks/long"} <= set(paths)


# ------------------------------------------------- inputs a form can't ask for
def test_an_input_no_form_can_ask_for_must_be_given_as_it_is_registered(tmp_path):
    experiment = experiment_with_endpoints(tmp_path)
    with pytest.raises(TypeError) as refused:
        experiment.register_task(PID)
    assert str(refused.value) == (
        "PID's input `read` (Callable) can't be asked for in a form: give it as you "
        "register the task, as in register_task(PID, read=...)."
    )
    schema = TestClient(experiment._api_server.app).get("/openapi.json")
    assert schema.status_code == 200  # nothing half-registered breaks the forms


def test_given_as_it_is_registered_the_rest_are_asked_for(tmp_path):
    experiment = experiment_with_endpoints(tmp_path)
    experiment.register_task(PID, label="Hold", read=lambda: 1.0, write=lambda value: None)
    schema = TestClient(experiment._api_server.app).get("/openapi.json")
    assert schema.status_code == 200
    names = [p["name"] for p in schema.json()["paths"]["/tasks/hold"]["get"]["parameters"]]
    assert "setpoint" in names and "read" not in names and "write" not in names


def test_one_with_a_default_is_left_out_and_takes_it(tmp_path):
    @dataclass
    class Smooth(Task):
        """Smooths with a function of its own."""

        window: int = 5
        smoother: Callable = max

        async def run(self, experiment):
            pass

    experiment = experiment_with_endpoints(tmp_path)
    experiment.register_task(Smooth)
    client = TestClient(experiment._api_server.app)
    names = [p["name"] for p in client.get("/openapi.json").json()["paths"]["/tasks/smooth"]["get"]["parameters"]]
    assert names == ["window"]
    assert client.get("/tasks/smooth", params={"window": 3}).status_code == 200
    (queued,) = list(experiment.task_managers["main"]._task_queue._queue)
    assert (queued.window, queued.smoother) == (3, max)


# ------------------------------------------------------------- a file's title
@pytest.mark.parametrize("title, message", [
    ("0.5 V/run", "A title can't contain /: '0.5 V/run'."),
    ("a:b", "A title can't contain :: 'a:b'."),
    ("  ", "The title is empty: '  '."),
])
def test_new_file_refuses_a_title_that_can_t_be_a_file_s_name(title, message):
    with pytest.raises(ValueError) as refused:
        NewFile(file_name=title)
    assert str(refused.value) == message


def test_the_scribe_refuses_one_too_and_keeps_its_file(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    before = experiment._scribe.current_path()
    with pytest.raises(ValueError, match="A title can't contain /"):
        experiment._scribe.next_file("a/b")
    assert experiment._scribe.current_path() == before


def test_new_file_takes_a_title_with_spaces_and_dots():
    assert NewFile(file_name="0.5 V, sweep 2").file_name == "0.5 V, sweep 2"
