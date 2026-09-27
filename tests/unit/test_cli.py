"""The `pyacquisition` command: `run` an experiment, or `build` it into an app."""

import sys
from unittest.mock import Mock

import pytest

import pyacquisition
from pyacquisition import Experiment, main


@pytest.fixture(autouse=True)
def in_a_folder_of_its_own(monkeypatch, tmp_path):
    """The experiments these make have no `root_path`, so they write their log
    (and data) where they are run from: here, not the repository."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def no_run(monkeypatch):
    """Stops an experiment from actually starting, and hands back what would run."""
    started = []
    monkeypatch.setattr(Experiment, "run", lambda self: started.append(self))
    return started


# --------------------------------------------------------------------- run
def test_run_with_a_toml_file(no_run, tmp_path):
    config = tmp_path / "rig.toml"
    config.write_text("")

    main("run", "--toml", str(config))

    assert len(no_run) == 1


def test_the_bare_flags_still_work_with_no_subcommand(no_run, tmp_path):
    """Backward compatibility: `pyacquisition --toml x.toml` used to be the whole
    command, before `run` and `build` existed."""
    config = tmp_path / "rig.toml"
    config.write_text("")

    main("--toml", str(config))

    assert len(no_run) == 1


def test_run_with_a_python_script(no_run, tmp_path):
    script = tmp_path / "my_experiment.py"
    script.write_text(
        "from pyacquisition import Experiment\n"
        "class MyExperiment(Experiment):\n"
        "    gui = False\n"
    )

    main("run", "--py", str(script))

    assert len(no_run) == 1
    assert type(no_run[0]).__name__ == "MyExperiment"


def test_run_needs_exactly_one_of_toml_or_py(capsys):
    with pytest.raises(SystemExit):
        main("run")
    assert "required" in capsys.readouterr().err.lower()


def test_run_refuses_both_toml_and_py(tmp_path, capsys):
    config = tmp_path / "rig.toml"
    config.write_text("")
    script = tmp_path / "my_experiment.py"
    script.write_text("")

    with pytest.raises(SystemExit):
        main("run", "--toml", str(config), "--py", str(script))

    assert "not allowed" in capsys.readouterr().err.lower()


def test_an_unknown_python_file_is_a_clear_error():
    with pytest.raises(FileNotFoundError):
        main("run", "--py", "no_such_file.py")


# ------------------------------------------------------------------- build
def test_build_calls_build_app_with_the_toml_file(monkeypatch, tmp_path, capsys):
    config = tmp_path / "rig.toml"
    config.write_text("")
    seen = {}

    def fake_build_app(**kwargs):
        seen.update(kwargs)
        return tmp_path / "dist" / "rig"

    monkeypatch.setattr("pyacquisition.freeze.build_app", fake_build_app)

    main("build", "--toml", str(config))

    assert seen == {
        "toml_file": str(config),
        "py_file": None,
        "name": None,
        "onefile": True,
        "windowed": True,
        "icon": None,
    }
    assert "Built" in capsys.readouterr().out


def test_build_passes_through_its_own_options(monkeypatch, tmp_path):
    config = tmp_path / "rig.toml"
    config.write_text("")
    seen = {}
    monkeypatch.setattr(
        "pyacquisition.freeze.build_app",
        lambda **kwargs: seen.update(kwargs) or tmp_path,
    )

    main(
        "build",
        "--toml",
        str(config),
        "--name",
        "MyRig",
        "--onedir",
        "--console",
        "--icon",
        "rig.ico",
    )

    assert seen["name"] == "MyRig"
    assert seen["onefile"] is False  # --onedir
    assert seen["windowed"] is False  # --console
    assert seen["icon"] == "rig.ico"


def test_build_with_a_python_script(monkeypatch, tmp_path):
    script = tmp_path / "my_experiment.py"
    script.write_text("")
    seen = {}
    monkeypatch.setattr(
        "pyacquisition.freeze.build_app",
        lambda **kwargs: seen.update(kwargs) or tmp_path,
    )

    main("build", "--py", str(script))

    assert seen["py_file"] == str(script)
    assert seen["toml_file"] is None


def test_build_needs_exactly_one_of_toml_or_py(capsys):
    with pytest.raises(SystemExit):
        main("build")
    assert "required" in capsys.readouterr().err.lower()


def test_a_failed_build_exits_cleanly_with_the_reason(monkeypatch, tmp_path, capsys):
    config = tmp_path / "rig.toml"
    config.write_text("")

    def fails(**kwargs):
        raise FileNotFoundError("PyInstaller is not installed.")

    monkeypatch.setattr("pyacquisition.freeze.build_app", fails)

    with pytest.raises(SystemExit, match="PyInstaller is not installed"):
        main("build", "--toml", str(config))


def test_the_freeze_module_is_not_imported_just_to_run(no_run, tmp_path):
    """Running an experiment must not require pyinstaller to be installed, so the
    module that shells out to it is only imported by the `build` subcommand."""
    sys.modules.pop("pyacquisition.freeze", None)
    config = tmp_path / "rig.toml"
    config.write_text("")

    main("run", "--toml", str(config))

    assert "pyacquisition.freeze" not in sys.modules


# ------------------------------------------------------------ freeze_support
def test_pyacquisition_calls_freeze_support_on_import(monkeypatch):
    """So a frozen build's spawned child does not re-run the whole script instead
    of becoming the child process (see the comment in __init__.py)."""
    called = Mock()
    monkeypatch.setattr("multiprocessing.freeze_support", called)

    import importlib

    importlib.reload(pyacquisition)

    called.assert_called_once()
