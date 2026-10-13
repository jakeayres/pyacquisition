"""The tasks that wait on a measurement: WaitForValue and WaitForStable, the feed
of readings they follow, and the stability check.

Rows are fed in through the experiment's `History`, as the rack's would arrive,
and the time each one arrives is a fake clock that the test moves on.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment, Measurement, Task
from pyacquisition.instruments import Clock
from pyacquisition.tasks import WaitForStable, WaitForValue, reading_tasks
from pyacquisition.tasks import readings as readings_module
from pyacquisition.tasks.readings import Readings, Stability, slope
from pyacquisition.tasks.wait import Condition


async def until(condition, timeout: float = 2.0):
    end = asyncio.get_running_loop().time() + timeout
    while not condition():
        assert asyncio.get_running_loop().time() < end, "timed out"
        await asyncio.sleep(0.002)


@pytest.fixture
def fast(monkeypatch):
    """Makes `self.sleep` a thousand times shorter, keeping its pause and abort."""
    real = Task.sleep

    async def quick(self, seconds):
        await real(self, seconds / 1000)

    monkeypatch.setattr(Task, "sleep", quick)


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(readings_module, "clock", fake)
    return fake


@pytest.fixture
def experiment(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    timer = Clock("clock")
    experiment.add_instrument(timer)
    experiment.add_measurement(Measurement("T", timer.time, unit="K"))
    experiment.add_calculation(lambda row: {"R": 1.0}, units={"R": "ohm"})
    return experiment


def feed(experiment, clock, *values, every=1.0, column="T"):
    """Rows with these values of the column, `every` seconds apart."""
    for value in values:
        clock.now += every
        experiment._history.add_row({column: value})


async def started(task, experiment):
    """Starts the task, and returns once it is following the readings."""
    runner = asyncio.ensure_future(task.start(experiment))
    await until(lambda: getattr(task, "_readings", None) is not None)
    return runner


def subscribed(experiment):
    return [s for s in experiment._history._subscribers if isinstance(s, Readings)]


def note(task):
    return (task.progress or {}).get("note")


# ------------------------------------------------------------------ slope
def test_slope_is_the_least_squares_line():
    assert slope([(0, 1.0), (1, 3.0), (2, 5.0)]) == pytest.approx(2.0)
    assert slope([(0, 1.0), (1, 2.0), (2, 1.0), (3, 2.0)]) == pytest.approx(0.2)


def test_slope_needs_two_times():
    assert slope([]) is None
    assert slope([(0, 1.0)]) is None
    assert slope([(5, 1.0), (5, 2.0)]) is None


# ------------------------------------------------------------- the feed
def test_the_feed_follows_the_rows_only_inside_its_block(experiment, clock):
    with Readings(experiment, "T") as readings:
        assert subscribed(experiment) == [readings]
        feed(experiment, clock, 4.0, 4.5)
        assert readings.new() == [(1001.0, 4.0), (1002.0, 4.5)]
        assert readings.new() == []
    assert subscribed(experiment) == []
    feed(experiment, clock, 5.0)
    assert readings.new() == []


def test_the_feed_skips_missing_readings_and_other_events(experiment, clock):
    with Readings(experiment, "T") as readings:
        feed(experiment, clock, None, float("nan"), float("inf"), "error", True, 3.0)
        experiment._history.new_file("next")
        feed(experiment, clock, 2.0, column="R")  # a row without T
        assert readings.new() == [(1006.0, 3.0)]


def test_the_feed_can_drop_what_has_arrived(experiment, clock):
    with Readings(experiment, "T") as readings:
        feed(experiment, clock, 1.0, 2.0)
        readings.clear()
        feed(experiment, clock, 3.0)
        assert [value for _, value in readings.new()] == [3.0]


def test_the_feed_knows_the_unit(experiment):
    assert Readings(experiment, "T").unit == "K"
    assert Readings(experiment, "R").unit == "ohm"


def test_a_column_the_rows_have_had_is_known_too(experiment, clock):
    # A calculation that doesn't name its columns, which only its rows show.
    feed(experiment, clock, 0.5, column="ratio")
    assert Readings(experiment, "ratio").unit == ""


def test_a_column_that_does_not_exist_is_refused_with_those_that_do(experiment):
    with pytest.raises(ValueError, match="no column called 'Q': there is 'T', 'R'."):
        Readings(experiment, "Q")


# --------------------------------------------------------- the check
def steady(check, values, start=0.0, every=1.0):
    for i, value in enumerate(values):
        check.add(start + i * every, value)


def test_noise_inside_the_band_is_stable_after_a_whole_hold():
    check = Stability(tolerance=0.1, hold=10)
    steady(check, [5.0, 5.05, 4.95, 5.1, 4.9, 5.0, 5.05, 4.95, 5.0, 5.0])  # 0 to 9 s
    assert check.in_band_for == 9
    assert not check.stable
    check.add(10, 5.0)
    assert check.in_band_for == 10
    assert check.stable


def test_one_reading_outside_the_band_starts_the_time_again():
    check = Stability(tolerance=0.1, hold=10, target=5.0)
    steady(check, [5.0] * 8)  # 0 to 7 s
    check.add(8, 5.5)
    assert check.in_band_for == 0
    steady(check, [5.0] * 10, start=9)  # 9 to 18 s
    assert check.in_band_for == 9
    assert not check.stable
    check.add(19, 5.0)
    assert check.stable


def test_without_a_target_the_band_sits_wherever_the_readings_do():
    check = Stability(tolerance=0.1, hold=5)
    steady(check, [7.3, 7.4, 7.5, 7.4, 7.3, 7.4])  # 0.2 wide, off any setpoint
    assert check.stable
    check.add(6, 7.55)  # 7.3 to 7.55 is wider than 0.2
    assert check.in_band_for == 1  # back to the 7.4 at 5 s: the 7.3 at 4 s is too low
    assert not check.stable


def test_readings_on_the_edge_of_the_band_are_in_it():
    # Readings rounded to an instrument's resolution land on the edge, where
    # floats don't add up exactly: 7.5 - 7.3 is a little over 0.2.
    check = Stability(tolerance=0.1, hold=2, target=7.4)
    steady(check, [7.3, 7.5, 7.3])
    assert check.stable


def test_off_the_target_is_never_stable_however_steady():
    check = Stability(tolerance=0.1, hold=5, target=10.0)
    steady(check, [9.5] * 20)
    assert check.in_band_for == 0
    assert not check.stable


def test_a_slow_drift_inside_the_band_is_stable_only_without_max_drift():
    values = [5.0 + 0.01 * i for i in range(11)]  # 0.01 a second, 0.1 in all
    unchecked = Stability(tolerance=0.1, hold=10)
    checked = Stability(tolerance=0.1, hold=10, max_drift=0.005)
    steady(unchecked, values)
    steady(checked, values)
    assert unchecked.stable
    assert checked.in_band_for == 10
    assert checked.drift == pytest.approx(0.01)
    assert checked.drifting_too_fast
    assert not checked.stable
    assert Stability(tolerance=0.1, hold=10, max_drift=0.02).stable is False
    loose = Stability(tolerance=0.1, hold=10, max_drift=0.02)
    steady(loose, values)
    assert loose.stable


def test_gaps_in_the_readings_do_not_shorten_the_hold():
    check = Stability(tolerance=0.1, hold=10)
    check.add(0, 5.0)
    check.add(4, 5.0)  # the readings between failed
    check.add(10, 5.0)
    assert check.stable


def test_only_the_last_hold_is_kept_and_the_one_before_it():
    check = Stability(tolerance=0.1, hold=10, target=5.0)
    check.add(0, 9.0)  # far outside, and then older than the hold
    steady(check, [5.0] * 11, start=1.5)  # 1.5 to 11.5 s
    assert check.in_band_for == 10
    assert check.stable
    assert check._points[0][0] == 1.5


def test_clearing_starts_again():
    check = Stability(tolerance=0.1, hold=2)
    steady(check, [1.0, 1.0, 1.0])
    assert check.stable
    check.clear()
    assert check.in_band_for == 0
    assert check.drift is None
    assert not check.stable


@pytest.mark.parametrize(
    "inputs, error",
    [
        ({"tolerance": 0, "hold": 1}, "tolerance"),
        ({"tolerance": 1, "hold": 0}, "hold"),
        ({"tolerance": 1, "hold": 1, "max_drift": -1}, "max_drift"),
    ],
)
def test_the_check_refuses_what_makes_no_sense(inputs, error):
    with pytest.raises(ValueError, match=error):
        Stability(**inputs)


# ------------------------------------------------------- WaitForValue
@pytest.mark.asyncio
async def test_it_waits_until_the_reading_is_below(experiment, clock, fast):
    task = WaitForValue("T", Condition.BELOW, 2.0)
    runner = await started(task, experiment)
    feed(experiment, clock, 5.0, 4.0, 3.0)
    await until(lambda: note(task) == "1 K to go")
    assert task.progress["fraction"] == pytest.approx(2 / 3)
    # 1 K a second. The time remaining counts down from when it was said, and the
    # clock may tick (15.6 ms on Windows) before it is read here.
    assert task.progress["remaining"] == pytest.approx(1.0, abs=0.1)
    assert not runner.done()
    feed(experiment, clock, 1.9)
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "completed"
    assert subscribed(experiment) == []


@pytest.mark.asyncio
async def test_it_waits_until_the_reading_is_above(experiment, clock, fast):
    task = WaitForValue("T", "ABOVE", 300.0)
    runner = await started(task, experiment)
    feed(experiment, clock, 290.0, 299.0, 300.0)
    await asyncio.sleep(0.05)
    assert not runner.done()  # 300 isn't above 300
    feed(experiment, clock, 300.5)
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "completed"


@pytest.mark.asyncio
async def test_a_reading_already_past_finishes_at_once(experiment, clock, fast):
    task = WaitForValue("T", "BELOW", 2.0)
    runner = await started(task, experiment)
    feed(experiment, clock, 1.5)
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "completed"


@pytest.mark.asyncio
async def test_with_a_hold_one_noisy_reading_does_not_end_it(experiment, clock, fast):
    task = WaitForValue("T", "BELOW", 2.0, hold=3)
    runner = await started(task, experiment)
    feed(experiment, clock, 1.9, 2.1, 1.9, 1.9, 1.9)  # past from the third, 2 s
    await until(lambda: note(task) == "Past 2 K for 2 of 3 s")
    assert task.progress["remaining"] == pytest.approx(1, abs=0.1)
    assert not runner.done()
    feed(experiment, clock, 1.9)
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "completed"


@pytest.mark.asyncio
async def test_a_timeout_fails_the_task_saying_where_it_got(experiment, clock, fast):
    task = WaitForValue("T", "BELOW", 2.0, timeout=0.05)  # 3 s
    runner = await started(task, experiment)
    feed(experiment, clock, 2.4)
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "failed"
    assert isinstance(task.failure, TimeoutError)
    assert str(task.failure) == (
        "Gave up after 0.05 min waiting until T is below 2: it is 2.4 K."
    )
    assert subscribed(experiment) == []


@pytest.mark.asyncio
async def test_a_timeout_can_carry_on_instead(experiment, clock, fast):
    task = WaitForValue("T", "BELOW", 2.0, timeout=0.05, continue_on_timeout=True)
    runner = await started(task, experiment)
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "completed"


@pytest.mark.asyncio
async def test_a_failed_task_pauses_its_queue(experiment, clock, fast):
    manager = experiment._task_manager
    run = asyncio.ensure_future(manager.run(experiment))
    try:
        manager.add_task(WaitForValue("T", "BELOW", 2.0, timeout=0.01))
        await until(lambda: manager._last_result is not None, timeout=3)
        assert manager._last_result["outcome"] == "failed"
        assert not manager._pause_event.is_set()
    finally:
        await manager.shutdown()
        await asyncio.wait_for(run, 2)


@pytest.mark.asyncio
async def test_an_abort_stops_following_the_readings(experiment, clock, fast):
    task = WaitForValue("T", "BELOW", 2.0)
    runner = await started(task, experiment)
    task.abort()
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "aborted"
    assert subscribed(experiment) == []


@pytest.mark.asyncio
async def test_readings_while_paused_are_dropped(experiment, clock, fast):
    task = WaitForValue("T", "BELOW", 2.0, hold=3)
    runner = await started(task, experiment)
    feed(experiment, clock, 1.9, 1.9)
    await until(lambda: note(task) == "Past 2 K for 1 of 3 s")
    task.pause()
    feed(experiment, clock, 1.9, 1.9, 1.9)  # enough, had they been seen
    task.resume()
    feed(experiment, clock, 1.9, 1.9, 1.9)
    await until(lambda: note(task) == "Past 2 K for 2 of 3 s")
    assert not runner.done()
    feed(experiment, clock, 1.9)
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "completed"


@pytest.mark.asyncio
async def test_it_says_when_there_is_nothing_to_go_on(experiment, clock, fast):
    task = WaitForValue("T", "BELOW", 2.0)
    runner = await started(task, experiment)
    await until(lambda: note(task) == "Waiting for a reading of T")
    experiment._rack.pause()
    await until(lambda: note(task) == "Measurements are paused")
    feed(experiment, clock, 3.0)
    await until(lambda: note(task) == "Measurements are paused")
    experiment._rack.resume()
    await until(lambda: note(task) == "1 K to go")
    task.abort()
    await asyncio.wait_for(runner, 2)


def test_value_inputs_are_checked():
    with pytest.raises(ValueError, match="not one of BELOW, ABOVE"):
        WaitForValue("T", "sideways", 1.0)
    with pytest.raises(ValueError, match="hold"):
        WaitForValue("T", "BELOW", 1.0, hold=-1)
    with pytest.raises(ValueError, match="timeout"):
        WaitForValue("T", "BELOW", 1.0, timeout=-1)


def test_the_value_description():
    assert WaitForValue("T", "below", 2).description == "Wait until T is below 2"
    assert WaitForValue("P", "ABOVE", 1e-5).description == "Wait until P is above 1e-05"


@pytest.mark.asyncio
async def test_an_unknown_measurement_fails_the_task(experiment, fast):
    task = WaitForValue("Q", "BELOW", 1.0)
    await task.start(experiment)
    assert task.outcome == "failed"
    assert "no column called 'Q'" in str(task.failure)


# ------------------------------------------------------ WaitForStable
@pytest.mark.asyncio
async def test_it_waits_until_stable_at_the_target(experiment, clock, fast):
    task = WaitForStable("T", tolerance=0.1, hold=0.1, target=10.0)  # 6 s
    runner = await started(task, experiment)
    feed(experiment, clock, 9.0, 9.5)
    await until(lambda: note(task) == "T is 9.5 K, outside 10 ± 0.1 K")
    feed(experiment, clock, 10.0, 10.05, 9.95, 10.0)
    await until(lambda: (note(task) or "").startswith("In the band for 0:03 of 0:06"))
    assert task.progress["fraction"] == pytest.approx(0.5)
    assert task.progress["remaining"] == pytest.approx(3, abs=0.1)
    feed(experiment, clock, 10.0, 10.0)
    await asyncio.sleep(0.05)
    assert not runner.done()
    feed(experiment, clock, 10.0)
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "completed"
    assert note(task).startswith("Stable at 10 K")
    assert subscribed(experiment) == []


@pytest.mark.asyncio
async def test_it_waits_while_drifting_too_fast(experiment, clock, fast):
    task = WaitForStable("T", tolerance=1.0, hold=0.1, max_drift=0.3)  # 6 s
    runner = await started(task, experiment)
    feed(experiment, clock, *[5.0 + 0.01 * i for i in range(8)])  # 0.6 K/min
    await until(lambda: "faster than 0.3 K/min" in (note(task) or ""))
    assert note(task) == "In the band for 0:06, drifting 0.6 K/min, faster than 0.3 K/min"
    feed(experiment, clock, *[5.07] * 7)
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "completed"


@pytest.mark.asyncio
async def test_a_resume_starts_the_time_again(experiment, clock, fast):
    task = WaitForStable("T", tolerance=0.1, hold=0.05)  # 3 s
    runner = await started(task, experiment)
    feed(experiment, clock, 5.0, 5.0, 5.0)
    await until(lambda: (note(task) or "").startswith("In the band for 0:02"))
    task.pause()
    feed(experiment, clock, 5.0, 5.0)
    task.resume()
    feed(experiment, clock, 5.0, 5.0)  # in the band for 6 s, had it not restarted
    await until(lambda: (note(task) or "").startswith("In the band for 0:01 of 0:03"))
    assert not runner.done()
    feed(experiment, clock, 5.0, 5.0)
    await asyncio.wait_for(runner, 2)
    assert task.outcome == "completed"


@pytest.mark.asyncio
async def test_stable_timeout_fails_or_carries_on(experiment, clock, fast):
    failing = WaitForStable("T", tolerance=0.1, hold=1, target=10, timeout=0.05)
    runner = await started(failing, experiment)
    feed(experiment, clock, 9.0)
    await asyncio.wait_for(runner, 2)
    assert failing.outcome == "failed"
    assert str(failing.failure) == (
        "Gave up after 0.05 min waiting until T is stable within 0.1 of 10 for 1 min: "
        "it is 9 K."
    )

    carrying_on = WaitForStable("T", 0.1, 1, timeout=0.05, continue_on_timeout=True)
    await carrying_on.start(experiment)
    assert carrying_on.outcome == "completed"


def test_stable_inputs_are_checked():
    with pytest.raises(ValueError, match="tolerance"):
        WaitForStable("T", tolerance=0, hold=1)
    with pytest.raises(ValueError, match="hold"):
        WaitForStable("T", tolerance=1, hold=0)
    with pytest.raises(ValueError, match="max_drift"):
        WaitForStable("T", tolerance=1, hold=1, max_drift=-1)
    with pytest.raises(ValueError, match="timeout"):
        WaitForStable("T", tolerance=1, hold=1, timeout=-1)


def test_the_stable_description():
    assert WaitForStable("T", 0.005, 5, target=10).description == (
        "Wait until T is stable within 0.005 of 10 for 5 min"
    )
    assert WaitForStable("T", 0.005, 5).description == (
        "Wait until T is stable within ±0.005 for 5 min"
    )


# ------------------------------------------------------- registration
def paths(experiment):
    return experiment._api_server.app.openapi()["paths"]


def parameters(experiment, path):
    operation = paths(experiment)[path]["get"]
    return {p["name"]: p for p in operation.get("parameters", [])}


def test_they_are_registered_with_the_columns_to_choose_from(experiment):
    assert "/tasks/waitforvalue" not in paths(experiment)  # not before setup
    experiment._register_reading_tasks()

    value = parameters(experiment, "/tasks/waitforvalue")
    assert value["measurement"]["schema"]["enum"] == ["T", "R"]
    assert value["condition"]["schema"]["enum"] == ["BELOW", "ABOVE"]
    stable = parameters(experiment, "/tasks/waitforstable")
    assert stable["measurement"]["schema"]["enum"] == ["T", "R"]
    assert not stable["target"]["required"]
    assert {"type": "null"} in stable["target"]["schema"]["anyOf"]
    assert "How many minutes the readings must stay" in stable["hold"]["description"]


def test_a_blank_target_is_none(experiment):
    experiment._register_reading_tasks()
    client = TestClient(experiment._api_server.app)
    reply = client.get(
        "/tasks/waitforstable", params={"measurement": "T", "tolerance": 0.1, "hold": 1}
    )
    assert reply.status_code == 200
    (task,) = list(experiment._task_manager._task_queue._queue)
    assert task.target is None
    assert task._queued_with["parameters"] == {
        "measurement": "T",
        "tolerance": 0.1,
        "hold": 1.0,
        "max_drift": 0.0,
        "target": None,
        "timeout": 0.0,
        "continue_on_timeout": False,
    }


def test_inputs_that_make_no_sense_are_refused_as_they_are_queued(experiment):
    experiment._register_reading_tasks()
    client = TestClient(experiment._api_server.app)
    reply = client.get(
        "/tasks/waitforstable", params={"measurement": "T", "tolerance": 0, "hold": 1}
    )
    assert reply.status_code == 422
    assert "tolerance must be above 0" in reply.text


def test_an_experiment_with_no_columns_has_neither(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    experiment._register_reading_tasks()
    assert not {"/tasks/waitforvalue", "/tasks/waitforstable"} & set(paths(experiment))


def test_a_registration_of_the_users_own_is_left_as_it_is(experiment):
    experiment.register_task(WaitForValue, measurement="T")
    experiment._register_reading_tasks()
    assert "measurement" not in parameters(experiment, "/tasks/waitforvalue")
    assert "/tasks/waitforstable" in paths(experiment)


def test_they_are_the_reading_tasks():
    assert reading_tasks == [WaitForValue, WaitForStable]
