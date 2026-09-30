"""Usage › Hold a temperature with PID (docs/usage/pid.md): each version of hold.py
makes its experiment with the real SR_830 and Lakeshore_350 drivers, at their
addresses, over a fake connection that records what is sent and answers from a
table. The resistance is X over the excitation, the heater is handed to the
computer and turned off at the end, the PID reads and writes what the page says,
and the Controls instrument changes it."""

import asyncio
import importlib.util
from pathlib import Path

import pytest

from pyacquisition.core import instrument as instrument_module
from pyacquisition.tasks import PID
from pyacquisition.tasks.pid import PIDController

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "pid"


class FakeConnection:
    """Stands in for an instrument at an address: it records what is written, keeps
    it for the queries that read it back, and answers the rest from `replies`."""

    def __init__(self, address, replies):
        self.resource_name = address
        self.written = []
        self.replies = dict(replies)

    def write(self, message):
        self.written.append(message)
        header, _, arguments = message.partition(" ")
        first, _, rest = arguments.partition(",")
        self.replies[f"{header}? {first}" if rest else f"{header}?"] = rest or first
        return len(message)

    def query(self, message):
        return self.replies.get(message, "0")

    def close(self):
        pass


@pytest.fixture
def connections(monkeypatch):
    """The fake connection opened for each address."""
    opened = {}
    replies = {
        "GPIB0::8::INSTR": {"OUTP? 1": "1.65e-04"},  # 165 uV over 100 nA: 1650 ohms
        "GPIB0::12::INSTR": {"KRDG? A": "8.0", "OUTMODE? 1": "1,1,0", "HTR? 1": "32.0"},
    }

    def open_resource(address, adapter="pyvisa", **options):
        opened[address] = FakeConnection(address, replies.get(address, {}))
        return opened[address]

    monkeypatch.setattr(instrument_module, "open_resource", open_resource)
    return opened


def hold(version: int, tmp_path):
    spec = importlib.util.spec_from_file_location(f"pid_hold_{version}", HERE / f"hold_{version}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    experiment = module.Hold(root_path=str(tmp_path), gui=False)
    experiment.setup()
    return module, experiment


def the_pid(experiment) -> PID:
    (task,) = experiment.task_managers["control"]._task_queue._queue
    return task


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_each_version_opens_the_two_instruments_at_their_addresses(version, tmp_path, connections):
    from pyacquisition.instruments import SR_830, Lakeshore_350

    _, experiment = hold(version, tmp_path)
    assert set(connections) == {"GPIB0::8::INSTR", "GPIB0::12::INSTR"}
    assert isinstance(experiment.instruments["lockin"], SR_830)
    assert isinstance(experiment.instruments["lakeshore"], Lakeshore_350)


@pytest.mark.parametrize("version", [2, 3, 4, 5])
def test_the_resistance_is_x_over_the_excitation(version, tmp_path, connections):
    module, experiment = hold(version, tmp_path)
    assert module.EXCITATION == 100e-9
    assert experiment.measurements["R"].unit == "Ω"
    assert experiment.measurements["R"].run() == pytest.approx(1650.0)
    assert experiment.measurements["T"].run() == 8.0
    sent = connections["GPIB0::8::INSTR"].written
    assert any(m.startswith("SLVL 1") for m in sent)  # the 1 V that drives the 100 nA


@pytest.mark.parametrize("version", [3, 4, 5])
def test_the_heater_is_handed_to_the_computer_and_off_at_the_end(version, tmp_path, connections, capsys):
    _, experiment = hold(version, tmp_path)
    sent = connections["GPIB0::12::INSTR"].written
    assert "OUTMODE 1,3,1,0" in sent  # open loop, keeping its input
    assert "MOUT 1,0.00" in sent
    assert "RANGE 1,3" in sent
    assert experiment.measurements["heater"].run() == 32.0

    experiment.teardown()
    assert sent[-1] == "RANGE 1,0"
    assert capsys.readouterr().out.strip().endswith("The heater is off.")


def test_the_pid_reads_the_resistance_and_writes_the_heater(tmp_path, connections):
    _, experiment = hold(4, tmp_path)
    assert set(experiment.task_managers) == {"main", "control"}
    assert list(experiment.task_managers["main"]._task_queue._queue) == []
    pid = the_pid(experiment)
    assert (pid.setpoint, pid.kp, pid.ki, pid.output_min, pid.output_max) == (1650.0, 1.0, 0.2, 0.0, 100.0)
    assert pid.inverted is True
    assert pid.final_output == 0.0  # the heater at 0 when it ends
    assert pid.label == "sample"

    assert pid.read() == pytest.approx(1650.0)
    pid.write(40.0)
    assert connections["GPIB0::12::INSTR"].written[-1] == "MOUT 1,40.00"
    assert experiment.measurements["setpoint"].run() == 1650.0


def test_the_controls_change_the_pid(tmp_path, connections):
    _, experiment = hold(5, tmp_path)
    pid = the_pid(experiment)
    controls = experiment.instruments["pid"]
    controls.set_setpoint(1560.0)
    controls.set_gains(0.5, 0.1)
    assert (pid.setpoint, pid.kp, pid.ki) == (1560.0, 0.5, 0.1)
    assert controls.get_setpoint() == 1560.0


@pytest.mark.parametrize("inverted, heats", [(True, True), (False, False)])
def test_a_resistance_above_the_setpoint_heats_only_when_inverted(inverted, heats):
    """Cold, a RuOx reads above the setpoint: only an inverted PID heats."""
    controller = PIDController(kp=1.0, ki=0.2, output_min=0.0, output_max=100.0, inverted=inverted)
    output = controller.update(setpoint=1650.0, process_value=1995.0, dt=1.0)
    assert (output > 0) is heats


@pytest.mark.asyncio
async def test_a_pid_whose_write_keeps_failing_stops_after_five_cycles(tmp_path, connections):
    _, experiment = hold(4, tmp_path)
    pid = the_pid(experiment)
    pid.period = 0.01

    def broken(percent):
        raise TimeoutError("the Lakeshore didn't answer")

    pid.write = broken
    await asyncio.wait_for(pid.start(experiment), 10)
    assert pid.outcome == "failed"


def test_a_value_instead_of_the_function_is_refused():
    with pytest.raises(Exception, match="read and write must be functions"):
        PID(read=1650.0, write=print, setpoint=1650.0)
