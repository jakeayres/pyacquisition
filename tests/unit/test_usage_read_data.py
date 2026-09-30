"""Usage › Read your data (docs/usage/read_data.md): each version of analyse.py
runs on the data folder of a reader who did every step of Getting Started, made
here by running its examples in turn, and prints what the page shows."""

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
import requests

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "read_data"
GETTING_STARTED = ROOT / "examples" / "getting_started"
PAGE = ROOT / "docs" / "usage" / "read_data.md"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run(experiment, until) -> None:
    """Runs an experiment in a thread until `until(address)` is true, then stops it."""
    port = experiment._api_server.port
    thread = threading.Thread(target=lambda: asyncio.run(experiment._run()), daemon=True)
    thread.start()
    address = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            requests.get(f"{address}/ping", timeout=1)
            break
        except requests.RequestException:
            time.sleep(0.1)
    try:
        while not until(address) and time.monotonic() < deadline:
            time.sleep(0.1)
    finally:
        requests.get(f"{address}/experiment/shutdown", timeout=5)
        thread.join(timeout=15)


def lab_class(name: str):
    spec = importlib.util.spec_from_file_location(f"read_data_{name}", GETTING_STARTED / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Lab


def rows(folder: Path, name: str) -> int:
    path = folder / "data" / name
    return len(path.read_text(encoding="utf-8").splitlines()) - 1 if path.exists() else 0


@pytest.fixture(scope="module")
def my_lab(tmp_path_factory):
    """`my-lab` after Getting Started: the empty file's run, the rig's, lab.py's
    first and lab.py's last, with Record queued (for 2 s a file, not 10: enough for
    the five rows that step 2 prints, at 0.25 s a row)."""
    folder = tmp_path_factory.mktemp("my-lab")
    before = os.getcwd()
    os.chdir(folder)
    try:
        (folder / "rig.toml").write_text("", encoding="utf-8")
        from pyacquisition import Experiment

        def made(cls, name):
            return cls.from_config("rig.toml", root_path=str(folder), gui=False, api_server_port=free_port())

        run(made(Experiment, "empty"), lambda a: time.sleep(1.5) or True)
        shutil.copy(GETTING_STARTED / "rig.toml", folder / "rig.toml")
        run(made(Experiment, "rig"), lambda a: rows(folder, "01.00 start.data") >= 3)
        run(made(lab_class("lab_1"), "lab_1"), lambda a: rows(folder, "02.00 start.data") >= 3)
        queued = []

        def recorded(address):
            if not queued and rows(folder, "03.00 start.data") >= 2:
                queued.append(requests.get(f"{address}/tasks/record", params={"files": 3, "seconds": 2}, timeout=5))
            return rows(folder, "03.03 run 3.data") >= 3

        run(made(lab_class("lab_6"), "lab_6"), recorded)
    finally:
        os.chdir(before)
    return folder


def analyse(version: int, folder: Path) -> subprocess.CompletedProcess:
    shutil.copy(HERE / f"analyse_{version}.py", folder / "analyse.py")
    return subprocess.run(
        [sys.executable, "analyse.py"], cwd=folder, capture_output=True, text=True, timeout=120,
        env={**os.environ, "MPLBACKEND": "Agg"},  # no window: plt.show() does nothing
    )


def page_output(after: str) -> list[str]:
    """The lines of the page's first text block after `after`."""
    text = PAGE.read_text(encoding="utf-8")
    block = re.search(r"```text\n(.*?)```", text[text.index(after):], re.S)
    return block.group(1).splitlines()


def test_the_folder_is_named_as_the_page_says(my_lab):
    names = sorted(p.name for p in (my_lab / "data").glob("*.data"))
    assert names == page_output("## Find the data files")


def test_step_1_lists_the_files(my_lab):
    done = analyse(1, my_lab)
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == page_output("## Find the data files")


def test_step_2_prints_the_first_rows_of_run_1(my_lab):
    done = analyse(2, my_lab)
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    assert lines[0].split() == ["time", "wave", "power"] == page_output("## Read a file with pandas")[0].split()
    assert [line.split()[0] for line in lines[1:]] == ["0", "1", "2", "3", "4"]


def test_step_3_plots_wave_against_time(my_lab):
    done = analyse(3, my_lab)
    assert done.returncode == 0, done.stderr


def test_step_4_reads_every_file_of_the_run_and_saves_the_figure(my_lab):
    (my_lab / "wave.png").unlink(missing_ok=True)
    done = analyse(4, my_lab)
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    pattern = re.compile(r"^03\.0(\d) run (\d): \d+ rows, from \d+\.\d s$")
    assert [pattern.match(line).groups() for line in lines] == [("1", "1"), ("2", "2"), ("3", "3")]
    assert all(pattern.match(line) for line in page_output("## Read every file of a run"))
    assert (my_lab / "wave.png").stat().st_size > 10_000


def test_each_file_of_a_run_starts_where_the_last_ended(my_lab):
    starts = [pd.read_csv(p)["time"].min() for p in sorted((my_lab / "data").glob("03.* run *.data"))]
    assert starts == sorted(starts)


def test_the_empty_file_has_no_columns_and_the_early_files_no_power(my_lab):
    with pytest.raises(pd.errors.EmptyDataError, match="No columns to parse from file"):
        pd.read_csv(my_lab / "data" / "00.00 start.data")
    early = pd.read_csv(my_lab / "data" / "01.00 start.data")
    assert list(early.columns) == ["time", "wave"]
    with pytest.raises(KeyError, match="power"):
        early["power"]
