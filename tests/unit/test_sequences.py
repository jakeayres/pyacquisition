"""Saving a queue as a sequence, and loading it again, in this run or the next
(milestone 13)."""

import json
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment, Task
from pyacquisition.instruments.lakeshore.lakeshore_350 import OutputChannel


@dataclass
class Heat(Task):
    """Heat an output."""

    power: float
    output: OutputChannel = OutputChannel.OUTPUT_1


class Rig(Experiment):
    def setup(self):
        self.register_task(Heat)
        self.add_task_manager("control")


def make(root):
    """An experiment on this root folder, set up and served as running does,
    without running."""
    experiment = Rig(root_path=str(root), gui=False)
    experiment.setup()
    for manager in experiment.task_managers.values():
        manager._register_endpoints(experiment._api_server)
    experiment._register_endpoints(experiment._api_server)
    return experiment, TestClient(experiment._api_server.app)


def queue_of(experiment, manager="main"):
    return list(experiment.task_managers[manager]._task_queue._queue)


def queued(client, path, **params):
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text


# -------------------------------------------------------------- the round trip
def test_a_saved_sequence_queues_identical_tasks_in_a_new_run(tmp_path):
    first, client = make(tmp_path)
    queued(client, "/tasks/waitfor", minutes=5)
    queued(client, "/tasks/heat", power=2.5, output="Output 3")
    queued(client, "/tasks/newfile", file_name="cooldown", increment_block=True)
    before = queue_of(first)

    response = client.get("/sequences/save", params={"name": "cooldown"})
    assert response.json()["saved"] == 3

    # A new run of the experiment, on the same folder.
    second, client = make(tmp_path)
    response = client.get("/sequences/load", params={"name": "cooldown"})

    assert response.json()["queued"] == 3
    after = queue_of(second)
    assert after == before  # dataclass equality: the same tasks, the same inputs
    assert after[1].output is OutputChannel.OUTPUT_3
    assert [t._id for t in after] != [t._id for t in before]  # new tasks


def test_the_file_says_how_each_task_was_queued(tmp_path):
    experiment, client = make(tmp_path)
    queued(client, "/tasks/heat", power=1.0, output="OUTPUT_2")

    client.get("/sequences/save", params={"name": "heat once"})

    saved = json.loads((tmp_path / "sequences" / "heat once.json").read_text())
    assert saved["name"] == "heat once"
    assert saved["saved"]
    assert saved["tasks"] == [
        {"task": "heat", "name": "Heat", "parameters": {"power": 1.0, "output": "OUTPUT_2"}}
    ]


def test_a_sequence_loads_onto_another_task_manager(tmp_path):
    experiment, client = make(tmp_path)
    queued(client, "/tasks/waitfor", seconds=5)
    client.get("/sequences/save", params={"name": "short"})

    client.get("/sequences/load", params={"name": "short", "manager": "control"})

    assert [t.seconds for t in queue_of(experiment, "control")] == [5]


def test_it_is_queued_after_what_is_there(tmp_path):
    experiment, client = make(tmp_path)
    queued(client, "/tasks/waitfor", seconds=1)
    client.get("/sequences/save", params={"name": "one"})

    client.get("/sequences/load", params={"name": "one"})
    client.get("/sequences/load", params={"name": "one"})

    assert len(queue_of(experiment)) == 3


# -------------------------------------------------------------- saving
def test_the_running_task_is_saved_first_unless_left_out(tmp_path):
    experiment, client = make(tmp_path)
    queued(client, "/tasks/waitfor", seconds=1)
    queued(client, "/tasks/waitfor", seconds=2)
    manager = experiment.task_managers["main"]
    manager._current_task = manager._task_queue._queue.popleft()  # as if running

    client.get("/sequences/save", params={"name": "with"})
    client.get("/sequences/save", params={"name": "without", "include_running": False})

    names = {s["name"]: s["tasks"] for s in client.get("/sequences").json()["data"]}
    assert names == {"with": ["WaitFor", "WaitFor"], "without": ["WaitFor"]}


def test_tasks_not_queued_from_the_api_are_skipped_and_named(tmp_path):
    experiment, client = make(tmp_path)
    experiment.task_managers["main"].add_task(Heat(power=1))  # as setup() might
    queued(client, "/tasks/waitfor", seconds=1)

    response = client.get("/sequences/save", params={"name": "some"})

    assert response.json()["saved"] == 1
    assert response.json()["skipped"] == ["Heat"]


def test_a_duplicate_is_saved_like_its_original(tmp_path):
    experiment, client = make(tmp_path)
    queued(client, "/tasks/waitfor", seconds=7)
    manager = experiment.task_managers["main"]
    manager.duplicate_queued_task(queue_of(experiment)[0]._id)

    entries, skipped = manager.saveable()

    assert [e["parameters"]["seconds"] for e in entries] == [7, 7]
    assert skipped == []


def test_an_empty_queue_is_not_saved(tmp_path):
    experiment, client = make(tmp_path)

    response = client.get("/sequences/save", params={"name": "nothing"})

    assert response.status_code == 422
    assert not (tmp_path / "sequences" / "nothing.json").exists()


def test_a_sequence_is_replaced_only_when_asked(tmp_path):
    experiment, client = make(tmp_path)
    queued(client, "/tasks/waitfor", seconds=1)
    client.get("/sequences/save", params={"name": "mine"})
    queued(client, "/tasks/waitfor", seconds=2)

    refused = client.get("/sequences/save", params={"name": "mine"})
    assert refused.status_code == 409
    assert "already a sequence called 'mine'" in refused.json()["detail"]

    client.get("/sequences/save", params={"name": "mine", "overwrite": True})
    (entry,) = [s for s in client.get("/sequences").json()["data"] if s["name"] == "mine"]
    assert len(entry["tasks"]) == 2


@pytest.mark.parametrize("name", ["", "a/b", "what?"])
def test_a_name_that_cannot_be_a_file_is_refused(tmp_path, name):
    experiment, client = make(tmp_path)
    queued(client, "/tasks/waitfor", seconds=1)

    response = client.get("/sequences/save", params={"name": name})

    assert response.status_code == 422
    assert "sequence's name" in response.json()["detail"] or "empty" in response.json()["detail"]


# -------------------------------------------------------------- loading
def test_nothing_is_queued_if_any_task_cannot_be(tmp_path):
    experiment, client = make(tmp_path)
    folder = tmp_path / "sequences"
    folder.mkdir()
    (folder / "broken.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {"task": "waitfor", "name": "WaitFor", "parameters": {"seconds": 1}},
                    {"task": "gone", "name": "Gone", "parameters": {}},
                    {"task": "heat", "name": "Heat", "parameters": {"output": "OUTPUT_9"}},
                ]
            }
        )
    )

    response = client.get("/sequences/load", params={"name": "broken"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "2. Gone: can't be queued here" in detail
    assert "3. Heat:" in detail  # no power, and no such output
    assert queue_of(experiment) == []


def test_an_input_missing_from_the_file_takes_its_default(tmp_path):
    experiment, client = make(tmp_path)
    folder = tmp_path / "sequences"
    folder.mkdir()
    (folder / "old.json").write_text(
        json.dumps({"tasks": [{"task": "heat", "parameters": {"power": 3}}]})
    )

    client.get("/sequences/load", params={"name": "old"})

    (task,) = queue_of(experiment)
    assert (task.power, task.output) == (3, OutputChannel.OUTPUT_1)


def test_an_unknown_sequence_or_manager_is_a_clear_error(tmp_path):
    experiment, client = make(tmp_path)
    queued(client, "/tasks/waitfor", seconds=1)
    client.get("/sequences/save", params={"name": "here"})

    missing = client.get("/sequences/load", params={"name": "nowhere"})
    assert missing.status_code == 422
    assert "no sequence called 'nowhere'" in missing.json()["detail"]

    no_manager = client.get("/sequences/load", params={"name": "here", "manager": "x"})
    assert no_manager.status_code == 422
    assert "no task manager called 'x'" in no_manager.json()["detail"]


# -------------------------------------------------------------- the list
def test_the_list_skips_a_file_it_cannot_read(tmp_path):
    experiment, client = make(tmp_path)
    folder = tmp_path / "sequences"
    folder.mkdir()
    (folder / "junk.json").write_text("{not json")
    (folder / "fine.json").write_text(json.dumps({"saved": "then", "tasks": []}))

    listed = client.get("/sequences").json()["data"]

    assert listed == [{"name": "fine", "saved": "then", "tasks": []}]


def test_a_sequence_can_be_deleted(tmp_path):
    experiment, client = make(tmp_path)
    queued(client, "/tasks/waitfor", seconds=1)
    client.get("/sequences/save", params={"name": "gone soon"})

    assert client.get("/sequences/delete", params={"name": "gone soon"}).status_code == 200
    assert client.get("/sequences").json()["data"] == []
    assert client.get("/sequences/delete", params={"name": "gone soon"}).status_code == 422
