"""Usage › Calculate new columns (docs/usage/calculations.md): each version of
sample.py makes its experiment, and its calculations make the columns, units and
values the page says, and fail as it says."""

import importlib.util
import math
import sys
from pathlib import Path

import pytest
from loguru import logger

from pyacquisition.core.calculations import Calculations

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "calculations"
SIMULATED = ROOT / "examples" / "simulated_rig"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.fixture
def simulated(monkeypatch):
    monkeypatch.syspath_prepend(str(SIMULATED))
    sys.modules.pop("simulated", None)


def module(version: int):
    spec = importlib.util.spec_from_file_location(f"calculations_sample_{version}", HERE / f"sample_{version}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def sample(version: int, tmp_path):
    experiment = module(version).Sample(root_path=str(tmp_path), gui=False)
    experiment.setup()
    return experiment


@pytest.fixture
def logged():
    """The warnings and errors logged while the test runs."""
    messages = []
    sink = logger.add(lambda message: messages.append(message.record["message"]), level="WARNING")
    yield messages
    logger.remove(sink)


def test_it_starts_from_tune_your_measurements_third_step():
    assert text(HERE / "sample_1.py") == text(ROOT / "examples" / "usage" / "measurements" / "sample_3.py")


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_each_version_sets_up(version, tmp_path, simulated):
    experiment = sample(version, tmp_path)
    assert list(experiment.measurements) == ["time", "x", "y", "T"]


def rows(experiment, count, **columns):
    """Runs the experiment's calculations on `count` rows made by `columns`, each a
    function of the row's number, and gives the rows back."""
    calculations = experiment._calculations
    return [calculations._apply({name: make(i) for name, make in columns.items()}) for i in range(count)]


def a_row(i):
    return {"time": lambda i: 0.25 * i, "x": lambda i: 1e-3 * (i % 2), "y": lambda i: 0.0, "T": lambda i: 20.0 - 0.25 * i}


def test_the_columns_are_the_measurements_then_the_calculations(tmp_path, simulated):
    made = rows(sample(4, tmp_path), 1, **a_row(0))
    assert list(made[0]) == ["time", "x", "y", "T", "x_mean10", "r", "T_rate"]


def test_the_units_are_volts_and_kelvin_per_minute(tmp_path, simulated):
    units = sample(4, tmp_path)._calculations.units
    assert units == {"x_mean10": "V", "r": "V", "T_rate": "K/min"}


def test_the_rolling_mean_is_empty_until_it_has_ten_values_then_smooths(tmp_path, simulated):
    made = rows(sample(2, tmp_path), 12, **a_row(0))
    assert all(math.isnan(row["x_mean10"]) for row in made[:9])
    assert made[9]["x_mean10"] == pytest.approx(0.5e-3)  # x alternates 0 and 1 mV


def test_r_is_the_size_of_the_signal(tmp_path, simulated):
    experiment = sample(3, tmp_path)
    (row,) = rows(experiment, 1, time=lambda i: 0.0, x=lambda i: 3e-3, y=lambda i: -4e-3, T=lambda i: 20.0)
    assert row["r"] == pytest.approx(5e-3)


def test_t_rate_is_how_fast_t_changes_per_minute_over_its_last_20_rows(tmp_path, simulated):
    made = rows(sample(4, tmp_path), 40, **a_row(0))  # T falls 1 K every second
    assert math.isnan(made[0]["T_rate"])  # one row: no rate yet
    assert made[1]["T_rate"] == pytest.approx(-60.0)
    assert made[39]["T_rate"] == pytest.approx(-60.0)
    rate = module(4).Rate("T", window=20, unit="K/min")
    for i in range(30):
        rate({"time": i, "T": 5.0})
    assert len(rate._rows) == 20  # the last 20 only
    assert rate({"time": 31, "T": 5.0}) == {"T_rate": 0.0}  # settled


def test_a_calculation_that_fails_is_logged_and_its_cells_are_empty(tmp_path, simulated, logged):
    experiment = sample(4, tmp_path)
    (row,) = rows(experiment, 1, time=lambda i: 0.0, x=lambda i: 1.0, Y=lambda i: 0.0, T=lambda i: 20.0)
    assert "[Calculations] Error in calculation magnitude: 'y'" in logged
    assert "r" not in row  # a function that fails on the first row: no column
    assert math.isnan(row["T_rate"])  # a Calculation keeps its column


def test_a_column_a_function_leaves_out_of_the_first_row_is_left_out_with_a_warning(logged):
    calculations = Calculations()
    answers = iter([{}, {"r": 1.0}])
    calculations.add_calculation(lambda row: next(answers))
    first = calculations._apply({"x": 1.0})
    second = calculations._apply({"x": 2.0})
    assert list(first) == list(second) == ["x"]
    assert "[Calculations] Column 'r' was not in the first row, so it is left out of the data." in logged


def test_a_function_s_units_must_be_a_dict():
    with pytest.raises(Exception, match=r'units must be a dict of column name to unit, such as \{"power": "W"\}'):
        Calculations().add_calculation(lambda row: {"r": 1.0}, units="V")
