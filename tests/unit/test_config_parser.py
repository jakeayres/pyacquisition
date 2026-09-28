from pyacquisition.core.config_parser import ConfigParser, InvalidCalculationError, InvalidTraceError
import pytest
import tomllib
import os
import re

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


@pytest.mark.parametrize(
    "file_name",
    [
        "pass_basic.toml",
        "pass_empty.toml",
        "fail_invalid_syntax.toml",
    ],
)
def test_invalid_syntax_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert isinstance(config, dict)
    elif "fail" in file_name:
        with pytest.raises(tomllib.TOMLDecodeError):
            load_toml_file(file_name)


@pytest.mark.parametrize(
    "file_name",
    [
        "pass_basic.toml",
        "pass_empty.toml",
        "fail_unallowed_section.toml",
    ],
)
def test_invalid_sections_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert ConfigParser.all_sections_are_valid(config), (
            "Config should contain only allowed sections"
        )
    elif "fail" in file_name:
        config = load_toml_file(file_name)
        assert not ConfigParser.all_sections_are_valid(config), (
            "Config should contain a disallowed sections"
        )


@pytest.mark.parametrize(
    "file_name",
    [
        "pass_basic.toml",
        "pass_empty.toml",
        "fail_bad_instrument.toml",
    ],
)
def test_invalid_instrument_not_dict_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert ConfigParser.all_instrument_values_are_dicts(config), (
            "Config should contain only valid instrument values"
        )
    elif "fail" in file_name:
        config = load_toml_file(file_name)
        assert not ConfigParser.all_instrument_values_are_dicts(config), (
            "Config should contain invalid instrument values"
        )


@pytest.mark.parametrize(
    "file_name",
    [
        "pass_basic.toml",
        "pass_empty.toml",
        "fail_instrument_missing_instrument_key.toml",
    ],
)
def test_invalid_instrument_missing_key_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert ConfigParser.all_instrument_dicts_contain_instrument(config), (
            "Config should contain only valid instrument values"
        )
    elif "fail" in file_name:
        config = load_toml_file(file_name)
        assert not ConfigParser.all_instrument_dicts_contain_instrument(config), (
            "Config should contain invalid instrument values"
        )


@pytest.mark.parametrize(
    "files",
    [
        ("pass", "pass_basic.toml"),
        ("pass", "pass_empty.toml"),
        ("fail", "fail_instrument_not_in_map.toml"),
    ],
)
def test_invalid_instrument_not_in_map_toml(load_toml_file, files):
    if files[0] == "pass":
        config = load_toml_file(files[1])
        assert ConfigParser.all_instruments_in_instrument_map(config), (
            "Config should contain only valid instrument keys"
        )
    elif files[0] == "fail":
        config = load_toml_file(files[1])
        assert not ConfigParser.all_instruments_in_instrument_map(config), (
            "Config should contain invalid instrument keys"
        )


@pytest.mark.parametrize(
    "file_name",
    [
        "pass_basic.toml",
        "pass_empty.toml",
        "fail_measurement_not_dict.toml",
    ],
)
def test_invalid_measurement_not_dict_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert ConfigParser.all_measurement_values_are_dicts(config), (
            "Config should contain only valid measurement values"
        )
    elif "fail" in file_name:
        config = load_toml_file(file_name)
        assert not ConfigParser.all_measurement_values_are_dicts(config), (
            "Config should contain invalid measurement values"
        )


@pytest.mark.parametrize(
    "file_name",
    [
        "pass_basic.toml",
        "pass_empty.toml",
        "fail_measurement_missing_instrument_key.toml",
    ],
)
def test_invalid_measurement_missing_key_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert ConfigParser.all_measurement_dicts_contain_instrument(config), (
            "Config should contain only valid measurement values"
        )
    elif "fail" in file_name:
        config = load_toml_file(file_name)
        assert not ConfigParser.all_measurement_dicts_contain_instrument(config), (
            "Config should contain invalid measurement values"
        )


@pytest.mark.parametrize(
    "file_name",
    [
        "pass_basic.toml",
        "pass_empty.toml",
        "fail_measurement_with_unknown_instrument.toml",
    ],
)
def test_invalid_measurement_unknown_instrument_toml(load_toml_file, file_name):
    if "pass" in file_name:
        config = load_toml_file(file_name)
        assert ConfigParser.all_measurement_instruments_exist(config), (
            "Config should contain only valid instrument values"
        )
    elif "fail" in file_name:
        config = load_toml_file(file_name)
        assert not ConfigParser.all_measurement_instruments_exist(config), (
            "Config should contain invalid instrument values"
        )


# -------------------------------------------------------------- [calculations]
def test_a_calculations_section_is_valid(load_toml_file):
    config = load_toml_file("pass_calculations.toml")

    assert ConfigParser.validate(config) is config


def test_an_unknown_calculation_is_refused(load_toml_file):
    config = load_toml_file("fail_calculation_unknown_kind.toml")

    with pytest.raises(
        InvalidCalculationError, match="no calculation called 'RollingMedian'"
    ):
        ConfigParser.validate(config)


MEASURED = {"x": {"instrument": "clock", "method": "time"}}


def with_calculations(calculations):
    return {
        "instruments": {"clock": {"instrument": "Clock"}},
        "measurements": MEASURED,
        "calculations": calculations,
    }


@pytest.mark.parametrize(
    "calculations, message",
    [
        ({"s": {"inputs": ["x"]}}, "needs `calculation`"),
        ({"s": {"calculation": "Sum"}}, "a Sum needs `inputs`"),
        ({"m": {"calculation": "RollingMean", "column": "x"}}, "needs `window`"),
        (
            {"s": {"calculation": "Sum", "inputs": ["x"], "window": 3}},
            "unknown key 'window'",
        ),
        (
            {"m": {"calculation": "RollingMean", "column": "x", "window": 0}},
            "`window` must be a whole number of at least 1, got 0",
        ),
        (
            {"m": {"calculation": "RollingMean", "column": "x", "window": 2.5}},
            "`window` must be a whole number",
        ),
        (
            {"m": {"calculation": "RollingMean", "column": "x", "window": True}},
            "`window` must be a whole number",
        ),
        ({"s": {"calculation": "Sum", "inputs": []}}, "a list of one or more"),
        ({"s": {"calculation": "Sum", "inputs": "x"}}, "a list of one or more"),
        (
            {"s": {"calculation": "Sum", "inputs": ["x"], "unit": 1}},
            "`unit` must be text",
        ),
        ({"s": "Sum"}, "must be a table"),
        ({"x": {"calculation": "Sum", "inputs": ["x"]}}, "same name as a column"),
        (
            {"s": {"calculation": "Sum", "inputs": ["x", "y"]}},
            "names 'y', which is not a measurement or a calculation above",
        ),
        (
            # A column used before the calculation that makes it.
            {
                "m": {"calculation": "RollingMean", "column": "s", "window": 2},
                "s": {"calculation": "Sum", "inputs": ["x"]},
            },
            "Calculation 'm': `column` names 's'",
        ),
    ],
)
def test_a_calculation_that_cant_be_made_is_refused(calculations, message):
    with pytest.raises(InvalidCalculationError, match=re.escape(message)):
        ConfigParser.validate(with_calculations(calculations))


def test_a_calculation_can_use_the_ones_above_it():
    config = with_calculations(
        {
            "s": {"calculation": "Sum", "inputs": ["x", "x"]},
            "m": {"calculation": "RollingMean", "column": "s", "window": 2},
        }
    )

    assert ConfigParser.validate(config) is config


def test_every_problem_is_found_with_where_it_is():
    from pyacquisition.core.calculations import config_problems

    problems = list(
        config_problems(
            {
                "s": {"calculation": "Sum", "inputs": ["y"], "colour": "red"},
                "m": {"calculation": "RollingMean", "column": "x", "window": 0},
            },
            ["x"],
        )
    )

    assert [where for where, _ in problems] == [
        ("s", "colour"),
        ("s", "inputs"),
        ("m", "window"),
    ]


# -------------------------------------------------------------------- [traces]
def test_an_unknown_reduction_is_refused(load_toml_file):
    config = load_toml_file("fail_trace_unknown_reduction.toml")

    with pytest.raises(InvalidTraceError, match="Trace 'spectrum': there is no reduction 'median'"):
        ConfigParser.validate(config)


def with_traces(traces):
    return {"instruments": {"vna": {"instrument": "Clock"}}, "traces": traces}


SWEEP = {"instrument": "vna", "method": "get_sweep"}


def test_a_traces_section_is_valid():
    entry = {**SWEEP, "every_rows": 10, "reduce": ["mean", "peak_x"], "reduce_units": {"mean": "V"},
             "x_unit": "Hz", "args": {"points": 256}}
    config = with_traces({"sweep": entry})

    assert ConfigParser.validate(config) is config


@pytest.mark.parametrize(
    "entry, message",
    [
        ("vna.get_sweep", "must be a table"),
        ({"method": "get_sweep"}, "needs `instrument`"),
        ({"instrument": "vna"}, "needs `method`"),
        ({**SWEEP, "instrument": "sa"}, "there is no instrument 'sa'"),
        ({**SWEEP, "colour": "red"}, "has 'colour', which a trace doesn't take"),
        ({**SWEEP, "every": 0}, "`every` must be a number of seconds above 0"),
        ({**SWEEP, "timeout": "long"}, "`timeout` must be a number of seconds above 0"),
        ({**SWEEP, "every_rows": 0}, "`every_rows` must be a whole number from 1"),
        ({**SWEEP, "every_rows": 2.5}, "`every_rows` must be a whole number from 1"),
        ({**SWEEP, "every": 5, "every_rows": 2}, "not both"),
        ({**SWEEP, "unit": 1}, "`unit` must be text"),
        ({**SWEEP, "args": [1]}, "`args` must be a table"),
        ({**SWEEP, "reduce": "mean"}, "`reduce` must be a list"),
        ({**SWEEP, "reduce_units": {"mean": 1}}, "`reduce_units` must be a table of units"),
        ({**SWEEP, "channels": []}, "`channels` must be a list of names"),
    ],
)
def test_a_trace_that_cant_be_taken_is_refused(entry, message):
    with pytest.raises(InvalidTraceError, match=re.escape(message)):
        ConfigParser.validate(with_traces({"sweep": entry}))
