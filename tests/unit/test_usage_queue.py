"""Usage › Queue, pause and save tasks (docs/usage/queue.md): the task queued in
setup(), and a queue of two sweeps saved as a sequence and loaded again, through
the endpoints the Queue tab's Save and Load use."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "queue"
SIMULATED = ROOT / "examples" / "simulated_rig"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SIMULATED))
    sys.modules.pop("simulated", None)
    spec = importlib.util.spec_from_file_location("queue_sample_2", HERE / "sample_2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    experiment = module.Sample(root_path=str(tmp_path), gui=False)
    experiment.setup()
    api = experiment._api_server
    experiment._register_endpoints(api)
    for manager in experiment.task_managers.values():
        manager._register_endpoints(api)
    return experiment, TestClient(api.app), tmp_path


def queued(experiment) -> list:
    return list(experiment.task_managers["main"]._task_queue._queue)


def test_it_starts_from_the_end_of_sweep_a_temperature():
    assert text(HERE / "sample_1.py") == text(ROOT / "examples" / "usage" / "sweep" / "sample_5.py")


def test_setup_queues_set_temperature_to_10_k(lab):
    experiment, _, _ = lab
    (task,) = queued(experiment)
    assert type(task).__name__ == "SetTemperature" and task.kelvin == 10.0


def test_the_night_s_work_is_saved_as_a_sequence_without_the_task_from_setup(lab):
    experiment, client, folder = lab
    for start, stop in ((10, 20), (20, 10)):
        answer = client.get("/tasks/sweep", params={"start_kelvin": start, "stop_kelvin": stop, "step": 2, "dwell": 60})
        assert answer.status_code == 200, answer.text
    saved = client.get("/sequences/save", params={"name": "hysteresis"}).json()
    assert "SetTemperature" in json.dumps(saved)  # named as left out
    sequence = json.loads((folder / "sequences" / "hysteresis.json").read_text(encoding="utf-8"))
    assert [(t["task"], t["parameters"]["start_kelvin"], t["parameters"]["stop_kelvin"]) for t in sequence["tasks"]] == [
        ("sweep", 10.0, 20.0), ("sweep", 20.0, 10.0)
    ]


def test_loading_it_queues_the_same_sweeps_after_those_waiting(lab):
    experiment, client, _ = lab
    for start, stop in ((10, 20), (20, 10)):
        client.get("/tasks/sweep", params={"start_kelvin": start, "stop_kelvin": stop, "step": 2, "dwell": 60})
    client.get("/sequences/save", params={"name": "hysteresis"})
    listed = client.get("/sequences").json()
    assert "hysteresis" in json.dumps(listed)
    assert client.get("/sequences/load", params={"name": "hysteresis"}).status_code == 200
    names = [(type(t).__name__, getattr(t, "start_kelvin", None)) for t in queued(experiment)]
    assert names == [("SetTemperature", None), ("Sweep", 10.0), ("Sweep", 20.0), ("Sweep", 10.0), ("Sweep", 20.0)]
