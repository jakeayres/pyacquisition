"""The install check's setup (see test_install_wheels.py).

Everything the check downloads lives in a folder of its own, `CHECK_HOME`: the
newest standalone uv, uv's Pythons and cache, and wheels built for the packages
that ship only as source. The maintainer's own uv, Pythons and cache are left
alone. A managed Python in uv's usual folder would become the default for their
new projects, and wheels once built from source in a shared cache would let
`--no-build` pass where a lab PC fails. Deleting the folder is safe: the next
run downloads again.

On GitHub Actions (`GITHUB_ACTIONS` set), the uv is the one setup-uv installed,
no internet is a failure rather than a skip, and each test adds a row to the
run's summary (`GITHUB_STEP_SUMMARY`).
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from pythons import ROOT

CHECK_HOME = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "pyacquisition-install-check"
ON_GITHUB = bool(os.environ.get("GITHUB_ACTIONS"))

# Packages that ship only as source and are pure Python, so any machine can build
# them. Each is built once into CHECK_HOME/wheels, which every install is given
# with --find-links. Everything else must come as a wheel (--no-build). Without a
# wheel for proxy-tools, which pywebview needs, `uv add --no-build` quietly
# installs an old release of pyacquisition whose dependencies all have wheels.
ALLOWED_SOURCE_BUILDS = {"proxy-tools"}

UV_LATEST = "https://github.com/astral-sh/uv/releases/latest"
UV_ASSET = "uv-x86_64-pc-windows-msvc.zip"


def fetch(url: str, timeout: float = 60) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


@dataclass(frozen=True)
class Ran:
    """What a command printed, and how it ended."""

    code: int
    out: str
    err: str

    @property
    def ok(self) -> bool:
        return self.code == 0

    def tail(self, lines: int = 8) -> str:
        printed = [line for line in (self.out + "\n" + self.err).splitlines() if line.strip()]
        return "\n".join(printed[-lines:])

    def reason(self) -> str:
        """The line that names the package without a wheel, or the last line."""
        printed = [line.strip() for line in self.err.splitlines() if line.strip()]
        named = [line for line in printed if line.startswith("hint: Wheels are required")]
        return (named or printed or ["(uv printed nothing)"])[-1]


@dataclass(frozen=True)
class Uv:
    """The uv the check runs, called with the check's environment."""

    path: Path
    version: str
    env: dict = field(repr=False)  # kept out of tracebacks: it is the whole environment

    def __call__(self, *args, cwd=None, timeout: float = 900) -> Ran:
        done = subprocess.run(
            [str(self.path), *map(str, args)], cwd=cwd, env=self.env, timeout=timeout,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        return Ran(done.returncode, done.stdout, done.stderr)


@dataclass(frozen=True)
class Target:
    """What to install: `pip` for `uv pip install`, `add` for `uv add` (as the
    installation page types it), and the version that must end up installed."""

    pip: str
    add: str
    version: str


def version_of(uv: Path) -> str:
    """`uv 0.13.6 (329bf9448 2026-10-26 x86_64-pc-windows-msvc)` gives `0.13.6`."""
    done = subprocess.run([str(uv), "--version"], capture_output=True, text=True, check=True)
    return done.stdout.split()[1]


def newest_uv() -> str:
    """The newest uv's version: the tag GitHub's latest release redirects to."""
    with urllib.request.urlopen(urllib.request.Request(UV_LATEST, method="HEAD"), timeout=30) as response:
        return response.url.rstrip("/").rsplit("/", 1)[-1]


def install_uv(version: str, folder: Path):
    """Unpacks the standalone uv `version` into `folder`, once its hash is checked."""
    url = f"https://github.com/astral-sh/uv/releases/download/{version}/{UV_ASSET}"
    archive = fetch(url, timeout=300)
    expected = fetch(url + ".sha256").decode().split()[0]
    if hashlib.sha256(archive).hexdigest() != expected:
        pytest.fail(f"{UV_ASSET} {version} doesn't match its published SHA-256")
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        zipped.extractall(folder)


def in_a_venv(entry: str) -> bool:
    """Whether a PATH entry is a virtual environment's own (its folder's parent
    holds a pyvenv.cfg), such as this checkout's `.venv\\Scripts`."""
    return (Path(entry).parent / "pyvenv.cfg").exists()


@pytest.fixture(scope="session")
def internet():
    try:
        fetch("https://pypi.org/simple/pyacquisition/", timeout=10)
    except OSError as error:
        message = f"the install check needs the internet ({error})"
        if ON_GITHUB:
            pytest.fail(message)
        pytest.skip(message)


@pytest.fixture(scope="session")
def check_env() -> dict:
    """The environment for everything the check runs. None of this checkout's
    environment shows through (`VIRTUAL_ENV`, a virtual environment on PATH),
    and uv uses only its own Pythons, from the check's folder, as on a machine
    with no Python of its own."""
    path = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry and not in_a_venv(entry)]
    env = {
        key: value for key, value in os.environ.items()
        if key not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH")
    }
    env.update(
        PATH=os.pathsep.join(path),
        UV_PYTHON_PREFERENCE="only-managed",
        UV_PYTHON_INSTALL_DIR=str(CHECK_HOME / "python"),
        UV_CACHE_DIR=str(CHECK_HOME / "cache"),
        PYACQUISITION_NEWS="off",
    )
    return env


@pytest.fixture(scope="session")
def uv(internet, check_env) -> Uv:
    """On GitHub, the uv setup-uv put on PATH. Here, the newest standalone uv, kept
    in the check's folder and replaced when a newer one is released."""
    if ON_GITHUB:
        found = shutil.which("uv")
        if not found:
            pytest.fail("the install check needs uv on PATH")
        path = Path(found)
    else:
        path = CHECK_HOME / "uv" / "uv.exe"
        newest = newest_uv()
        if not path.exists() or version_of(path) != newest:
            install_uv(newest, path.parent)
    return Uv(path, version_of(path), check_env)


@pytest.fixture(scope="session")
def wheels(uv) -> Path:
    """CHECK_HOME/wheels: a wheel for each of ALLOWED_SOURCE_BUILDS, built from its
    newest release's source on PyPI, and nothing else."""
    folder = CHECK_HOME / "wheels"
    folder.mkdir(parents=True, exist_ok=True)
    wanted = {name.replace("-", "_") for name in ALLOWED_SOURCE_BUILDS}
    for wheel in folder.glob("*.whl"):
        if wheel.name.split("-")[0].lower() not in wanted:
            wheel.unlink()
    for name in sorted(ALLOWED_SOURCE_BUILDS):
        info = json.loads(fetch(f"https://pypi.org/pypi/{name}/json"))
        version = info["info"]["version"]
        if any(folder.glob(f"{name.replace('-', '_')}-{version}-*.whl")):
            continue
        sdist = next(file for file in info["urls"] if file["packagetype"] == "sdist")
        source = fetch(sdist["url"], timeout=300)
        if hashlib.sha256(source).hexdigest() != sdist["digests"]["sha256"]:
            pytest.fail(f"{sdist['filename']} doesn't match PyPI's SHA-256")
        path = CHECK_HOME / "sdists" / sdist["filename"]
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(source)
        built = uv("build", "--wheel", path, "--out-dir", folder, cwd=CHECK_HOME)
        if not built.ok:
            pytest.fail(f"couldn't build {name} {version}:\n{built.tail()}")
    return folder


@pytest.fixture(scope="session")
def target(request, uv, tmp_path_factory) -> Target:
    """With --install, the checkout's own wheel. With --install-release, the
    newest release on PyPI."""
    if request.config.getoption("--install"):
        out = tmp_path_factory.mktemp("dist")
        built = uv("build", "--wheel", "--out-dir", out, cwd=ROOT)
        if not built.ok:
            pytest.fail(f"couldn't build the checkout's wheel:\n{built.tail()}")
        wheel = next(out.glob("pyacquisition-*.whl"))
        return Target(pip=str(wheel), add=str(wheel), version=wheel.name.split("-")[1])
    version = json.loads(fetch("https://pypi.org/pypi/pyacquisition/json"))["info"]["version"]
    return Target(pip=f"pyacquisition=={version}", add="pyacquisition", version=version)


# ------------------------------------------------------- the run's summary
_summary_started = False


def _outcome(report) -> tuple[str, str]:
    if hasattr(report, "wasxfail"):
        if report.passed:
            return "passed unexpectedly", ""
        return "expected failure", report.wasxfail
    if report.skipped:
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else str(report.longrepr)
        return "skipped", reason.removeprefix("Skipped: ")
    if report.failed:
        crash = getattr(report.longrepr, "reprcrash", None)
        message = crash.message if crash else str(report.longrepr)
        if "XPASS(strict)" in message:
            return "passed unexpectedly", message
        return "failed", message
    return "passed", ""


def pytest_runtest_logreport(report):
    """On GitHub, one row of the run's summary for each install test: from its
    call, or from its setup when it never got that far."""
    global _summary_started
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary or "install" not in report.keywords:
        return
    if report.when != "call" and not (report.when == "setup" and not report.passed):
        return
    outcome, reason = _outcome(report)
    reason = " ".join(reason.split()).replace("|", "\\|")[:400]
    found = dict(report.user_properties)
    test = report.nodeid.split("::")[-1]
    with open(summary, "a", encoding="utf-8") as file:
        if not _summary_started:
            file.write("| Test | Python | uv | Outcome | Reason |\n|---|---|---|---|---|\n")
            _summary_started = True
        file.write(f"| {test} | {found.get('python', '-')} | {found.get('uv', '-')} | {outcome} | {reason} |\n")
