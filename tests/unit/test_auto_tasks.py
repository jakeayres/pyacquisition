"""Tasks that come with an instrument are registered when the instrument is present."""

import dataclasses

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment, Task
from pyacquisition.instruments import Lakeshore_340, Lakeshore_350, Mercury_IPS
from pyacquisition.instruments.lakeshore.lakeshore_340 import (
    OutputChannel as OC340,
)
from pyacquisition.instruments.lakeshore.lakeshore_350 import (
    OutputChannel as OC350,
)
from pyacquisition.tasks import (
    RampTemperature,
    SweepMagneticField,
    instrument_tasks,
    standard_tasks,
)
from pyacquisition.tasks.field_sweep import RampMagnet, RampMagnetToZero


@pytest.fixture
def experiment(tmp_path):
    return Experiment(root_path=str(tmp_path), gui=False)


def mock(cls, uid):
    return cls(uid, "GPIB0::1::INSTR", adapter="mock")


def paths(experiment):
    return experiment._api_server.app.openapi()["paths"]


def parameters(experiment, path):
    operation = paths(experiment)[path]["get"]
    return {p["name"]: p["schema"] for p in operation.get("parameters", [])}


def queued(experiment):
    return list(experiment._task_manager._task_queue._queue)


# ------------------------------------------------------------ what is declared
def test_the_tasks_say_what_they_are_for():
    assert RampTemperature.applies_to == {"lakeshore": (Lakeshore_340, Lakeshore_350)}
    assert SweepMagneticField.applies_to == {"magnet_psu": (Mercury_IPS,)}


def test_the_leaf_tasks_are_left_out_and_the_standard_tasks_stay_as_they_were():
    assert instrument_tasks == [RampTemperature, SweepMagneticField]
    assert RampMagnet not in instrument_tasks
    assert RampMagnetToZero not in instrument_tasks
    assert [task.__name__ for task in standard_tasks] == [
        "NewFile",
        "WaitFor",
        "WaitUntil",
        "PauseMeasurements",
        "ResumeMeasurements",
        "SetMeasurementPeriod",
    ]


@pytest.mark.parametrize("task", instrument_tasks)
def test_each_declaration_names_inputs_that_the_task_has(task):
    names = {field.name for field in dataclasses.fields(task)}
    for field, types in task.applies_to.items():
        assert field in names, f"{task.__name__} has no input {field!r}"
        assert all(isinstance(t, type) for t in types)


def test_a_task_that_declares_nothing_is_not_for_any_instrument():
    assert Task.applies_to is None


# --------------------------------------------------------------- registering
def test_a_lakeshore_registers_ramp_temperature_with_its_id_fixed(experiment):
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))

    experiment._register_instrument_tasks()

    assert "/tasks/ramp_temperature" in paths(experiment)
    asked = parameters(experiment, "/tasks/ramp_temperature")
    assert set(asked) == {"output_channel", "setpoint", "ramp_rate"}, "it knows which"


def test_the_fixed_id_reaches_the_task_that_is_queued(experiment):
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))
    experiment._register_instrument_tasks()
    client = TestClient(experiment._api_server.app)

    response = client.get(
        "/tasks/ramp_temperature",
        params={"output_channel": "OUTPUT_1", "setpoint": 4.2, "ramp_rate": 1.0},
    )

    assert response.json() == {"status": 200, "message": "RampTemperature added"}
    (task,) = queued(experiment)
    assert task.lakeshore == "cryo"
    assert task.output_channel.name == "OUTPUT_1"
    assert (task.setpoint, task.ramp_rate) == (4.2, 1.0)


def test_a_lakeshore_340_will_do_as_well(experiment):
    experiment.add_instrument(mock(Lakeshore_340, "old"))

    experiment._register_instrument_tasks()

    assert "/tasks/ramp_temperature" in paths(experiment)


def test_several_matching_instruments_leave_the_id_to_be_asked(experiment):
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))
    experiment.add_instrument(mock(Lakeshore_340, "old"))

    experiment._register_instrument_tasks()

    assert "lakeshore" in parameters(experiment, "/tasks/ramp_temperature")
    registered = [
        task for task, _ in experiment._shared_tasks if task is RampTemperature
    ]
    assert registered == [RampTemperature], "registered once, not once for each"


def test_no_matching_instrument_registers_nothing(experiment):
    experiment._register_instrument_tasks()

    assert "/tasks/ramp_temperature" not in paths(experiment)
    assert "/tasks/sweep_magnetic_field" not in paths(experiment)


def test_a_mercury_registers_the_sweep_but_not_its_parts(experiment):
    experiment.add_instrument(mock(Mercury_IPS, "magnet"))

    experiment._register_instrument_tasks()

    assert "/tasks/sweep_magnetic_field" in paths(experiment)
    assert set(parameters(experiment, "/tasks/sweep_magnetic_field")) == {
        "setpoint",
        "ramp_rate",
        "new_chapter",
    }
    assert "/tasks/ramp_magnet" not in paths(experiment)
    assert "/tasks/ramp_magnet_to_zero" not in paths(experiment)
    assert "/tasks/ramp_temperature" not in paths(experiment), "no Lakeshore here"


def test_the_labels_are_words(experiment):
    experiment.add_instrument(mock(Mercury_IPS, "magnet"))
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))

    experiment._register_instrument_tasks()

    assert "/tasks/sweep_magnetic_field" in paths(experiment)
    assert "/tasks/ramp_temperature" in paths(experiment)


def test_the_standard_tasks_keep_their_addresses(experiment):
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))
    experiment._register_instrument_tasks()

    assert {"/tasks/newfile", "/tasks/waitfor", "/tasks/waituntil"} <= set(
        paths(experiment)
    )


def test_a_task_registered_by_hand_is_not_registered_again(experiment):
    experiment.register_task(RampTemperature, label="Ramp", lakeshore="cryo")
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))

    experiment._register_instrument_tasks()

    assert "/tasks/ramp" in paths(experiment)
    assert "/tasks/ramp_temperature" not in paths(experiment)
    assert [t for t, _ in experiment._shared_tasks if t is RampTemperature] == [
        RampTemperature
    ]


def test_registering_twice_does_nothing_the_second_time(experiment):
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))

    experiment._register_instrument_tasks()
    experiment._register_instrument_tasks()

    assert [t for t, _ in experiment._shared_tasks if t is RampTemperature] == [
        RampTemperature
    ]


def test_the_tasks_can_be_queued_on_every_task_manager(experiment):
    control = experiment.add_task_manager("control")
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))

    experiment._register_instrument_tasks()

    assert "/managers/control/tasks/ramp_temperature" in paths(experiment)
    assert control is experiment.task_managers["control"]


# ----------------------------------------------------------------- turning off
def test_auto_tasks_is_on_by_default(experiment):
    assert experiment._auto_tasks is True
    assert Experiment.auto_tasks is True


def test_it_can_be_turned_off_with_an_argument(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False, auto_tasks=False)
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))

    experiment._register_instrument_tasks()

    assert "/tasks/ramp_temperature" not in paths(experiment)


def test_it_can_be_turned_off_in_the_class(tmp_path):
    class MyExperiment(Experiment):
        root_path = str(tmp_path)
        gui = False
        auto_tasks = False

    experiment = MyExperiment()
    experiment.add_instrument(mock(Mercury_IPS, "magnet"))
    experiment._register_instrument_tasks()

    assert "/tasks/sweep_magnetic_field" not in paths(experiment)


def test_it_can_be_turned_off_in_a_config_file(tmp_path):
    config = tmp_path / "rig.toml"
    config.write_text(
        "[experiment]\nauto_tasks = false\n"
        '[instruments]\ncryo = {instrument = "Lakeshore_350", adapter = "mock", '
        'resource = "GPIB0::1::INSTR"}\n'
    )

    class MyExperiment(Experiment):
        root_path = str(tmp_path)
        gui = False

    experiment = MyExperiment.from_config(str(config))
    experiment._register_instrument_tasks()

    assert "cryo" in experiment.instruments
    assert "/tasks/ramp_temperature" not in paths(experiment)


def test_a_config_experiment_gets_the_tasks_of_its_instruments(tmp_path):
    config = tmp_path / "rig.toml"
    config.write_text(
        '[instruments]\ncryo = {instrument = "Lakeshore_350", adapter = "mock", '
        'resource = "GPIB0::1::INSTR"}\n'
    )

    class MyExperiment(Experiment):
        root_path = str(tmp_path)
        gui = False

    experiment = MyExperiment.from_config(str(config))
    experiment._register_instrument_tasks()

    assert "/tasks/ramp_temperature" in paths(experiment)


def test_the_option_is_documented_as_an_experiment_option():
    from pyacquisition.core import settings

    assert settings.SETTINGS["auto_tasks"].section == "experiment"
    assert settings.SETTINGS["auto_tasks"].key == "auto_tasks"


# ------------------------------------------------------------ enum inputs
def test_an_enum_input_is_asked_for_as_text(experiment):
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))
    experiment._register_instrument_tasks()

    assert (
        parameters(experiment, "/tasks/ramp_temperature")["output_channel"]["type"]
        == "string"
    )


def test_text_for_an_enum_input_is_resolved_when_the_task_is_queued(experiment):
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))
    experiment._register_instrument_tasks()
    client = TestClient(experiment._api_server.app)

    client.get(
        "/tasks/ramp_temperature",
        params={"output_channel": "output 2", "setpoint": 1, "ramp_rate": 1},
    )

    (task,) = queued(experiment)
    assert task.output_channel.name == "OUTPUT_2"


def test_a_channel_that_does_not_exist_is_refused_saying_what_would_do(experiment):
    experiment.add_instrument(mock(Lakeshore_350, "cryo"))
    experiment._register_instrument_tasks()
    client = TestClient(experiment._api_server.app)

    response = client.get(
        "/tasks/ramp_temperature",
        params={"output_channel": "OUTPUT_9", "setpoint": 1, "ramp_rate": 1},
    )

    assert response.status_code == 422
    assert "OUTPUT_1, OUTPUT_2, OUTPUT_3, OUTPUT_4" in response.json()["detail"]
    assert queued(experiment) == []


def test_a_fixed_input_may_be_text_for_an_enum(experiment):
    experiment.register_task(
        RampTemperature,
        label="Ramp Output 2",
        lakeshore="cryo",
        output_channel="OUTPUT_2",
    )
    client = TestClient(experiment._api_server.app)

    client.get("/tasks/ramp_output_2", params={"setpoint": 1, "ramp_rate": 1})

    (task,) = queued(experiment)
    assert task.output_channel.name == "OUTPUT_2"


def test_the_description_names_the_channel(experiment):
    assert RampTemperature("c", OC350.OUTPUT_1, 4.0, 1.0).description == (
        "Ramping temperature OUTPUT_1 to 4.0 at 1.0K/min"
    )
    assert RampTemperature("c", "OUTPUT_1", 4.0, 1.0).description == (
        "Ramping temperature OUTPUT_1 to 4.0 at 1.0K/min"
    )


# ------------------------------------------------------ the task on a controller
@pytest.fixture
def fast(monkeypatch):
    real = Task.sleep

    async def quick(self, seconds):
        await real(self, seconds / 1000)

    monkeypatch.setattr(Task, "sleep", quick)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "channel", ["OUTPUT_2", "output 2", OC350.OUTPUT_2, OC340.OUTPUT_2]
)
async def test_ramp_temperature_works_on_a_350_whichever_way_the_channel_is_given(
    fast, experiment, channel
):
    cryo = mock(Lakeshore_350, "cryo")
    experiment.add_instrument(cryo)

    task = RampTemperature("cryo", channel, 5.0, 2.0)
    await task.start(experiment)

    assert task.outcome == "completed", task.failure
    written = cryo._visa_resource.written
    assert any(line.startswith("RAMP 2") for line in written), written
    assert any(line.startswith("SETP 2") for line in written), written
