"""The tasks every experiment has for its measurements (tasks/measurements.py):
pausing and resuming them, and setting the time between them."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment
from pyacquisition.tasks import PauseMeasurements, ResumeMeasurements, SetMeasurementPeriod

NAMES = ["pausemeasurements", "resumemeasurements", "setmeasurementperiod"]


@pytest.fixture
def experiment(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    experiment.add_task_manager("control")
    return experiment


def run(experiment, task):
    asyncio.run(task.start(experiment=experiment))
    assert task.outcome == "completed", task.failure


def test_pausing_and_resuming_the_measurements(experiment):
    rack = experiment._rack
    assert not rack.paused

    run(experiment, PauseMeasurements())
    assert rack.paused
    run(experiment, PauseMeasurements())  # already paused: nothing more
    assert rack.paused

    run(experiment, ResumeMeasurements())
    assert not rack.paused
    run(experiment, ResumeMeasurements())  # already running: nothing more
    assert not rack.paused


def test_setting_the_period(experiment):
    run(experiment, SetMeasurementPeriod(period=2.5))

    assert experiment._rack.period == 2.5


@pytest.mark.parametrize("period", [0, -1.0])
def test_a_period_that_isnt_above_zero_is_refused(experiment, period):
    with pytest.raises(ValueError, match="above zero"):
        SetMeasurementPeriod(period=period)

    response = TestClient(experiment._api_server.app).get(
        "/tasks/setmeasurementperiod", params={"period": period}
    )
    assert response.status_code == 422
    assert "above zero" in response.json()["detail"]


def test_every_task_manager_has_them(experiment):
    paths = TestClient(experiment._api_server.app).get("/openapi.json").json()["paths"]

    for name in NAMES:
        assert f"/tasks/{name}" in paths
        assert f"/managers/control/tasks/{name}" in paths
        assert "tasks" in paths[f"/tasks/{name}"]["get"]["tags"]


def test_they_are_queued_saved_and_loaded_in_a_sequence(experiment):
    client = TestClient(experiment._api_server.app)
    client.get("/tasks/pausemeasurements")
    client.get("/tasks/setmeasurementperiod", params={"period": 10})
    client.get("/tasks/resumemeasurements")
    manager = experiment._task_managers["main"]

    entries, skipped = manager.saveable()
    manager._task_queue._queue.clear()
    manager.queue_saved(entries)

    assert skipped == []
    queued = list(manager._task_queue._queue)
    assert [task.name for task in queued] == [
        "PauseMeasurements",
        "SetMeasurementPeriod",
        "ResumeMeasurements",
    ]
    assert queued[1].period == 10
    assert [task.description for task in queued] == [
        "Pausing the measurements",
        "Measuring every 10.0 s",
        "Resuming the measurements",
    ]
