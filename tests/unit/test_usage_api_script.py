"""Usage › Drive an experiment from a script (docs/usage/api_script.md): lab.py
runs with no window, and each version of drive.py, run against it on a free port,
prints what the page says (with Record's files 1 s long, not 5, to be quick)."""

import asyncio
import importlib.util
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "api_script"
GETTING_STARTED = ROOT / "examples" / "getting_started"
PAGE = ROOT / "docs" / "usage" / "api_script.md"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_it_starts_from_the_end_of_getting_started():
    assert text(HERE / "lab_1.py") == text(GETTING_STARTED / "lab_6.py")


def lab_class():
    spec = importlib.util.spec_from_file_location("api_script_lab_2", HERE / "lab_2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Lab


def test_the_lab_runs_with_no_window():
    assert lab_class().gui is False


@pytest.fixture
def lab(tmp_path):
    """lab.py's second version, running in a thread on a free port."""
    shutil.copy(GETTING_STARTED / "rig.toml", tmp_path / "rig.toml")
    port = free_port()
    experiment = lab_class().from_config(str(tmp_path / "rig.toml"), root_path=str(tmp_path), api_server_port=port)
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
    yield address, tmp_path, thread
    try:
        requests.get(f"{address}/experiment/shutdown", timeout=5)
    except requests.RequestException:
        pass
    thread.join(timeout=20)


def drive(version: int, address: str, folder: Path, change=lambda s: s) -> subprocess.CompletedProcess:
    source = change(text(HERE / f"drive_{version}.py")).replace("http://localhost:8000", address)
    (folder / "drive.py").write_text(source.replace("seconds=5", "seconds=1"), encoding="utf-8")
    return subprocess.run([sys.executable, "drive.py"], cwd=folder, capture_output=True, text=True, timeout=120)


def page_says(heading: str) -> list[str]:
    page = text(PAGE)
    return re.search(r"```text\n(.*?)```", page[page.index(heading):], re.S).group(1).splitlines()


@pytest.mark.parametrize("version, heading", [
    (1, "## Read a value"), (2, "## Send a command"), (3, "## Queue a task"),
])
def test_each_version_prints_what_the_page_says(lab, version, heading):
    address, folder, _ = lab
    done = drive(version, address, folder)
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines()[-len(page_says(heading)):] == page_says(heading)


def test_the_last_version_records_two_files_waits_and_stops_the_experiment(lab):
    address, folder, thread = lab
    done = drive(5, address, folder)
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [
        "The lock-in is at 137.0 Hz", "Now it is at 211.0 Hz", "Record is queued",
        "The queue is empty", "The experiment is stopping",
    ]
    names = sorted(p.name for p in (folder / "data").glob("*.data"))
    assert names == ["00.00 start.data", "00.01 run 1.data", "00.02 run 2.data"]
    thread.join(timeout=20)
    assert not thread.is_alive()  # the experiment ended


def test_a_mistyped_address_and_a_wrong_argument_are_errors(lab):
    address, folder, _ = lab
    done = drive(1, address, folder, lambda s: s.replace("get_frequency", "get_frequncy"))
    assert "requests.exceptions.HTTPError: 404 Client Error: Not Found for url:" in done.stderr
    done = drive(2, address, folder, lambda s: s.replace("frequency=211.0", "freq=211.0"))
    assert "requests.exceptions.HTTPError: 422 Client Error" in done.stderr
