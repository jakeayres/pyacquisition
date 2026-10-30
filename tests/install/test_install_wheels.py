"""The install check. Each listed Python installs PyAcquisition from wheels
alone, as a lab PC with no compiler must, and runs a rig with no window. The
newest also runs the installation page's own commands. The next Python is tried
too, and expected to fail until its dependencies have wheels for it.

Skipped unless asked for, since it needs the internet and takes minutes:

    uv run --no-sync pytest tests/install --install -rA           the checkout
    uv run --no-sync pytest tests/install --install-release -rA   the newest release

Its setup, and why it keeps a uv and a folder of its own, is in conftest.py.
"""

import json
import os
import socket
import subprocess
import time
import tomllib
import urllib.request
from pathlib import Path

import pytest

from pythons import listed, next_after

pytestmark = pytest.mark.install

LISTED = listed()
NEWEST = LISTED[-1]
NEXT = next_after(LISTED)
PYTHONS = [
    *LISTED,
    pytest.param(NEXT, marks=pytest.mark.xfail(
        # On GitHub its first pass fails the run, which is the notice to list it.
        strict=bool(os.environ.get("GITHUB_ACTIONS")),
        # Only the test's own pytest.xfail(), when the install fails, is expected.
        # Anything after it, such as the rig, fails with its own reason.
        raises=pytest.xfail.Exception,
        reason="the next Python: it passes once every dependency has a wheel for it",
    )),
]

VERSION = "import importlib.metadata as m; print(m.version('pyacquisition'))"

RIG = """\
[experiment]
root_path = "."

[gui]
run = false

[api_server]
port = {port}

[instruments]
clock = {{instrument = "Clock"}}
generator = {{instrument = "TraceGenerator"}}

[measurements]
time = {{instrument = "clock", method = "time"}}

[traces.spectrum]
instrument = "generator"
method = "get_spectrum"
every_rows = 1
reduce = ["peak_x"]
"""


def in_python(python: Path, code: str, env: dict) -> str:
    done = subprocess.run([str(python), "-c", code], env=env, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def describe(uv, python: Path, record_property) -> str:
    """`uv 0.13.6, Python 3.14.10`, printed, and kept for the run's summary."""
    full = in_python(python, "import sys; print(sys.version.split()[0])", uv.env)
    record_property("python", full)
    record_property("uv", uv.version)
    versions = f"uv {uv.version}, Python {full}"
    print(versions)
    return versions


def get(url: str):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read())


def traces_beside_data(data: Path) -> bool:
    """Whether a data file in `data` has its trace file, `<stem>.h5`, beside it."""
    return data.is_dir() and any(
        file.with_suffix(".h5").exists() for file in data.iterdir() if file.suffix != ".h5"
    )


def check_rig(base: str, folder: Path, proc: subprocess.Popen):
    deadline = time.monotonic() + 50
    while True:
        try:
            if get(f"{base}/ping") == "pong":
                break
        except OSError:
            pass
        if proc.poll() is not None:
            raise RuntimeError(f"stopped with code {proc.returncode} before answering /ping")
        if time.monotonic() > deadline:
            raise RuntimeError("never answered /ping")
        time.sleep(0.25)

    names = {column["name"] for column in get(f"{base}/experiment/columns")["data"]}
    if not {"time", "spectrum_index", "spectrum_peak_x"} <= names:
        raise RuntimeError(f"has the columns {sorted(names)}")

    data = folder / "data"
    deadline = time.monotonic() + 20
    while not traces_beside_data(data):
        if time.monotonic() > deadline:
            found = sorted(path.name for path in data.iterdir()) if data.is_dir() else "no data folder"
            raise RuntimeError(f"wrote no trace file beside its data file: {found}")
        time.sleep(0.25)

    try:
        get(f"{base}/experiment/shutdown")
    except OSError:
        pass  # the process may close the connection before the reply is read
    if proc.wait(timeout=20) != 0:
        raise RuntimeError(f"stopped with code {proc.returncode}")


def run_rig(folder: Path, pyacquisition: Path, env: dict, versions: str):
    """Runs a rig with no window, a clock and a trace on every row, from the
    environment's own `pyacquisition` command, as test_a_real_toml_build does."""
    folder.mkdir()
    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
    (folder / "rig.toml").write_text(RIG.format(port=port), encoding="utf-8")
    log_path = folder / "console.log"
    # Output goes to a file: unread output piped to the parent can block the child.
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [str(pyacquisition), "run", "--toml", "rig.toml"],
            stdout=log, stderr=subprocess.STDOUT, cwd=folder, env=env,
        )
        try:
            check_rig(f"http://localhost:{port}", folder, proc)
        except Exception as error:
            output = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
            pytest.fail(f"{versions}: the rig {error}\n--- its output, last lines ---\n" + "\n".join(output))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)


@pytest.mark.parametrize("python", PYTHONS)
def test_installs_and_runs(python, uv, wheels, target, tmp_path, record_property):
    made = uv("venv", "--python", python, tmp_path / "env")
    if not made.ok:
        message = f"uv {uv.version} can't provide Python {python}: {made.reason()}"
        if python == NEXT:
            pytest.skip(message)
        pytest.fail(message)
    exe = tmp_path / "env" / "Scripts" / "python.exe"
    versions = describe(uv, exe, record_property)

    installed = uv("pip", "install", "--python", exe, "--no-build", "--find-links", wheels, target.pip)
    if not installed.ok:
        if python == NEXT:
            pytest.xfail(f"{versions}: {installed.reason()}")
        pytest.fail(f"{versions}: {target.pip} doesn't install from wheels alone:\n{installed.tail()}")
    found = in_python(exe, VERSION, uv.env)
    assert found == target.version, f"{versions}: installed pyacquisition {found}, not {target.version}"

    run_rig(tmp_path / "rig", exe.parent / "pyacquisition.exe", uv.env, versions)


def test_the_install_page_commands(uv, wheels, target, tmp_path, record_property):
    """The installation page's commands, on the newest listed Python:
    `uv init my-lab --python <newest> --no-package`, `uv add pyacquisition` and
    its check."""
    made = uv("init", "my-lab", "--python", NEWEST, "--no-package", cwd=tmp_path)
    assert made.ok, made.tail()
    lab = tmp_path / "my-lab"
    project = tomllib.loads((lab / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["requires-python"] == f">={NEWEST}"

    added = uv("add", target.add, "--no-build", "--find-links", wheels, cwd=lab)
    assert added.ok, f"uv {uv.version}: `uv add` on Python {NEWEST} doesn't install from wheels alone:\n{added.tail()}"
    exe = lab / ".venv" / "Scripts" / "python.exe"
    versions = describe(uv, exe, record_property)

    checked = uv("run", "python", "-c", "import pyacquisition; print('pyacquisition is installed')", cwd=lab)
    assert checked.out.strip() == "pyacquisition is installed", f"{versions}:\n{checked.tail()}"
    # With --no-build, uv quietly falls back to an older release whose dependencies
    # all have wheels, so the version is what shows that it didn't.
    found = in_python(exe, VERSION, uv.env)
    assert found == target.version, f"{versions}: `uv add` installed pyacquisition {found}, not {target.version}"
