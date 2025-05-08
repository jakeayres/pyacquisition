from pyacquisition.core.config_parser import ConfigParser, TOMLConfigError
import pytest
import tomllib
import os

# Define a directory containing your test TOML files
TOML_TEST_DIR = "tests/toml/"


def test_load_valid_toml():
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
        _path = os.path.join(TOML_TEST_DIR, file_path)
        return ConfigParser.load_toml(_path)
    return _load


@pytest.mark.parametrize("file_name", [
    "pass_basic.toml",
    "pass_empty.toml",
    "fail_invalid_syntax.toml",
])
def test_invalid_syntax_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert isinstance(config, dict)
    elif "fail" in file_name:
        with pytest.raises(tomllib.TOMLDecodeError):
            load_toml_file(file_name)



@pytest.mark.parametrize("file_name", [
    "pass_basic.toml",
    "pass_empty.toml",
    "fail_unallowed_section.toml",
])
def test_invalid_sections_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert ConfigParser.all_sections_are_valid(config), "Config should contain only allowed sections"
    elif "fail" in file_name:
        config = load_toml_file(file_name)
        assert not ConfigParser.all_sections_are_valid(config), "Config should contain a disallowed sections"
        

@pytest.mark.parametrize("file_name", [
    "pass_basic.toml",
    "pass_empty.toml",
    "fail_bad_instrument.toml",
])
def test_invalid_instrument_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert ConfigParser.all_instrument_values_are_dicts(config), "Config should contain only valid instrument values"
    elif "fail" in file_name:
        config = load_toml_file(file_name)
        assert not ConfigParser.all_instrument_values_are_dicts(config), "Config should contain invalid instrument values"
        
    
@pytest.mark.parametrize("file_name", [
    "pass_basic.toml",
    "pass_empty.toml",
    "fail_instrument_missing_instrument_key.toml",
])
def test_invalid_instrument_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert ConfigParser.all_instrument_dicts_contain_instrument(config), "Config should contain only valid instrument values"
    elif "fail" in file_name:
        config = load_toml_file(file_name)
        assert not ConfigParser.all_instrument_dicts_contain_instrument(config), "Config should contain invalid instrument values"
       
       
@pytest.mark.parametrize("file_name", [
    "pass_basic.toml",
    "pass_empty.toml",
    "fail_measurement_with_nonexistant_instrument.toml",
])
def test_invalid_measurement(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert ConfigParser.all_measurement_instruments_exist(config), "Config should contain only valid instrument values"
    elif "fail" in file_name:
        config = load_toml_file(file_name)
        assert not ConfigParser.all_measurement_instruments_exist(config), "Config should contain invalid instrument values"
       