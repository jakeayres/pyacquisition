import asyncio
import pytest
from pyacquisition import Experiment, Measurement
from pyacquisition.instruments.software import Clock


@pytest.fixture
def experiment(tmp_path):
    return Experiment(root_path=str(tmp_path), gui=False)


def test_add_and_remove_instrument(experiment):
    clock = Clock("clock")

    experiment.add_instrument(clock)
    assert experiment.instruments["clock"] is clock

    experiment.remove_instrument("clock")
    assert "clock" not in experiment.instruments


def test_add_and_remove_measurement(experiment):
    clock = Clock("clock")
    experiment.add_instrument(clock)

    measurement = Measurement("time", clock.timestamp_ms)
    experiment.add_measurement(measurement)
    assert experiment.measurements["time"] is measurement

    experiment.remove_measurement("time")
    assert "time" not in experiment.measurements


def test_add_measurement_rejects_non_measurement(experiment):
    with pytest.raises(TypeError):
        experiment.add_measurement(lambda: 1)


def test_views_are_read_only(experiment):
    with pytest.raises(TypeError):
        experiment.instruments["clock"] = Clock("clock")
    with pytest.raises(TypeError):
        experiment.measurements["time"] = None


def test_programmatic_setup_hook(tmp_path):
    """Building an experiment by subclassing and overriding setup()."""

    class MyExperiment(Experiment):
        def setup(self):
            clock = Clock("clock")
            self.add_instrument(clock)
            self.add_measurement(Measurement("time", clock.timestamp_ms))

    experiment = MyExperiment(root_path=str(tmp_path), gui=False)
    experiment.setup()

    assert "clock" in experiment.instruments
    assert "time" in experiment.measurements


@pytest.mark.asyncio
async def test_cannot_change_once_running(tmp_path):
    class MyExperiment(Experiment):
        def setup(self):
            clock = Clock("clock")
            self.add_instrument(clock)
            self.add_measurement(Measurement("time", clock.timestamp_ms))

    experiment = MyExperiment(root_path=str(tmp_path), api_server_port=8123, gui=False)
    errors = {}

    async def change_while_running():
        await asyncio.sleep(0.5)
        attempts = {
            "add_instrument": lambda: experiment.add_instrument(Clock("late")),
            "remove_instrument": lambda: experiment.remove_instrument("clock"),
            "add_measurement": lambda: experiment.add_measurement(
                Measurement("late", lambda: 1)
            ),
            "remove_measurement": lambda: experiment.remove_measurement("time"),
            "add_calculation": lambda: experiment.add_calculation(lambda row: {}),
            "add_task_manager": lambda: experiment.add_task_manager("late"),
        }
        for name, attempt in attempts.items():
            try:
                attempt()
            except RuntimeError as e:
                errors[name] = e
        experiment._shutdown_event.set()

    await asyncio.wait_for(
        asyncio.gather(experiment._run(), change_while_running()), timeout=20
    )

    assert set(errors) == {
        "add_instrument",
        "remove_instrument",
        "add_measurement",
        "remove_measurement",
        "add_calculation",
        "add_task_manager",
    }
    # nothing was changed by the rejected calls
    assert set(experiment.instruments) == {"clock"}
    assert set(experiment.measurements) == {"time"}
