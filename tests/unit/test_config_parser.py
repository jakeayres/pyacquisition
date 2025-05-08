from pyacquisition.core.config_parser import ConfigParser
import pytest
import tomllib
import os

# Define a directory containing your test TOML files
TOML_TEST_DIR = "tests/toml/"


def test_load_toml():
    """Test the load_toml method with a valid TOML file."""
    file_path = os.path.join(TOML_TEST_DIR, "pass_basic.toml")
    config = ConfigParser.load_toml(file_path)
    assert isinstance(config, dict), "Loaded config should be a dictionary"
    assert "experiment" in config, "Config should contain 'experiment' section"
    assert "instruments" in config, "Config should contain 'instruments' section"


@pytest.fixture
def load_toml_file():
    """Fixture to load a TOML file."""
    def _load(file_path):
        return ConfigParser.load_toml(file_path)
    return _load


