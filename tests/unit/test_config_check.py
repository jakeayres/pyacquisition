"""Checking a config without running it (core/config_check.py): every problem,
with where it is, and none for a config that loads."""

import tomllib
from pathlib import Path

import pytest

from pyacquisition import Experiment
from pyacquisition.core.config_check import ConfigError, Problem, problems

TOML = Path(__file__).resolve().parents[1] / "toml"
EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def readable():
    """The test files that are TOML, and whether `from_config` loads each."""
    for path in sorted(TOML.glob("*.toml")):
        try:
            config = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            continue  # not TOML at all: the page can't open it either
        yield pytest.param(path, config, id=path.name)


def loads(path, tmp_path, monkeypatch) -> bool:
    monkeypatch.chdir(tmp_path)  # their logs and data go here
    try:
        Experiment.from_config(str(path), gui=False)
    except Exception:  # noqa: BLE001 - any refusal
        return False
    return True


@pytest.mark.parametrize("path, config", readable())
def test_a_file_that_is_refused_has_a_problem_and_one_that_loads_has_none(
    path, config, tmp_path, monkeypatch
):
    found = problems(config)

    if loads(path, tmp_path, monkeypatch):
        assert found == []
    else:
        assert found, f"{path.name} is refused, but no problem was found"
        assert all(isinstance(p, Problem) and p.where for p in found)


@pytest.mark.parametrize("name", ["front_page.toml", "calculations.toml"])
def test_the_examples_have_no_problems(name):
    assert problems(tomllib.loads((EXAMPLES / name).read_text(encoding="utf-8"))) == []


def where(config) -> list:
    return [p.where for p in problems(config)]


CLOCK = {"clock": {"instrument": "Clock"}}
LAKESHORE = {"ls": {"instrument": "Lakeshore_350", "adapter": "mock", "resource": "x"}}


def measuring(measurement, instruments=LAKESHORE):
    return {"instruments": instruments, "measurements": {"T": measurement}}


def test_every_problem_is_reported_not_only_the_first():
    config = {
        "rack": {"period": "fast", "perod": 1},
        "instruments": {"lockin": {"instrument": "SR_830"}},
        "measurements": {"x": {"instrument": "nowhere", "method": "get_x"}},
        "colours": {},
    }

    assert where(config) == [
        ("colours",),
        ("rack", "period"),
        ("rack", "perod"),
        ("instruments", "lockin", "adapter"),
        ("instruments", "lockin", "resource"),
        ("measurements", "x", "instrument"),
    ]


def test_an_option_says_what_is_wrong_by_its_toml_key():
    (problem,) = problems({"rack": {"period": -1}})

    assert problem.message == "`period` must be a positive number, got -1"


def test_a_misspelt_option_is_suggested():
    (problem,) = problems({"data": {"pth": "x"}})

    assert "did you mean 'path'" in problem.message


def test_a_removed_option_is_let_be():
    assert problems({"gui": {"sparkline_points": 50}}) == []


# ------------------------------------------------------------ instruments
def test_a_software_instrument_takes_no_adapter():
    config = {"instruments": {"clock": {"instrument": "Clock", "adapter": "mock"}}}

    assert where(config) == [("instruments", "clock", "adapter")]


def test_an_unknown_adapter_or_key_is_a_problem():
    config = {
        "instruments": {
            "ls": {"instrument": "Lakeshore_350", "adapter": "usb", "resource": "x", "colour": 1}
        }
    }

    assert where(config) == [("instruments", "ls", "colour"), ("instruments", "ls", "adapter")]


@pytest.mark.parametrize("timeout", ["5s", 0, -1, 2.5, True])
def test_a_timeout_must_be_whole_milliseconds(timeout):
    config = {"instruments": {"ls": {**LAKESHORE["ls"], "args": {"timeout": timeout}}}}

    assert where(config) == [("instruments", "ls", "args", "timeout")]


def test_a_termination_must_be_text():
    config = {"instruments": {"ls": {**LAKESHORE["ls"], "args": {"read_termination": 10}}}}

    assert where(config) == [("instruments", "ls", "args", "read_termination")]


def test_other_args_are_let_be():
    config = {"instruments": {"ls": {**LAKESHORE["ls"], "args": {"baud_rate": 9600}}}}

    assert problems(config) == []


def test_an_unknown_driver_is_a_problem():
    assert where({"instruments": {"x": {"instrument": "Mongolia"}}}) == [
        ("instruments", "x", "instrument")
    ]


@pytest.mark.parametrize("driver, meant", [("SR830", "SR_830"), ("signalgenerator", "SignalGenerator")])
def test_a_misspelt_driver_is_given_the_closest_name(driver, meant):
    (problem,) = problems({"instruments": {"x": {"instrument": driver}}})

    assert problem.message == (
        f"Instrument 'x': there is no driver called '{driver}' (did you mean '{meant}'?)."
    )


def test_a_driver_with_no_close_name_lists_them_all():
    (problem,) = problems({"instruments": {"x": {"instrument": "Mongolia"}}})

    assert problem.message.startswith(
        "Instrument 'x': there is no driver called 'Mongolia'. The drivers are Calculator, Clock,"
    )


# ------------------------------------------------------------ measurements
def test_a_measurement_of_a_query_with_enum_text_is_fine():
    config = measuring(
        {"instrument": "ls", "method": "get_temperature", "args": {"input_channel": "INPUT_A"}}
    )

    assert problems(config) == []


@pytest.mark.parametrize("text", ["Input A", "input_a"])
def test_enum_text_can_be_a_label_or_any_case(text):
    config = measuring(
        {"instrument": "ls", "method": "get_temperature", "args": {"input_channel": text}}
    )

    assert problems(config) == []


def test_args_are_checked_from_the_class():
    config = measuring(
        {
            "instrument": "ls",
            "method": "get_temperature",
            "args": {"input_channel": "INPUT_Z", "colour": "red"},
        }
    )

    found = problems(config)

    assert [p.where for p in found] == [
        ("measurements", "T", "args", "colour"),
        ("measurements", "T", "args", "input_channel"),
    ]
    assert "INPUT_A, INPUT_B" in found[1].message


def test_a_missing_argument_is_a_problem():
    config = measuring({"instrument": "ls", "method": "get_temperature"})

    assert where(config) == [("measurements", "T", "args", "input_channel")]


def test_an_argument_of_the_wrong_kind_is_a_problem():
    config = measuring(
        {"instrument": "ls", "method": "get_temperature", "args": {"input_channel": 3}}
    )

    assert where(config) == [("measurements", "T", "args", "input_channel")]


def test_a_command_can_not_be_measured():
    ips = {"ips": {"instrument": "Mercury_IPS", "adapter": "mock", "resource": "x"}}
    (problem,) = problems(measuring({"instrument": "ips", "method": "to_zero"}, ips))

    assert problem.where == ("measurements", "T", "method")
    assert "is a command" in problem.message


def test_any_query_can_be_measured_not_only_get_ones():
    config = measuring({"instrument": "clock", "method": "timestamp_ms"}, CLOCK)

    assert problems(config) == []


def test_an_unknown_method_lists_the_queries():
    (problem,) = problems(measuring({"instrument": "clock", "method": "tiem"}, CLOCK))

    assert "timestamp_ms" in problem.message


def test_a_unit_must_be_text():
    config = measuring({"instrument": "clock", "method": "time", "unit": 1}, CLOCK)

    assert where(config) == [("measurements", "T", "unit")]


# ------------------------------------------------------------ calculations
def test_a_calculation_problem_is_placed_in_its_section():
    config = {
        **measuring({"instrument": "clock", "method": "time"}, CLOCK),
        "calculations": {"m": {"calculation": "RollingMean", "column": "T", "window": 0}},
    }

    assert where(config) == [("calculations", "m", "window")]


def test_a_calculation_named_like_a_measurement_is_a_problem():
    config = {
        **measuring({"instrument": "clock", "method": "time"}, CLOCK),
        "calculations": {"T": {"calculation": "Sum", "inputs": ["T"]}},
    }

    assert where(config) == [("calculations", "T")]


def test_a_problem_is_json_for_the_page():
    assert Problem(("rack", "period"), "no").to_json() == {
        "where": ["rack", "period"],
        "message": "no",
    }


# ------------------------------------------------------------------ traces
@pytest.fixture
def generator(monkeypatch):
    """TraceGenerator as a driver (it joins the map when traces are shown)."""
    from pyacquisition.instruments import instrument_map
    from pyacquisition.instruments.software.trace_generator import TraceGenerator

    monkeypatch.setitem(instrument_map, "TraceGenerator", TraceGenerator)
    return {"gen": {"instrument": "TraceGenerator"}}


def tracing(entry, instruments):
    return {"instruments": instruments, "traces": {"spectrum": entry}}


def test_a_trace_of_a_driver_has_no_problems(generator):
    entry = {"instrument": "gen", "method": "get_spectrum", "every_rows": 5, "reduce": ["mean"]}

    assert problems(tracing(entry, generator)) == []


@pytest.mark.parametrize(
    "entry, place, message",
    [
        ({"instrument": "gen", "method": "get_centre"}, ("method",),
         "TraceGenerator has no trace 'get_centre'. Its traces are get_spectrum."),
        ({"instrument": "gen", "method": "get_spectrum", "args": {"colour": 1}}, ("args", "colour"),
         "get_spectrum takes no `colour`"),
        ({"instrument": "gen", "method": "get_spectrum", "reduce": ["median"]}, (),
         "there is no reduction 'median'"),
        ({"instrument": "vna", "method": "get_spectrum"}, (), "there is no instrument 'vna'"),
    ],
)
def test_a_trace_problem_is_placed_in_its_section(generator, entry, place, message):
    (problem,) = problems(tracing(entry, generator))

    assert problem.where == ("traces", "spectrum", *place)
    assert message in problem.message
    assert problem.message.startswith("Trace 'spectrum'")


def test_a_trace_of_a_clock_is_a_problem():
    (problem,) = problems(tracing({"instrument": "clock", "method": "time"}, CLOCK))

    assert problem.where == ("traces", "spectrum", "method")
    assert "Its traces are none" in problem.message


# ------------------------------------------------------------------ a file
def test_a_file_with_problems_is_refused_listing_every_one(tmp_path):
    path = tmp_path / "rig.toml"
    path.write_text(
        '[rack]\nperiod = "fast"\n\n[instruments]\n'
        'lockin = {instrument = "SR830", adapter = "mock", resource = "x"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as refused:
        Experiment.from_config(str(path), gui=False)

    # An option's message is led by its place, which the rest say themselves.
    assert str(refused.value) == (
        f"{path} has 2 problems:\n"
        "  - [rack] period: `period` must be a positive number, got 'fast'\n"
        "  - Instrument 'lockin': there is no driver called 'SR830' (did you mean 'SR_830'?)."
    )
    assert [p.where for p in refused.value.problems] == [
        ("rack", "period"),
        ("instruments", "lockin", "instrument"),
    ]
    assert isinstance(refused.value, ValueError)
