"""The PIDController instrument (instruments/software/pid_controller.py): the
controls of a running PID task, as an instrument. Its queries read the PID's
settings and live values, its commands change them, refusing what the PID can't
take, and the interface can call both."""

import asyncio
import math

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import PIDController, instrument_map
from pyacquisition.tasks import PID


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def pid():
    clock = FakeClock()
    values = iter([2.0, 3.0, 4.0])

    def read():
        clock.now += 1.0
        return next(values)

    return PID(
        read=read, write=lambda output: None, setpoint=5.0, kp=1.0, ki=0.5,
        output_min=0.0, output_max=100.0, duration=3, time_source=clock,
    )


@pytest.fixture
def controller(pid):
    return PIDController("pid", pid)


def test_every_public_method_is_a_query_or_a_command_and_says_what_it_does():
    for name, member in vars(PIDController).items():
        if name.startswith("_") or not callable(member):
            continue
        assert hasattr(member, "_is_query") ^ hasattr(member, "_is_command"), name
        assert member.__doc__, name


def test_getters_are_queries_and_setters_are_commands():
    queries = {m.__name__ for m in PIDController._queries}
    commands = {m.__name__ for m in PIDController._commands}
    assert all(n.startswith("get_") for n in queries)
    assert all(n.startswith("set_") for n in commands)


def test_it_is_made_in_code_so_it_isnt_in_the_config_file_s_drivers():
    assert "PIDController" not in instrument_map


def test_the_queries_read_the_pid(controller):
    assert controller.get_setpoint() == 5.0
    assert (controller.get_p(), controller.get_i(), controller.get_d()) == (1.0, 0.5, 0.0)
    assert controller.get_pid() == {"p": 1.0, "i": 0.5, "d": 0.0}
    assert controller.get_output_limits() == {"output_min": 0.0, "output_max": 100.0}
    assert controller.get_period() == 1.0
    assert controller.get_ramp_rate() == 0.0
    assert math.isnan(controller.get_value())  # before its first cycle
    assert math.isnan(controller.get_ramped_setpoint())


def test_the_commands_change_the_pid(pid, controller):
    controller.set_setpoint(7.5)
    controller.set_p(2.0)
    controller.set_i(0.1)
    controller.set_d(0.3)
    controller.set_output_limits(10.0, 60.0)
    controller.set_period(0.5)
    controller.set_ramp_rate(12.0)
    assert (pid.setpoint, pid.kp, pid.ki, pid.kd) == (7.5, 2.0, 0.1, 0.3)
    assert (pid.output_min, pid.output_max, pid.period, pid.ramp_rate) == (10.0, 60.0, 0.5, 12.0)


def test_set_pid_sets_the_three_with_set_p_set_i_and_set_d(controller, monkeypatch):
    called = []
    for name in ("set_p", "set_i", "set_d"):
        original = getattr(controller, name)
        monkeypatch.setattr(controller, name, lambda value, n=name, o=original: called.append(n) or o(value))
    controller.set_pid(3.0, 0.2, 0.0)
    assert called == ["set_p", "set_i", "set_d"]
    assert controller.get_pid() == {"p": 3.0, "i": 0.2, "d": 0.0}


@pytest.mark.parametrize(
    "call, message",
    [
        (lambda c: c.set_p(-1.0), "p must not be negative"),
        (lambda c: c.set_i(-0.1), "i must not be negative"),
        (lambda c: c.set_d(-2.0), "d must not be negative"),
        (lambda c: c.set_output_limits(50.0, 10.0), "must not be above output_max"),
        (lambda c: c.set_period(0.0), "The period must be positive"),
        (lambda c: c.set_ramp_rate(-5.0), "The ramp rate must not be negative"),
    ],
)
def test_what_the_pid_can_t_take_is_refused(controller, call, message):
    with pytest.raises(ValueError, match=message):
        call(controller)


def test_set_pid_changes_none_if_one_is_refused(controller):
    with pytest.raises(ValueError, match="d must not be negative"):
        controller.set_pid(9.0, 9.0, -1.0)
    assert controller.get_pid() == {"p": 1.0, "i": 0.5, "d": 0.0}


def test_the_live_values_are_the_pid_s_and_work_as_measurements(pid, controller):
    asyncio.run(pid.start())
    assert controller.get_value() == 4.0  # its last reading
    assert controller.get_ramped_setpoint() == 5.0  # no ramp: the setpoint
    assert controller.get_error() == pytest.approx(1.0)
    assert controller.get_output() == pid.output
    assert Measurement("output", controller.get_output).run() == pid.output


def test_the_interface_can_call_its_queries_and_commands(tmp_path, pid):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    experiment.add_instrument(PIDController("pid", pid))
    experiment._rack._register_endpoints(experiment._api_server)
    client = TestClient(experiment._api_server.app)

    assert client.get("/pid/set_pid", params={"p": 2, "i": 0.4, "d": 0}).status_code == 200
    assert client.get("/pid/get_pid").json()["data"] == {"p": 2.0, "i": 0.4, "d": 0.0}
    assert client.get("/pid/set_setpoint", params={"setpoint": 6.5}).status_code == 200
    assert pid.setpoint == 6.5
    refused = client.get("/pid/set_p", params={"p": -1})
    assert refused.status_code == 500
    assert "p must not be negative" in refused.json()["detail"]
