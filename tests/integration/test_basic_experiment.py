import pytest
from pyacquisition import Experiment
import tomllib


@pytest.fixture
def basic_toml():
    filepath = "tests/integration/basic.toml"
    with open(filepath, "rb") as file:
        return tomllib.load(file)


def test_experiment_initialization(basic_toml):
    print("Basic TOML content:", basic_toml)
    experiment = Experiment.from_config("tests/integration/basic.toml")
    assert experiment is not None, "Experiment should be initialized successfully."

    assert experiment._api_server.host == basic_toml["api_server"]["host"], (
        "API server host should match TOML configuration."
    )
