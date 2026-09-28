"""The example code that the documentation shows must keep working.

The tutorial and the front page include their code straight from `examples/`, so these
tests are what keep the documentation honest.
"""

import dataclasses
import importlib
import re
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pyacquisition import Experiment

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

SIMULATED_STEPS = [
    "step_1_first_experiment",
    "step_2_simulated_rig",
    "step_3_recording_data",
    "step_4_first_task",
    "step_5_composing_tasks",
]
HARDWARE_EXAMPLES = ["step_7_real_instruments", "front_page"]

# The types that the interface can draw an input box for.
FORM_TYPES = (int, float, str, bool)


@pytest.fixture
def examples(monkeypatch, tmp_path):
    """Make the examples importable, and keep their files out of the repository."""
    monkeypatch.syspath_prepend(str(EXAMPLES))
    monkeypatch.syspath_prepend(str(EXAMPLES / "tutorial"))
    monkeypatch.chdir(tmp_path)
    before = set(sys.modules)
    yield
    for name in set(sys.modules) - before:
        sys.modules.pop(name, None)


@pytest.fixture
def fake_visa(monkeypatch):
    """A stand-in for pyvisa that answers every query like an idle instrument."""
    resource = MagicMock()
    resource.query.side_effect = lambda text, *a, **k: "0" if "ESR" in text else "1.5"
    resource.resource_name = "fake"
    manager = MagicMock()
    manager.return_value.open_resource.return_value = resource
    monkeypatch.setattr("pyacquisition.core.adapters.pyvisa.ResourceManager", manager)


def build(name):
    experiment = importlib.import_module(name).MyExperiment()
    experiment.setup()
    return experiment


@pytest.mark.parametrize("name", SIMULATED_STEPS)
def test_each_simulated_step_sets_up(examples, name):
    experiment = build(name)
    assert "clock" in experiment.instruments


@pytest.mark.parametrize("name", HARDWARE_EXAMPLES)
def test_each_hardware_example_sets_up(examples, fake_visa, name):
    experiment = build(name)
    assert {"lockin", "lakeshore"} <= set(experiment.instruments)


@pytest.mark.parametrize("name", SIMULATED_STEPS[3:] + ["step_7_real_instruments"])
def test_task_inputs_can_be_shown_in_the_interface(examples, fake_visa, name):
    # A task input of any other type (a tuple, say) makes the interface raise
    # "Unsupported parameter type" when the task is opened from the Tasks menu.
    experiment = build(name)
    assert experiment._shared_tasks, "the example registers no tasks"
    for task, _ in experiment._shared_tasks:
        for field in dataclasses.fields(task):
            assert field.type in FORM_TYPES, f"{task.__name__}.{field.name}"


def test_the_simulated_lockin_signal_falls_away_as_the_sample_warms(examples):
    from simulated import SimulatedCryostat, SimulatedLockin

    cold = SimulatedLockin("lockin", SimulatedCryostat("cryostat", temperature=4.0))
    warm = SimulatedLockin("lockin", SimulatedCryostat("cryostat", temperature=20.0))
    assert cold.get_x() > 2.0e-3
    assert abs(warm.get_x()) < 1.0e-4


def test_the_simulated_lockin_signal_scales_with_the_excitation(examples):
    from simulated import SimulatedCryostat, SimulatedLockin

    lockin = SimulatedLockin("lockin", SimulatedCryostat("cryostat", temperature=4.0))
    full = lockin.get_x()
    lockin.set_reference_amplitude(0.5)
    assert lockin.get_reference_amplitude() == 0.5
    assert lockin.get_x() == pytest.approx(full / 2, rel=0.05)


def test_the_simulated_cryostat_ramps_and_then_settles(examples):
    from simulated import SimulatedCryostat

    from pyacquisition.instruments.lakeshore.lakeshore_350 import (
        InputChannel,
        OutputChannel,
        State,
    )

    cryostat = SimulatedCryostat("cryostat", temperature=20.0, lag=0.05)
    cryostat.set_ramp(OutputChannel.OUTPUT_1, State.ON, 600.0)  # 10 K a second
    cryostat.set_setpoint(OutputChannel.OUTPUT_1, 19.0)
    assert cryostat.get_setpoint(OutputChannel.OUTPUT_1) > 19.0  # still on its way
    import time

    time.sleep(0.5)
    assert cryostat.get_setpoint(OutputChannel.OUTPUT_1) == 19.0
    assert cryostat.get_temperature(InputChannel.INPUT_A) == pytest.approx(
        19.0, abs=0.05
    )


def stub_experiment(cryostat):
    """Just enough of an experiment for the tutorial tasks to run against."""
    return SimpleNamespace(instruments={"lakeshore": cryostat}, _scribe=MagicMock())


@pytest.mark.asyncio
async def test_set_temperature_arrives_and_leaves_the_cryostat_holding(examples):
    from simulated import SimulatedCryostat
    from step_4_first_task import SetTemperature

    from pyacquisition.instruments.lakeshore.lakeshore_350 import (
        InputChannel,
        OutputChannel,
    )

    cryostat = SimulatedCryostat("lakeshore", temperature=20.0, lag=0.05)
    experiment = stub_experiment(cryostat)

    await SetTemperature(kelvin=19.0, ramp_rate=120.0).start(experiment)

    assert cryostat.get_temperature(InputChannel.INPUT_A) == pytest.approx(
        19.0, abs=0.1
    )
    # teardown stopped the ramp where it was, so it holds
    assert cryostat.get_setpoint(OutputChannel.OUTPUT_1) == pytest.approx(19.0, abs=0.1)


@pytest.mark.asyncio
async def test_the_sweep_records_a_file_at_each_temperature(examples):
    from simulated import SimulatedCryostat
    from step_5_composing_tasks import TemperatureSweep

    cryostat = SimulatedCryostat("lakeshore", temperature=20.0, lag=0.05)
    experiment = stub_experiment(cryostat)

    await TemperatureSweep(low=19.0, high=20.0, step=0.5, dwell=0).start(experiment)

    titles = [
        call.kwargs["title"] for call in experiment._scribe.next_file.call_args_list
    ]
    assert titles == [
        "19K ramp",
        "19K hold",
        "19.5K ramp",
        "19.5K hold",
        "20K ramp",
        "20K hold",
    ]


def build_from_config():
    """The front-page example that describes the whole experiment in a config file."""
    shutil.copy(EXAMPLES / "front_page.toml", "rig.toml")  # what `--toml` is given
    return Experiment.from_config("rig.toml")


def test_the_config_file_example_sets_up(examples, fake_visa):
    experiment = build_from_config()
    assert {"lockin", "lakeshore"} <= set(experiment.instruments)
    assert set(experiment.measurements) == {"x", "y", "T"}


def test_the_calculations_config_example_sets_up(examples, fake_visa):
    shutil.copy(EXAMPLES / "calculations.toml", "rig.toml")
    experiment = Experiment.from_config("rig.toml")

    assert set(experiment.measurements) == {"v1", "v2"}
    assert experiment._calculations.known_columns == ["v_total", "v_smooth"]
    assert experiment._calculations.units == {"v_total": "V", "v_smooth": "V"}
    row = {"v1": 1.5, "v2": 1.5}
    assert experiment._calculations._apply(row)["v_total"] == 3.0


def test_the_config_file_example_is_equivalent_to_the_python_one(examples, fake_visa):
    python = build("front_page")
    config = build_from_config()

    assert set(config.instruments) == set(python.instruments)
    assert set(config.measurements) == set(python.measurements)
    assert config._data_path == python._data_path
    # Each measurement reads the same thing, including the one with an argument.
    for name in python.measurements:
        assert config.measurements[name].run() == python.measurements[name].run()


ROOT = EXAMPLES.parent
DOCS = ROOT / "docs"

# The notes beside a snippet are placed against its line numbers, so they must still point
# at the code they describe. A note takes about a title line and 0.8 of a line per line of
# text, and the text wraps at about this many characters (the front page is wider).
TITLE_LINES, TEXT_LINE_HEIGHT = 1.0, 0.81
CHARACTERS_PER_LINE = {"index.md": 62}
DEFAULT_CHARACTERS_PER_LINE = 44


def shown_lines(source):
    """The lines of `file` or `file:section`, as the documentation includes them."""
    path, _, section = source.partition(":")
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    if section:
        start = next(i for i, x in enumerate(lines) if f"[start:{section}]" in x)
        end = next(i for i, x in enumerate(lines) if f"[end:{section}]" in x)
        lines = lines[start + 1 : end]
    return [x for x in lines if "--8<--" not in x]


def annotated_snippets():
    """Every annotated snippet in the documentation, as (page, source, html)."""
    for page in sorted(DOCS.rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        opening = r'<div class="pa-annot(?: [^"]*)?" data-source='
        starts = [m.start() for m in re.finditer(opening, text)]
        for begin, end in zip(starts, starts[1:] + [len(text)]):
            html = text[begin:end]
            source = re.match(opening + '"([^"]+)"', html)
            assert source, f"{page.name}: an annotated snippet has no data-source"
            yield page, source.group(1), html


def test_there_are_annotated_snippets_to_check():
    assert len(list(annotated_snippets())) >= 5


@pytest.mark.parametrize(
    "page, source, html",
    [pytest.param(*x, id=f"{x[0].name}:{x[1]}") for x in annotated_snippets()],
)
def test_annotated_snippets_point_at_the_code_they_describe(page, source, html):
    code = shown_lines(source)

    included = re.search(r'--8<-- "([^"]+)"', html)
    assert included and included.group(1) == source, (
        f"the snippet includes {included and included.group(1)!r}, not {source!r}"
    )

    notes = re.findall(
        r'<div class="pa-note" style="--from: (\d+); --to: (\d+)" '
        r'data-contains="([^"]+)"><b>[^<]*</b><span>(.*?)</span></div>',
        html,
    )
    assert notes, "the snippet has no notes"

    annotated, previous = set(), None
    wrap = CHARACTERS_PER_LINE.get(page.name, DEFAULT_CHARACTERS_PER_LINE)
    for start, end, expected, text in notes:
        first, last = int(start), int(end)
        where = f"the note for lines {first}-{last}"
        assert 1 <= first <= last <= len(code), (
            f"{where}: the snippet has {len(code)} lines"
        )
        assert expected in "\n".join(code[first - 1 : last]), (
            f"{where} expects {expected!r}, but those lines are {code[first - 1 : last]}"
        )
        assert not (annotated & set(range(first, last + 1))), (
            f"{where} overlaps another"
        )
        annotated |= set(range(first, last + 1))

        # The note before this one must fit in the space above it.
        if previous:
            before_first, height = previous
            assert first - before_first >= height, (
                f"{where} starts {first - before_first} lines after the note above it, "
                f"which needs about {height:.1f}"
            )
        text_lines = -(-len(re.sub(r"<[^>]+>", "", text)) // wrap)
        previous = (first, TITLE_LINES + TEXT_LINE_HEIGHT * text_lines)

    highlighted = set()
    hl = re.search(r'hl_lines="([^"]+)"', html)
    assert hl, "the snippet highlights no lines"
    for part in hl.group(1).split():
        first, _, last = part.partition("-")
        highlighted |= set(range(int(first), int(last or first) + 1))
    assert highlighted == annotated, "hl_lines and the notes cover different lines"


# -------------------------------------------------------------------- traces
TRACE_EXAMPLES = ["traces_occasional", "traces_every_row"]


@pytest.mark.parametrize("name", TRACE_EXAMPLES)
def test_each_trace_example_sets_up_with_its_spectrum(examples, name):
    experiment = build(name)
    assert list(experiment.traces) == ["spectrum"]
    assert experiment.traces["spectrum"].trace.channels == ["intensity"]


def test_the_simulated_spectrum_moves_up_as_the_sample_warms(examples):
    import numpy as np
    from simulated import SimulatedCryostat, SimulatedSpectrometer

    def peak(kelvin):
        spectrometer = SimulatedSpectrometer(
            "s", SimulatedCryostat("c", temperature=kelvin), sweep_time=0
        )
        spectrometer.start_sweep()
        assert spectrometer.sweep_done()
        data = spectrometer.get_spectrum()
        return data.axis()[np.argmax(data.channels["intensity"])]

    assert peak(5.0) == pytest.approx(170.0, abs=2.0)
    assert peak(20.0) == pytest.approx(230.0, abs=2.0)


def test_the_traces_config_example_loads_with_no_problems(examples):
    import tomllib

    from pyacquisition.core.config_check import problems

    shutil.copy(EXAMPLES / "traces.toml", "rig.toml")
    experiment = Experiment.from_config("rig.toml", gui=False)

    assert list(experiment.traces) == ["spectrum"]
    assert experiment.traces["spectrum"].trace.every == 5
    assert problems(tomllib.loads((EXAMPLES / "traces.toml").read_text(encoding="utf-8"))) == []


def running(experiment, script):
    """Runs an experiment while `script(experiment)` does its part."""
    import asyncio

    async def drive():
        try:
            while not experiment._started:
                await asyncio.sleep(0.01)
            await asyncio.sleep(0.3)
            return await script(experiment)
        finally:
            experiment._shutdown_event.set()

    async def both():
        return (await asyncio.gather(experiment._run(), drive()))[1]

    return asyncio.run(asyncio.wait_for(both(), timeout=60))


def free_port():
    import socket

    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def test_the_spectrum_sweep_takes_a_spectrum_with_its_temperature(examples, tmp_path):
    from pyacquisition import read_traces

    module = importlib.import_module("traces_occasional")
    experiment = module.MyExperiment(gui=False, api_server_port=free_port())

    async def sweep(experiment):
        # One point, at the temperature the cryostat starts at: no waiting for it.
        await module.SpectrumSweep(low=20.0, high=20.0, step=1.0).start(experiment)

    running(experiment, sweep)
    traces = read_traces(Path("my_data") / "00.00 start.data")
    assert list(traces.index) == [0]
    assert traces.info["row.T"].iloc[0] == pytest.approx(20.0, abs=0.1)
    assert traces.x_unit == "GHz" and traces.channels["intensity"].shape == (1, 2048)


def test_the_every_row_example_has_a_peak_on_every_row(examples, tmp_path):
    import asyncio

    import pandas as pd

    module = importlib.import_module("traces_every_row")
    experiment = module.MyExperiment(
        gui=False, api_server_port=free_port(), measurement_period=0.1
    )

    async def wait(experiment):
        await asyncio.sleep(1.5)

    running(experiment, wait)
    rows = pd.read_csv(Path("my_data") / "00.00 start.data")
    assert len(rows) >= 3
    assert rows["spectrum_index"].tolist() == list(range(len(rows)))
    assert rows["spectrum_peak_x"].between(225, 235).all()  # 150 + 4 x 20 K
