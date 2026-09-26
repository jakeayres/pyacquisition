"""What a task's endpoint says about its inputs, so that a form can be built from
the API schema: defaults, descriptions and choices (milestone 10)."""

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment, Task
from pyacquisition.core.task_manager.inputs import attribute_docs
from pyacquisition.instruments import Lakeshore_350
from pyacquisition.instruments.lakeshore.lakeshore_350 import OutputChannel
from pyacquisition.tasks import RampTemperature


@dataclass
class Heat(Task):
    """Heat an output.

    A longer description, which is not about the inputs.

    Attributes:
        output (OutputChannel): Which output to use.
        power (float): The power, in percent. It can
            run over two lines.
        label: Text for the log.

    Class Attributes:
        name (str): Not an input.
    """

    note: str
    output: OutputChannel = OutputChannel.OUTPUT_2
    power: float = 10.0
    label: str = "heating"

    async def run(self, experiment):
        pass


@dataclass
class Collect(Task):
    """An input whose default is made by a factory."""

    names: list = field(default_factory=list)

    async def run(self, experiment):
        pass


@pytest.fixture
def experiment(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    experiment.register_task(Heat)
    experiment.register_task(Collect)
    return experiment


def schema(experiment, path):
    operation = experiment._api_server.app.openapi()["paths"][path]["get"]
    return operation, {p["name"]: p for p in operation.get("parameters", [])}


def queued(experiment):
    return list(experiment._task_manager._task_queue._queue)


# -------------------------------------------------------------- the docstring
def test_each_input_is_described_from_the_attributes_section():
    assert attribute_docs(Heat) == {
        "output": "Which output to use.",
        "power": "The power, in percent. It can run over two lines.",
        "label": "Text for the log.",
    }


def test_an_args_section_works_too():
    class Plain:
        """Something.

        Args:
            x (int): How many.
        """

    assert attribute_docs(Plain) == {"x": "How many."}


def test_a_task_with_no_section_has_no_descriptions():
    class Bare:
        """Just a line."""

    assert attribute_docs(Bare) == {}
    assert attribute_docs(type("NoDoc", (), {})) == {}


# -------------------------------------------------------------- the schema
def test_an_input_with_a_default_is_optional_and_says_its_default(experiment):
    _, inputs = schema(experiment, "/tasks/heat")

    assert inputs["power"]["required"] is False
    assert inputs["power"]["schema"]["default"] == 10.0
    assert inputs["label"]["schema"]["default"] == "heating"


def test_an_input_without_a_default_is_required(experiment):
    _, inputs = schema(experiment, "/tasks/heat")

    assert inputs["note"]["required"] is True
    assert "default" not in inputs["note"]["schema"]


def test_an_input_made_by_a_factory_is_still_asked_for(experiment):
    # Its default is made afresh for each task, so the schema can't give one.
    _, inputs = schema(experiment, "/tasks/collect")

    assert inputs["names"]["required"] is True


def test_each_input_says_what_it_is_for(experiment):
    _, inputs = schema(experiment, "/tasks/heat")

    assert inputs["power"]["description"] == (
        "The power, in percent. It can run over two lines."
    )


def test_an_enum_input_lists_its_choices_with_their_labels(experiment):
    _, inputs = schema(experiment, "/tasks/heat")
    output = inputs["output"]["schema"]

    assert output["type"] == "string"
    assert output["enum"] == ["OUTPUT_1", "OUTPUT_2", "OUTPUT_3", "OUTPUT_4"]
    assert output["x-labels"] == ["Output 1", "Output 2", "Output 3", "Output 4"]
    assert output["default"] == "OUTPUT_2"  # the member's name, as it is sent


def test_the_endpoint_is_named_after_the_task(experiment):
    operation, _ = schema(experiment, "/tasks/heat")

    assert operation["summary"] == "Heat"


def test_an_instrument_input_lists_the_instruments_it_can_be(experiment):
    experiment.add_instrument(Lakeshore_350("cryo_a", "GPIB0::1::INSTR", adapter="mock"))
    experiment.add_instrument(Lakeshore_350("cryo_b", "GPIB0::2::INSTR", adapter="mock"))
    experiment._register_instrument_tasks()

    _, inputs = schema(experiment, "/tasks/ramp_temperature")

    assert inputs["lakeshore"]["schema"]["enum"] == ["cryo_a", "cryo_b"]


def test_an_instrument_input_with_none_to_offer_is_free_text(experiment):
    experiment.register_task(RampTemperature)

    _, inputs = schema(experiment, "/tasks/ramptemperature")

    assert "enum" not in inputs["lakeshore"]["schema"]


# -------------------------------------------------------------- queueing
def test_an_input_left_out_takes_its_default(experiment):
    client = TestClient(experiment._api_server.app)

    response = client.get("/tasks/heat", params={"note": "warm up"})

    assert response.status_code == 200, response.text
    (task,) = queued(experiment)
    assert (task.note, task.output, task.power, task.label) == (
        "warm up",
        OutputChannel.OUTPUT_2,
        10.0,
        "heating",
    )


def test_an_enum_is_still_accepted_by_its_label(experiment):
    client = TestClient(experiment._api_server.app)

    response = client.get(
        "/tasks/heat", params={"note": "x", "output": "Output 3"}
    )

    assert response.status_code == 200, response.text
    assert queued(experiment)[0].output is OutputChannel.OUTPUT_3


def test_the_standard_tasks_need_nothing_they_have_a_default_for(experiment):
    client = TestClient(experiment._api_server.app)

    assert client.get("/tasks/waitfor", params={"seconds": 5}).status_code == 200
    (task,) = queued(experiment)
    assert (task.hours, task.minutes, task.seconds) == (0, 0, 5)


@dataclass
class Checked(Task):
    """Refuses a dwell that isn't positive."""

    dwell: int = 60

    def __post_init__(self):
        super().__post_init__()
        if self.dwell <= 0:
            raise ValueError("The dwell must be more than 0 seconds.")

    async def run(self, experiment):
        pass


def test_a_task_that_refuses_its_inputs_says_why(experiment):
    experiment.register_task(Checked)
    client = TestClient(experiment._api_server.app)

    response = client.get("/tasks/checked", params={"dwell": 0})

    assert response.status_code == 422
    assert response.json()["detail"] == "The dwell must be more than 0 seconds."
    assert queued(experiment) == []
