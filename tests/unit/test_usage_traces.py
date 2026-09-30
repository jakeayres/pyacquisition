"""Usage › Record spectra and traces (docs/usage/traces.md): each version of
sample.py makes its experiment with the trace the page says, a short run writes a
spectrum with every row, and spectra.py reads them back."""

import asyncio
import importlib.util
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pandas as pd
import pytest
from fake_rig import REPLIES, open_fakes
import requests

from pyacquisition import Trace, read_traces

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "traces"
SIMULATED = ROOT / "examples" / "simulated_rig"
PAGE = ROOT / "docs" / "usage" / "traces.md"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def simulated(monkeypatch):
    open_fakes(monkeypatch, REPLIES)  # the lock-in and Lakeshore, for the first version
    monkeypatch.syspath_prepend(str(SIMULATED))
    sys.modules.pop("simulated", None)


def module(version: int):
    spec = importlib.util.spec_from_file_location(f"traces_sample_{version}", HERE / f"sample_{version}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def sample(version: int, folder: Path, **options):
    experiment = module(version).Sample(root_path=str(folder), gui=False, **options)
    experiment.setup()
    return experiment


def test_it_starts_from_tune_your_measurements_third_step():
    assert text(HERE / "sample_1.py") == text(ROOT / "examples" / "usage" / "measurements" / "sample_3.py")


def test_each_version_adds_the_trace_the_page_says(tmp_path, simulated):
    assert sample(1, tmp_path).traces == {}
    on_demand, reduced, every_row = (sample(v, tmp_path).traces["spectrum"].trace for v in (2, 3, 4))
    assert (on_demand.every, on_demand.every_rows, len(on_demand.reductions)) == (None, None, 0)
    assert len(reduced.reductions) == 1 and reduced.every_rows is None
    assert every_row.every_rows == 1 and every_row.every is None
    assert on_demand.instrument._uid == "spectrometer"


def test_a_spectrum_is_2048_points_from_100_to_300_ghz_about_230_at_20_k(tmp_path, simulated):
    spectrometer = sample(2, tmp_path).instruments["spectrometer"]
    spectrometer.start_sweep()
    data = spectrometer.get_spectrum()
    assert data.x == (100.0, 300.0) and data.x_unit == "GHz"
    assert len(data.channels["intensity"]) == 2048
    peak = 100 + 200 * data.channels["intensity"].argmax() / 2047
    assert peak == pytest.approx(230, abs=3)


def test_a_trace_is_given_the_method_not_a_spectrum(tmp_path, simulated):
    spectrometer = sample(2, tmp_path).instruments["spectrometer"]
    spectrometer.start_sweep()
    with pytest.raises(TypeError, match=r"^Trace 'spectrum' needs an instrument's trace method \(marked @mark_trace\), such as generator\.get_spectrum, not TraceData"):
        Trace("spectrum", spectrometer.get_spectrum())


@pytest.fixture(scope="module")
def a_run(tmp_path_factory):
    """sample.py's last version, run for a few rows, as `my-lab` would have it."""
    folder = tmp_path_factory.mktemp("my-lab")
    sys.path.insert(0, str(SIMULATED))
    sys.modules.pop("simulated", None)
    try:
        experiment = module(4).Sample(root_path=str(folder), gui=False, api_server_port=free_port())
        port = experiment._api_server.port
        thread = threading.Thread(target=lambda: asyncio.run(experiment._run()), daemon=True)
        thread.start()
        data = folder / "data" / "00.00 start.data"
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            if data.exists() and len(data.read_text(encoding="utf-8").splitlines()) >= 5:
                break
            time.sleep(0.2)
        requests.get(f"http://127.0.0.1:{port}/experiment/shutdown", timeout=5)
        thread.join(timeout=20)
    finally:
        sys.path.remove(str(SIMULATED))
    return folder


def test_every_row_has_its_spectrum_s_number_and_peak(a_run):
    rows = pd.read_csv(a_run / "data" / "00.00 start.data")
    assert list(rows.columns) == ["time", "x", "y", "T", "spectrum_index", "spectrum_peak_x"]
    assert rows["spectrum_index"].tolist() == list(range(len(rows)))
    assert rows["spectrum_peak_x"].between(225, 235).all()  # 20 K: about 230 GHz
    assert rows["time"].diff().dropna().min() > 0.9  # each row waits for its spectrum, about 1 s
    assert (a_run / "data" / "00.00 start.h5").exists()


def test_read_traces_links_each_spectrum_to_its_row(a_run):
    traces = read_traces(a_run / "data" / "00.00 start.data", "spectrum")
    assert traces.x.shape == (2048,) and traces.channels["intensity"].shape[1] == 2048
    assert traces.info["row.T"].to_numpy() == pytest.approx(20.0, abs=0.1)
    with pytest.raises(KeyError, match="There is no trace called 'spectra'"):
        read_traces(a_run / "data" / "00.00 start.data", "spectra")
    with pytest.raises(FileNotFoundError, match="has no trace file beside it"):
        read_traces(a_run / "data" / "missing.data", "spectrum")


def test_spectra_py_says_what_it_read_and_draws_them(a_run):
    shutil.copy(HERE / "spectra_1.py", a_run / "spectra.py")
    (a_run / "spectra.png").unlink(missing_ok=True)
    done = subprocess.run([sys.executable, "spectra.py"], cwd=a_run, capture_output=True, text=True, timeout=120,
                          env={**os.environ, "MPLBACKEND": "Agg"})
    assert done.returncode == 0, done.stderr
    first, second = done.stdout.splitlines()
    assert re.fullmatch(r"00\.00 start\.data: \d+ spectra of 2048 points", first)
    assert re.fullmatch(r"from \d+\.\d K to \d+\.\d K", second)
    page = re.search(r"```text\n(.*?)```", text(PAGE), re.S).group(1).splitlines()
    assert re.fullmatch(r"00\.00 start\.data: \d+ spectra of 2048 points", page[0])
    assert (a_run / "spectra.png").stat().st_size > 10_000


def test_the_page_shows_the_spectrometer_s_class_from_simulated_py():
    source = text(SIMULATED / "simulated.py")
    section = source.split("# --8<-- [start:spectrometer]\n")[1].split("# --8<-- [end:spectrometer]")[0]
    assert "@mark_trace(" in section and section.startswith("class SimulatedSpectrometer")
    assert '"examples/simulated_rig/simulated.py:spectrometer"' in text(PAGE)
