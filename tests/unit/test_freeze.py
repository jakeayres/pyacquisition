"""`build_app` shells out to PyInstaller. These tests fake the subprocess, so they
run without PyInstaller installed. `test_a_real_toml_build` (skipped unless it is)
runs a real build, end to end."""

import pathlib
import shutil
import socket
import subprocess

import pytest

from pyacquisition import freeze
from pyacquisition.core.config_parser import InvalidInstrumentError


@pytest.fixture
def fake_pyinstaller(monkeypatch):
    """Stands in for the `pyinstaller` command: records how it was called, and
    creates the dist folder a real run would, so the file it is asked to freeze
    is never actually run."""
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        name = command[command.index("--name") + 1]
        dist = command[command.index("--distpath") + 1]
        onefile = "--onefile" in command
        target = f"{dist}/{name}.exe" if onefile else f"{dist}/{name}/{name}.exe"
        pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(target).write_text("fake exe")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(freeze.subprocess, "run", run)
    monkeypatch.setattr(freeze, "pyinstaller_available", lambda: True)
    return calls


@pytest.fixture
def config(tmp_path):
    path = tmp_path / "rig.toml"
    path.write_text('[experiment]\nroot_path = "."\n')
    return path


# ----------------------------------------------------------------- arguments
def test_exactly_one_of_toml_or_py_is_required(fake_pyinstaller, config, tmp_path):
    with pytest.raises(ValueError, match="exactly one"):
        freeze.build_app()
    with pytest.raises(ValueError, match="exactly one"):
        freeze.build_app(toml_file=str(config), py_file=str(tmp_path / "x.py"))


def test_pyinstaller_missing_is_reported_before_anything_else(monkeypatch, config):
    monkeypatch.setattr(freeze, "pyinstaller_available", lambda: False)
    called = []
    monkeypatch.setattr(freeze.subprocess, "run", lambda *a, **k: called.append(1))

    with pytest.raises(FileNotFoundError, match="pyacquisition\\[build\\]"):
        freeze.build_app(toml_file=str(config))

    assert called == [], "pyinstaller must not be invoked when it is not there"


def test_a_bad_toml_is_refused_before_pyinstaller_runs(fake_pyinstaller, tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("[instruments]\nx = 1\n")  # not a dict

    with pytest.raises(InvalidInstrumentError):
        freeze.build_app(toml_file=str(bad), out_dir=tmp_path)

    assert fake_pyinstaller == []


def test_a_missing_py_file_is_refused_before_pyinstaller_runs(
    fake_pyinstaller, tmp_path
):
    with pytest.raises(FileNotFoundError, match="no_such_file"):
        freeze.build_app(py_file=str(tmp_path / "no_such_file.py"), out_dir=tmp_path)

    assert fake_pyinstaller == []


def test_a_pyinstaller_failure_is_reported(monkeypatch, config, tmp_path):
    monkeypatch.setattr(freeze, "pyinstaller_available", lambda: True)
    monkeypatch.setattr(
        freeze.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 1),
    )

    with pytest.raises(RuntimeError, match="exit code 1"):
        freeze.build_app(toml_file=str(config), out_dir=tmp_path)


# --------------------------------------------------------------- a toml build
def test_a_toml_build_generates_and_freezes_the_entry_script(
    fake_pyinstaller, config, tmp_path
):
    freeze.build_app(toml_file=str(config), out_dir=tmp_path)

    (command,) = fake_pyinstaller
    script = command[1]
    assert script.endswith("_entry.py")
    text = pathlib.Path(script).read_text(encoding="utf-8")
    assert 'Experiment.from_config(str(_app_dir() / "config.toml"))' in text
    assert "from pyacquisition import Experiment" in text


def test_a_toml_build_names_itself_after_the_file(fake_pyinstaller, config, tmp_path):
    freeze.build_app(toml_file=str(config), out_dir=tmp_path)

    (command,) = fake_pyinstaller
    assert command[command.index("--name") + 1] == "rig"


def test_a_toml_build_can_be_named_explicitly(fake_pyinstaller, config, tmp_path):
    freeze.build_app(toml_file=str(config), name="MyRig", out_dir=tmp_path)

    (command,) = fake_pyinstaller
    assert command[command.index("--name") + 1] == "MyRig"


def test_the_config_is_copied_into_the_built_folder(fake_pyinstaller, config, tmp_path):
    app_dir = freeze.build_app(toml_file=str(config), out_dir=tmp_path)

    copy = app_dir / "config.toml"
    assert copy.read_text() == config.read_text()
    assert copy != config


def test_a_toml_build_puts_the_config_beside_the_single_exe_by_default(
    fake_pyinstaller, config, tmp_path
):
    app_dir = freeze.build_app(toml_file=str(config), out_dir=tmp_path)

    assert app_dir == tmp_path / "dist"
    assert (app_dir / "config.toml").exists()
    assert (app_dir / "rig.exe").exists()


def test_onedir_puts_the_config_in_the_named_folder(fake_pyinstaller, config, tmp_path):
    app_dir = freeze.build_app(toml_file=str(config), onefile=False, out_dir=tmp_path)

    assert app_dir == tmp_path / "dist" / "rig"
    assert (app_dir / "config.toml").exists()
    assert (app_dir / "rig.exe").exists()


def test_windowed_by_default_and_console_when_asked(fake_pyinstaller, config, tmp_path):
    freeze.build_app(toml_file=str(config), out_dir=tmp_path)
    assert "--windowed" in fake_pyinstaller[0]

    freeze.build_app(toml_file=str(config), windowed=False, out_dir=tmp_path)
    assert "--windowed" not in fake_pyinstaller[1]


def test_an_icon_is_passed_through(fake_pyinstaller, config, tmp_path):
    freeze.build_app(toml_file=str(config), icon="rig.ico", out_dir=tmp_path)

    (command,) = fake_pyinstaller
    assert command[command.index("--icon") + 1] == "rig.ico"


def test_pyvisas_backends_are_always_collected(fake_pyinstaller, config, tmp_path):
    freeze.build_app(toml_file=str(config), out_dir=tmp_path)

    (command,) = fake_pyinstaller
    collected = [
        command[i + 1] for i, arg in enumerate(command) if arg == "--collect-all"
    ]
    assert set(collected) == {"pyvisa", "pyvisa_py"}


def test_the_gui_page_is_always_collected(fake_pyinstaller, config, tmp_path):
    # The API server serves it with or without a window, and does not start
    # without it.
    freeze.build_app(toml_file=str(config), out_dir=tmp_path)

    (command,) = fake_pyinstaller
    collected = [
        command[i + 1] for i, arg in enumerate(command) if arg == "--collect-data"
    ]
    assert collected == ["pyacquisition.gui"]


def test_onefile_by_default(fake_pyinstaller, config, tmp_path):
    freeze.build_app(toml_file=str(config), out_dir=tmp_path)
    assert "--onefile" in fake_pyinstaller[0]
    assert "--onedir" not in fake_pyinstaller[0]


def test_onedir_when_asked(fake_pyinstaller, config, tmp_path):
    freeze.build_app(toml_file=str(config), onefile=False, out_dir=tmp_path)
    assert "--onedir" in fake_pyinstaller[0]
    assert "--onefile" not in fake_pyinstaller[0]


# ----------------------------------------------------------------- a py build
def test_a_py_build_freezes_the_script_itself_not_a_wrapper(fake_pyinstaller, tmp_path):
    script = tmp_path / "my_experiment.py"
    script.write_text("from pyacquisition import Experiment\n")

    freeze.build_app(py_file=str(script), out_dir=tmp_path)

    (command,) = fake_pyinstaller
    assert command[1] == str(script)


def test_a_py_build_names_itself_after_the_script(fake_pyinstaller, tmp_path):
    script = tmp_path / "my_experiment.py"
    script.write_text("")

    freeze.build_app(py_file=str(script), out_dir=tmp_path)

    (command,) = fake_pyinstaller
    assert command[command.index("--name") + 1] == "my_experiment"


def test_a_py_build_does_not_copy_any_config(fake_pyinstaller, tmp_path):
    script = tmp_path / "my_experiment.py"
    script.write_text("")

    app_dir = freeze.build_app(py_file=str(script), out_dir=tmp_path)

    assert not (app_dir / "config.toml").exists()


def test_pyinstaller_available_reflects_the_path(monkeypatch):
    monkeypatch.setattr(freeze.shutil, "which", lambda name: None)
    assert freeze.pyinstaller_available() is False

    monkeypatch.setattr(freeze.shutil, "which", lambda name: "/usr/bin/pyinstaller")
    assert freeze.pyinstaller_available() is True


# --------------------------------------------------------- a real build, end to end
@pytest.mark.slow  # about a minute: run with --slow
@pytest.mark.skipif(
    shutil.which("pyinstaller") is None, reason="pyinstaller is not installed"
)
def test_a_real_toml_build(tmp_path):
    """Freezes a genuine, tiny experiment and checks the result runs and serves
    the GUI's page. (It runs without a window: the window itself was checked by
    hand, in milestone 19 of specs/archive/new-gui.md.)"""
    # A free port: 8000 is often the docs server's, and other tests may be
    # running at the same time.
    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
    base = f"http://localhost:{port}"
    config = tmp_path / "rig.toml"
    config.write_text(
        '[experiment]\nroot_path = "."\n[gui]\nrun = false\n'
        f"[api_server]\nport = {port}\n"
        '[instruments]\nclock = {instrument = "Clock"}\n'
    )

    app_dir = freeze.build_app(
        toml_file=str(config), name="RigSmoke", out_dir=tmp_path, windowed=False
    )

    exe = app_dir / "RigSmoke.exe"
    assert exe.exists()
    assert (app_dir / "config.toml").exists()

    # What the GUI's window needs, which is found at runtime rather than
    # imported: pywebview's WebView2 libraries, pythonnet's .NET runtime and its
    # loader, and the page itself.
    from PyInstaller.archive.readers import CArchiveReader

    bundled = {name.replace("\\", "/") for name in CArchiveReader(str(exe)).toc}
    for name in (
        "webview/lib/Microsoft.Web.WebView2.Core.dll",
        "webview/lib/Microsoft.Web.WebView2.WinForms.dll",
        "webview/lib/runtimes/win-x64/native/WebView2Loader.dll",
        "pythonnet/runtime/Python.Runtime.dll",
        "clr_loader/ffi/dlls/amd64/ClrLoader.dll",
        "pyacquisition/gui/static/index.html",
        "pyacquisition/gui/static/js/main.js",
        "pyacquisition/gui/static/vendor/preact/preact.module.js",
    ):
        assert name in bundled, f"{name} is missing from the build"

    import time

    import requests

    # Unread output piped to the parent can fill the OS pipe buffer and block the
    # child, including its shutdown, so it goes to a file instead (as in the console
    # log it would write to a terminal, were one attached).
    with open(app_dir / "console.log", "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [str(exe)], stdout=log, stderr=subprocess.STDOUT, cwd=app_dir
        )
        try:
            for _ in range(200):
                try:
                    requests.get(f"{base}/ping", timeout=1)
                    break
                except requests.exceptions.RequestException:
                    time.sleep(0.25)
            else:
                raise AssertionError("the frozen app never answered /ping")

            assert requests.get(f"{base}/ping", timeout=2).json() == "pong"
            # The page, as the window loads it: its scripts as modules.
            page = requests.get(f"{base}/", timeout=5)
            assert page.status_code == 200 and 'type="module"' in page.text
            for path in ("/ui/js/main.js", "/ui/vendor/uplot/uPlot.esm.js"):
                script = requests.get(f"{base}{path}", timeout=5)
                assert script.status_code == 200
                assert script.headers["content-type"].startswith("text/javascript")
            try:
                requests.get(f"{base}/experiment/shutdown", timeout=5)
            except requests.exceptions.RequestException:
                pass  # the process may close the connection before the reply is read
            proc.wait(timeout=20)
            assert proc.returncode == 0
        finally:
            if proc.poll() is None:
                proc.kill()
