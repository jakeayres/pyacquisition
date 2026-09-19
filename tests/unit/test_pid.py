import asyncio
import math

import pytest

from pyacquisition import Task
from pyacquisition.tasks import PID, PIDController


# ---------------------------------------------------------------------------
# PIDController: the calculation
# ---------------------------------------------------------------------------


def run_controller(controller, setpoint, values, dt=1.0):
    return [controller.update(setpoint, v, dt) for v in values]


def test_proportional_output_starts_at_kp_times_error():
    controller = PIDController(kp=2.0)
    assert controller.update(10, 4, 1.0) == 12.0
    assert controller.update(10, 7, 1.0) == 6.0
    assert controller.error == 3


def test_the_integral_accumulates_ki_times_error_times_time():
    controller = PIDController(kp=0.0, ki=0.5)
    # The first update has no elapsed time, so nothing has been integrated yet.
    assert run_controller(controller, 1.0, [0, 0, 0, 0], dt=2.0) == [0, 1, 2, 3]


def test_the_integral_is_in_output_units_so_changing_ki_does_not_jump():
    controller = PIDController(kp=0.0, ki=1.0)
    run_controller(controller, 1.0, [0, 0, 0])
    before = controller.output

    controller.ki = 10.0
    assert controller.update(1.0, 0, 1.0) == before + 10.0  # only new time counts


def test_changing_the_setpoint_does_not_kick_the_output():
    controller = PIDController(kp=0.0, kd=5.0)
    run_controller(controller, 0.0, [3, 3, 3])
    assert controller.update(100.0, 3, 1.0) == 0.0


def test_the_derivative_opposes_a_rising_value():
    controller = PIDController(kp=0.0, kd=2.0)
    # The value rises 1 per second, so the error falls 1 per second.
    assert run_controller(controller, 0.0, [0, 1, 2, 3]) == [0, -2, -2, -2]


def test_the_derivative_filter_smooths_a_step():
    controller = PIDController(kp=0.0, kd=1.0, derivative_filter=1.0)
    controller.update(0.0, 0.0, 1.0)
    # A jump of 2 is a rate of -2. With alpha = dt / (tau + dt) = 0.5, half shows.
    assert controller.update(0.0, 2.0, 1.0) == pytest.approx(-1.0)
    assert controller.update(0.0, 2.0, 1.0) == pytest.approx(-0.5)


def test_output_limits():
    controller = PIDController(kp=10.0, output_min=0.0, output_max=5.0)
    assert controller.update(10, 0, 1.0) == 5.0
    assert controller.update(0, 10, 1.0) == 0.0


def test_no_limits_by_default():
    assert PIDController(kp=1000.0).update(10, 0, 1.0) == 10000.0


def test_the_integral_does_not_wind_up_at_a_limit():
    controller = PIDController(kp=0.0, ki=1.0, output_min=0.0, output_max=1.0)
    run_controller(controller, 10.0, [0] * 200)  # a large error, held for a long time
    assert controller.output == 1.0
    assert controller.i_term <= 1.0, "The integral should have stopped growing."

    # Once the error changes sign, the output leaves the limit straight away.
    assert controller.update(0.0, 1.0, 1.0) < 1.0


def test_windup_would_otherwise_delay_leaving_the_limit():
    """The same scenario with a huge limit shows why the check matters."""
    controller = PIDController(kp=0.0, ki=1.0)
    run_controller(controller, 10.0, [0] * 200)
    assert controller.i_term > 1000.0


def test_a_lower_limit_is_handled_the_same_way():
    controller = PIDController(kp=0.0, ki=1.0, output_min=-1.0, output_max=1.0)
    run_controller(controller, -10.0, [0] * 200)
    assert controller.output == -1.0
    assert controller.i_term >= -1.0
    assert controller.update(0.0, -1.0, 1.0) > -1.0


def test_inverted_raises_the_output_when_the_value_is_too_high():
    cooler = PIDController(kp=2.0, inverted=True)
    assert cooler.update(10, 15, 1.0) == 10.0  # too hot, so cool harder
    assert cooler.update(10, 5, 1.0) == -10.0  # too cold


def test_inverted_derivative_still_opposes_the_change():
    controller = PIDController(kp=0.0, kd=2.0, inverted=True)
    # A rising value is moving away from the target for a cooler... the error
    # (value minus setpoint) rises 1 per second, so the derivative is positive.
    assert run_controller(controller, 0.0, [0, 1, 2]) == [0, 2, 2]


def test_a_starting_output_makes_the_first_output_that_and_carries_on_smoothly():
    controller = PIDController(kp=3.0, ki=0.0)
    controller.reset(output=40.0)

    assert controller.update(10, 4, 1.0) == 40.0
    assert controller.update(10, 4, 1.0) == 40.0  # same error, same output
    assert controller.update(10, 3, 1.0) == 43.0  # then it follows the error


def test_a_starting_output_is_kept_within_the_limits():
    controller = PIDController(kp=1.0, output_max=50.0)
    controller.reset(output=80.0)
    assert controller.update(10, 4, 1.0) == 50.0


def test_reset_forgets_everything():
    controller = PIDController(kp=0.0, ki=1.0)
    run_controller(controller, 1.0, [0, 0, 0])
    controller.reset()
    assert controller.output == 0.0
    assert controller.update(1.0, 0, 1.0) == 0.0


def test_no_elapsed_time_changes_nothing():
    controller = PIDController(kp=1.0, ki=1.0, kd=1.0)
    run_controller(controller, 5.0, [0, 1])
    before = controller.output
    assert controller.update(5.0, 2, 0.0) == before
    assert controller.update(5.0, 2, -1.0) == before


def test_max_dt_limits_how_much_one_long_gap_can_integrate():
    controller = PIDController(kp=0.0, ki=1.0, max_dt=2.0)
    controller.update(1.0, 0, 1.0)
    assert controller.update(1.0, 0, 1000.0) == 2.0


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_a_value_that_is_not_a_number_is_rejected(bad):
    controller = PIDController()
    with pytest.raises(ValueError):
        controller.update(1.0, bad, 1.0)
    with pytest.raises(ValueError):
        controller.update(bad, 1.0, 1.0)


def test_the_parts_of_the_output_are_available():
    controller = PIDController(kp=2.0, ki=1.0, kd=1.0)
    run_controller(controller, 10.0, [0, 2], dt=1.0)
    assert controller.p_term == 16.0
    assert controller.d_term == -2.0
    assert controller.i_term == 8.0  # the error was 8 by the second update


def simulate(
    controller, setpoint, seconds=200, dt=0.1, tau=5.0, gain=2.0, disturbance=0.0
):
    """A first-order plant, dy/dt = (-y + gain * u) / tau, controlled from y = 0."""
    y = 0.0
    peak = 0.0
    for _ in range(int(seconds / dt)):
        u = controller.update(setpoint, y, dt)
        y += dt * (-y + gain * u + disturbance) / tau
        peak = max(peak, y)
    return y, peak


def test_pi_control_removes_the_steady_state_error():
    y, peak = simulate(PIDController(kp=1.5, ki=0.5), setpoint=10.0)
    assert y == pytest.approx(10.0, rel=0.01)
    assert peak < 12.5, "It should not overshoot badly."


def test_proportional_only_leaves_a_steady_state_error():
    y, _ = simulate(PIDController(kp=1.5), setpoint=10.0)
    assert y == pytest.approx(10.0 * 3 / 4, rel=0.01)  # gain*kp / (1 + gain*kp)


def test_integral_action_rejects_a_disturbance():
    y, _ = simulate(PIDController(kp=1.5, ki=0.5), setpoint=10.0, disturbance=-3.0)
    assert y == pytest.approx(10.0, rel=0.01)


def test_a_limited_output_still_reaches_the_setpoint_without_a_big_overshoot():
    controller = PIDController(kp=1.5, ki=0.5, output_min=0.0, output_max=8.0)
    y, peak = simulate(controller, setpoint=10.0, seconds=400)
    assert y == pytest.approx(10.0, rel=0.01)
    assert peak < 11.0


def test_a_cooler_is_controlled_with_inverted():
    controller = PIDController(kp=1.5, ki=0.5, inverted=True)
    y = 30.0
    for _ in range(2000):
        u = controller.update(10.0, y, 0.1)
        y += 0.1 * (-(y - 30.0) - 2.0 * u) / 5.0  # more output pulls the value down
    assert y == pytest.approx(10.0, rel=0.01)


# ---------------------------------------------------------------------------
# PID: the task
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Plant:
    """A first-order plant that advances the clock by one period on every read,
    so each cycle takes exactly one period without any real waiting."""

    def __init__(self, clock, period=1.0, tau=5.0, gain=2.0, on_read=None):
        self.clock, self.period, self.tau, self.gain = clock, period, tau, gain
        self.on_read = on_read
        self.y = 0.0
        self.u = 0.0
        self.reads = 0
        self.writes = []

    def read(self):
        self.reads += 1
        self.clock.now += self.period  # time passes even if the read then fails
        self.y += self.period * (-self.y + self.gain * self.u) / self.tau
        if self.on_read:
            self.on_read(self)
        return self.y

    def write(self, u):
        self.u = u
        self.writes.append(u)


@pytest.fixture
def clock():
    return FakeClock()


def make(clock, plant=None, **kwargs):
    plant = plant or Plant(clock)
    settings = dict(setpoint=10.0, kp=1.5, ki=0.5, time_source=clock)
    settings.update(kwargs)
    return PID(plant.read, plant.write, **settings), plant


async def run(task, timeout=10):
    await asyncio.wait_for(task.start(), timeout=timeout)


@pytest.mark.asyncio
async def test_it_brings_the_plant_to_the_setpoint(clock):
    pid, plant = make(clock, duration=200, output_min=0, output_max=50)

    await run(pid)

    assert plant.y == pytest.approx(10.0, rel=0.02)
    assert 190 <= plant.reads <= 210


@pytest.mark.asyncio
async def test_it_writes_the_final_output_when_it_ends(clock):
    pid, plant = make(clock, duration=20, final_output=-1.0)

    await run(pid)

    assert plant.writes[-1] == -1.0
    assert plant.writes[-2] != -1.0


@pytest.mark.asyncio
async def test_it_writes_the_final_output_when_aborted(clock):
    plant = Plant(clock, on_read=lambda p: pid.abort() if p.reads == 30 else None)
    pid, _ = make(clock, plant, final_output=0.0)

    await run(pid)

    assert plant.reads == 30, "It should stop at the next step after the abort."
    assert plant.writes[-1] == 0.0


@pytest.mark.asyncio
async def test_the_setpoint_can_be_changed_while_it_runs(clock):
    def change(p):
        if p.reads == 150:
            pid.setpoint = 20.0

    plant = Plant(clock, on_read=change)
    pid, _ = make(clock, plant, duration=400)

    await run(pid)

    assert plant.y == pytest.approx(20.0, rel=0.02)


@pytest.mark.asyncio
async def test_the_gains_can_be_changed_while_it_runs(clock):
    def change(p):
        if p.reads == 3:
            pid.kp = 5.0

    plant = Plant(clock, on_read=change)
    plant.read = lambda: (Plant.read(plant), 0.0)[1]  # the value stays at 0
    pid, _ = make(clock, plant, ki=0.0, setpoint=1.0, kp=2.0, duration=6)

    await run(pid)

    # Set during the third read, so it applies from the fourth cycle.
    assert plant.writes[:5] == [2.0, 2.0, 2.0, 5.0, 5.0]


@pytest.mark.asyncio
async def test_a_long_gap_does_not_add_a_huge_integral_step(clock):
    """A paused task resumes after a long time. The gap must not count in full."""

    def jump(p):
        if p.reads == 5:
            clock.now += 1000.0
        if p.reads == 9:
            pid.abort()

    plant = Plant(clock, on_read=jump)
    plant.read = lambda: (Plant.read(plant), 0.0)[1]  # error stays at 1
    pid, _ = make(clock, plant, kp=0.0, ki=1.0, setpoint=1.0, period=1.0)

    await run(pid)

    steps = [
        b - a for a, b in zip(plant.writes[:-1], plant.writes[1:-1])
    ]  # not the final
    assert max(steps) == pytest.approx(5.0)  # 5 periods at most, not 1000
    assert steps.count(1.0) >= 4, "The other cycles are one period each."


@pytest.mark.asyncio
async def test_a_failed_cycle_leaves_the_output_alone_and_it_carries_on(clock):
    def fail(p):
        if p.reads in (3, 4):
            raise OSError("timeout")

    plant = Plant(clock, on_read=fail)
    pid, _ = make(clock, plant, duration=10, max_failures=3, final_output=-1.0)

    await run(pid)

    assert plant.reads == 10
    assert len(plant.writes) == 10 - 2 + 1  # none for the two failed cycles, then final
    assert plant.writes[-1] == -1.0


@pytest.mark.asyncio
async def test_a_value_that_is_not_a_number_counts_as_a_failure(clock):
    plant = Plant(clock)
    values = iter([1.0, math.nan, None, 2.0, 3.0])

    def read():
        clock.now += 1.0
        return next(values)

    pid = PID(
        read,
        plant.write,
        setpoint=10.0,
        max_failures=5,
        duration=0,
        time_source=clock,
    )

    class Runs(Task):
        async def run(self, experiment=None):
            try:
                await self.run_subtask(pid)
            except RuntimeError:
                pass
            yield None

    # Runs out of values (StopIteration is an error too), so it fails in the end.
    await run(Runs())
    assert len(plant.writes) == 3 + 1  # three good cycles, then the final output


@pytest.mark.asyncio
async def test_too_many_failures_in_a_row_stop_it_with_an_error(clock):
    def fail(p):
        raise OSError("timeout")

    plant = Plant(clock, on_read=fail)
    pid, _ = make(clock, plant, max_failures=3, final_output=-1.0)
    caught = []

    class Runs(Task):
        async def run(self, experiment=None):
            try:
                await self.run_subtask(pid)
            except RuntimeError as e:
                caught.append(e)
            yield None

    await run(Runs())

    assert len(caught) == 1 and "3 failed cycles" in str(caught[0])
    assert plant.reads == 3
    assert plant.writes == [-1.0], "It should still leave a safe output."


@pytest.mark.asyncio
async def test_a_failure_that_is_followed_by_success_resets_the_count(clock):
    def fail(p):
        if p.reads % 3 == 0:  # every third read fails, never two in a row
            raise OSError("timeout")

    plant = Plant(clock, on_read=fail)
    pid, _ = make(clock, plant, duration=30, max_failures=2)

    await run(pid)  # would raise if the count were not reset

    assert plant.reads >= 30


@pytest.mark.asyncio
async def test_a_failing_write_is_a_failed_cycle_and_teardown_survives_it(clock):
    plant = Plant(clock)
    calls = []

    def write(u):
        calls.append(u)
        raise OSError("disconnected")

    pid = PID(plant.read, write, setpoint=10.0, max_failures=2, time_source=clock)
    caught = []

    class Runs(Task):
        async def run(self, experiment=None):
            try:
                await self.run_subtask(pid)
            except RuntimeError as e:
                caught.append(e)
            yield None

    await run(Runs())

    assert len(caught) == 1
    assert len(calls) == 3, "Two failed cycles, and one attempt at the final output."


@pytest.mark.asyncio
async def test_it_can_take_over_from_an_output_that_is_already_applied(clock):
    pid, plant = make(clock, initial_output=30.0, duration=3, ki=0.0, kp=1.0)

    await run(pid)

    assert plant.writes[0] == 30.0
    assert plant.writes[1] == pytest.approx(30.0 + (10.0 - plant.y) - 10.0 + 0.0, abs=5)


@pytest.mark.asyncio
async def test_it_exposes_its_state_for_logging(clock):
    pid, plant = make(clock, duration=5)
    assert math.isnan(pid.process_value)

    await run(pid)

    assert pid.process_value == plant.y
    assert pid.error == pytest.approx(10.0 - plant.y)
    assert isinstance(pid.output, float)


@pytest.mark.asyncio
async def test_it_stops_when_a_block_using_alongside_ends(clock):
    pid, plant = make(clock, final_output=-1.0)  # no duration: it never ends itself

    class Runs(Task):
        async def run(self, experiment=None):
            async with self.alongside(pid):
                for _ in range(20):
                    await asyncio.sleep(0)
                    yield None

    parent = Runs()
    await run(parent)

    assert plant.reads > 0
    assert plant.writes[-1] == -1.0
    reads = plant.reads
    await asyncio.sleep(0.05)
    assert plant.reads == reads, "It should not still be running."


def test_the_label_is_its_name(clock):
    pid, _ = make(clock, label="heater")
    assert pid.name == "heater"
    assert make(clock)[0].name == "PID"


def test_an_output_or_measured_value_can_be_any_function(clock):
    seen = []
    pid = PID(lambda: 1, seen.append, setpoint=2.0, time_source=clock)
    assert callable(pid.read) and callable(pid.write)


@pytest.mark.parametrize(
    "kwargs, error",
    [
        (dict(read="thermometer"), TypeError),
        (dict(write=None), TypeError),
        (dict(period=0), ValueError),
        (dict(period=-1), ValueError),
        (dict(duration=-1), ValueError),
        (dict(max_failures=0), ValueError),
        (dict(output_min=5, output_max=1), ValueError),
    ],
)
def test_bad_settings_are_rejected(clock, kwargs, error):
    settings = dict(read=lambda: 0.0, write=lambda u: None, setpoint=1.0)
    settings.update(kwargs)
    with pytest.raises(error):
        PID(**settings)


# --- what the interface shows ---


def test_parameters_show_the_settings_before_it_has_read_anything(clock):
    pid, _ = make(clock)
    assert pid.parameters == {"setpoint": 10.0, "kp": 1.5, "ki": 0.5, "kd": 0.0}


@pytest.mark.asyncio
async def test_parameters_include_the_live_values_once_it_has_read(clock):
    pid, plant = make(clock, duration=5)

    await run(pid)

    parameters = pid.parameters
    assert list(parameters) == [
        "setpoint",
        "kp",
        "ki",
        "kd",
        "value",
        "output",
        "error",
    ]
    assert parameters["value"] == plant.y
    assert parameters["error"] == pytest.approx(10.0 - plant.y)
    assert all(math.isfinite(v) for v in parameters.values()), "They are sent as JSON."


def test_parameters_follow_changes_to_the_settings(clock):
    pid, _ = make(clock)
    pid.setpoint, pid.kp = 20.0, 3.0
    assert pid.parameters["setpoint"] == 20.0
    assert pid.parameters["kp"] == 3.0


def test_the_display_of_a_pid_carries_its_parameters(clock):
    pid, _ = make(clock, label="furnace")
    display = pid.display_dict()
    assert display["name"] == "furnace"
    assert display["description"] == "Hold 10.0 with a PID controller"
    assert display["parameters"]["setpoint"] == 10.0
