import asyncio
import math
import pytest
import pandas as pd
from pyacquisition import Experiment, Measurement, RollingMean, Sum, Calculation
from pyacquisition.core.calculations import Calculations
from pyacquisition.core.consumer import Consumer
from pyacquisition.instruments.software import Clock


def test_no_calculations_passes_the_message_through():
    calculations = Calculations()
    message = {"a": 1}
    assert calculations._apply(message) == {"a": 1}


def test_lambda_adds_columns_and_keeps_raw_ones():
    calculations = Calculations()
    calculations.add_calculation(lambda row: {"c": row["a"] + row["b"]})
    assert calculations._apply({"a": 1, "b": 2}) == {"a": 1, "b": 2, "c": 3}


def test_message_is_not_changed():
    """The rack sends the same dict to every subscriber."""
    calculations = Calculations()
    calculations.add_calculation(lambda row: {"c": 1})
    message = {"a": 1}
    calculations._apply(message)
    assert message == {"a": 1}


def test_calculations_see_earlier_results():
    calculations = Calculations()
    calculations.add_calculation(lambda row: {"double": row["a"] * 2})
    calculations.add_calculation(lambda row: {"quad": row["double"] * 2})
    assert calculations._apply({"a": 1})["quad"] == 4


def test_rejects_non_callable():
    with pytest.raises(TypeError):
        Calculations().add_calculation("a + b")


def test_sum():
    calculations = Calculations()
    calculations.add_calculation(Sum("a", "b", "c"))
    assert calculations._apply({"a": 1, "b": 2, "c": 3})["a+b+c"] == 6


def test_sum_name():
    calculations = Calculations()
    calculations.add_calculation(Sum("a", "b", name="total"))
    assert calculations._apply({"a": 1, "b": 2})["total"] == 3


def test_sum_needs_columns():
    with pytest.raises(ValueError):
        Sum()


def test_sum_with_missing_value_is_nan():
    calculations = Calculations()
    calculations.add_calculation(Sum("a", "b", name="total"))
    assert math.isnan(calculations._apply({"a": 1, "b": None})["total"])


def test_rolling_mean_is_nan_until_window_is_full():
    calculations = Calculations()
    calculations.add_calculation(RollingMean("a", window=3))
    results = [calculations._apply({"a": v})["a_mean3"] for v in [1, 2, 3, 4, 5]]
    assert math.isnan(results[0]) and math.isnan(results[1])
    assert results[2:] == [2, 3, 4]


@pytest.mark.parametrize("window", [0, -1, 1.5, "3"])
def test_rolling_mean_rejects_bad_window(window):
    with pytest.raises(ValueError):
        RollingMean("a", window=window)


def test_failing_calculation_gives_nan_and_the_rest_carry_on():
    calculations = Calculations()
    calculations.add_calculation(Sum("a", "missing", name="total"))
    calculations.add_calculation(lambda row: {"double": row["a"] * 2})

    row = calculations._apply({"a": 1})
    assert math.isnan(row["total"])
    assert row["double"] == 2


def test_columns_are_fixed_by_the_first_row():
    """A function that only sometimes returns a column must not change the file."""
    calculations = Calculations()
    calculations.add_calculation(lambda row: {"x": 1} if row["a"] > 1 else {})

    first = calculations._apply({"a": 1})
    assert list(first) == ["a"]

    later = calculations._apply({"a": 2})
    assert list(later) == ["a"]


def test_missing_column_is_filled_with_nan():
    calculations = Calculations()
    calculations.add_calculation(lambda row: {"x": 1} if row["a"] == 1 else {})

    calculations._apply({"a": 1})
    row = calculations._apply({"a": 2})
    assert list(row) == ["a", "x"]
    assert math.isnan(row["x"])


def test_calculation_base_class_must_be_implemented():
    with pytest.raises(NotImplementedError):
        Calculation()({})


@pytest.mark.asyncio
async def test_run_broadcasts_calculated_rows():
    calculations = Calculations()
    calculations.add_calculation(Sum("a", "b", name="total"))
    consumer = Consumer()
    consumer.subscribe_to(calculations)

    task = asyncio.create_task(calculations.run(experiment=None))
    await calculations.queue.put({"a": 1, "b": 2})
    result = await consumer.consume(timeout=2)
    await calculations.shutdown()
    await asyncio.wait_for(task, timeout=2)

    assert result == {"a": 1, "b": 2, "total": 3}


def test_add_calculation_on_experiment(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    with pytest.raises(TypeError):
        experiment.add_calculation("not callable")


@pytest.mark.asyncio
async def test_calculated_columns_reach_the_data_file(tmp_path):
    class MyExperiment(Experiment):
        def setup(self):
            clock = Clock("clock")
            self.add_instrument(clock)
            self.add_measurement(Measurement("time", clock.timestamp_ms))
            self.add_calculation(Sum("time", "time", name="double_time"))
            self.add_calculation(RollingMean("time", window=2))

    experiment = MyExperiment(
        root_path=str(tmp_path),
        data_path="data",
        api_server_port=8124,
        measurement_period=0.05,
        gui=False,
    )

    async def stop_soon():
        await asyncio.sleep(1)
        experiment._shutdown_event.set()

    await asyncio.wait_for(asyncio.gather(experiment._run(), stop_soon()), timeout=20)

    (data_file,) = (tmp_path / "data").glob("*.data")
    data = pd.read_csv(data_file)
    assert list(data.columns) == ["time", "double_time", "time_mean2"]
    assert len(data) > 2
    assert (data["double_time"] == 2 * data["time"]).all()
