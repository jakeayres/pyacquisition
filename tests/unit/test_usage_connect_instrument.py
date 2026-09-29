"""Usage › Connect a real instrument (docs/usage/connect_instrument.md): each
version of rig.toml and lab.py makes its experiment, and does what the page says,
over `mock` since there is no instrument here. A wrong address is tried for real:
there is no GPIB instrument on a test machine, so pyvisa can't open one."""

import importlib.util
import tomllib
from pathlib import Path

import pytest

from pyacquisition import Experiment

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "connect_instrument"
GETTING_STARTED = ROOT / "examples" / "getting_started"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def on_mock(rig: str) -> str:
    """A version of rig.toml as a reader with no instrument follows it."""
    return rig.replace('adapter = "pyvisa"', 'adapter = "mock"')


def load_lab(name: str, source: str | None = None):
    """lab_N.py as a module of its own name (or `source` in its place)."""
    path = HERE / f"{name}.py"
    spec = importlib.util.spec_from_loader(f"connect_instrument_{name}", loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(compile(source or text(path), str(path), "exec"), module.__dict__)
    return module


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def experiment_from(folder: Path, rig: str, cls=Experiment):
    (folder / "rig.toml").write_text(rig, encoding="utf-8")
    return cls.from_config("rig.toml", root_path=str(folder), gui=False)


def test_it_starts_from_the_end_of_getting_started():
    assert text(HERE / "rig_1.toml") == text(GETTING_STARTED / "rig.toml")
    assert text(HERE / "lab_1.py") == text(GETTING_STARTED / "lab_6.py")


def test_the_lock_in_moves_from_mock_to_pyvisa_at_the_same_address():
    before = tomllib.loads(text(HERE / "rig_1.toml"))["instruments"]["lockin"]
    after = tomllib.loads(text(HERE / "rig_2.toml"))["instruments"]["lockin"]
    assert (before["adapter"], after["adapter"]) == ("mock", "pyvisa")
    assert before["resource"] == after["resource"] == "GPIB0::8::INSTR"


@pytest.mark.parametrize("version", [1, 2, 3])
def test_each_rig_runs_on_mock(folder, version):
    experiment = experiment_from(folder, on_mock(text(HERE / f"rig_{version}.toml")))
    assert experiment.instruments["lockin"].identify() == "MOCK,GPIB0::8::INSTR,0,0"


def test_the_lock_in_s_x_and_y_are_recorded_in_volts(folder):
    experiment = experiment_from(folder, on_mock(text(HERE / "rig_3.toml")))
    x, y = experiment.measurements["x"], experiment.measurements["y"]
    assert (x.unit, y.unit) == ("V", "V")
    assert (x.run(), y.run()) == (0.0, 0.0)  # mock answers 0 until something is set


def test_from_the_file_an_instrument_that_cant_be_opened_is_left_out(folder):
    experiment = experiment_from(folder, text(HERE / "rig_3.toml"))
    assert "lockin" not in experiment.instruments
    assert {"x", "y"}.isdisjoint(experiment.measurements)  # its measurements too
    assert {"clock", "signal"} <= set(experiment.instruments)  # the rest still starts


def test_then_getting_started_s_setup_stops_on_the_missing_lock_in(folder):
    lab = load_lab("lab_1").Lab
    experiment = experiment_from(folder, text(HERE / "rig_3.toml"), cls=lab)
    with pytest.raises(KeyError, match="lockin"):
        experiment.setup()


def test_the_multimeter_is_connected_in_python(folder):
    source = text(HERE / "lab_2.py").replace("timeout=10000)", 'timeout=10000, adapter="mock")')
    experiment = experiment_from(folder, on_mock(text(HERE / "rig_3.toml")), cls=load_lab("lab_2", source).Lab)
    experiment.setup()
    dmm = experiment.instruments["dmm"]
    assert dmm.name == "Keithley_2000"  # as the Instruments tab shows it
    assert dmm.identify() == "MOCK,GPIB0::16::INSTR,0,0"
    assert dmm._visa_resource.timeout == 10000
    assert experiment.measurements["v"].unit == "V"
    assert experiment.measurements["v"].run() == 0.0


def test_from_python_an_instrument_that_cant_be_opened_stops_the_experiment(folder):
    experiment = experiment_from(folder, on_mock(text(HERE / "rig_3.toml")), cls=load_lab("lab_2").Lab)
    with pytest.raises(ConnectionError, match=r"^Could not open 'GPIB0::16::INSTR' with the pyvisa adapter: "):
        experiment.setup()


def test_the_page_s_prologix_and_serial_tips_are_valid_config(folder):
    """The tips' lines, in a copy of the rig: they pass the config check (the
    connections themselves can't be opened here)."""
    from pyacquisition.core import config_check

    rig = text(HERE / "rig_2.toml")
    prologix = rig.replace('adapter = "pyvisa"\nresource = "GPIB0::8::INSTR"',
                           'adapter = "prologix"\nresource = "COM3::8"')
    serial = rig.replace('resource = "GPIB0::8::INSTR"',
                         'resource = "ASRL3::INSTR"\nargs = { baud_rate = 9600, read_termination = "\\r" }')
    for version in (prologix, serial):
        (folder / "rig.toml").write_text(version, encoding="utf-8")
        config_check.load(str(folder / "rig.toml"))
    assert tomllib.loads(serial)["instruments"]["lockin"]["args"]["read_termination"] == "\r"


def test_the_examples_match_the_getting_started_rig_where_they_should():
    """Only the lock-in's adapter, and two measurements, differ from Getting Started."""
    gs = text(GETTING_STARTED / "rig.toml").splitlines()
    final = text(HERE / "rig_3.toml").splitlines()
    added = [line for line in final if line not in gs]
    assert added == [
        'adapter = "pyvisa"',
        'x = { instrument = "lockin", method = "get_x", unit = "V" }',
        'y = { instrument = "lockin", method = "get_y", unit = "V" }',
    ]
