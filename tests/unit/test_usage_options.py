"""Usage › Set the experiment's options (docs/usage/options.md): each version of
lab.py sets the options the page says, the file wins over the class and an
argument over both, and mistakes are refused with the page's messages."""

import importlib.util
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "options"
GETTING_STARTED = ROOT / "examples" / "getting_started"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def lab_class(version: int, source: str | None = None):
    path = HERE / f"lab_{version}.py"
    spec = importlib.util.spec_from_loader(f"options_lab_{version}", loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(compile(source or text(path), str(path), "exec"), module.__dict__)
    return module.Lab


def made(version: int, rig: int, tmp_path, **arguments):
    rig_file = tmp_path / "rig.toml"
    rig_file.write_text(text(HERE / f"rig_{rig}.toml"), encoding="utf-8")
    return lab_class(version).from_config(str(rig_file), root_path=str(tmp_path), gui=False, **arguments)


def test_it_starts_from_the_end_of_getting_started():
    assert text(HERE / "lab_1.py") == text(GETTING_STARTED / "lab_6.py")
    assert text(HERE / "rig_1.toml") == text(GETTING_STARTED / "rig.toml")


def test_the_data_go_in_a_folder_for_the_sample_and_the_day(tmp_path):
    experiment = made(2, 1, tmp_path)
    today = time.strftime("%Y-%m-%d")
    assert experiment._data_path == tmp_path / "data" / "sample_A" / today


def test_the_terminal_shows_info_and_above(tmp_path):
    assert lab_class(3).console_log_level == "INFO"
    made(3, 1, tmp_path)  # made without a problem


def test_the_port_and_its_fallbacks(tmp_path):
    server = made(4, 1, tmp_path)._api_server
    assert server.port == 8001
    assert tuple(server.fallback_ports) == (8002, 8003)


def test_the_file_s_period_wins_over_the_class(tmp_path):
    assert lab_class(5).measurement_period == 0.5
    assert made(5, 1, tmp_path)._rack.period == 0.2


def test_without_it_in_the_file_the_class_s_period_applies(tmp_path):
    assert "[rack]" not in text(HERE / "rig_2.toml")
    assert made(5, 2, tmp_path)._rack.period == 0.5


def test_an_argument_wins_over_both(tmp_path):
    assert made(5, 1, tmp_path, measurement_period=1.0)._rack.period == 1.0


def test_a_misspelt_option_is_refused_as_the_class_is_made():
    source = text(HERE / "lab_5.py").replace("    console_log_level", "    console_log_levl")
    with pytest.raises(TypeError, match=r"^`console_log_levl` in Lab looks like a misspelling of the option `console_log_level`, so it would do nothing\."):
        lab_class(5, source)


def test_a_wrong_value_is_refused_as_the_experiment_is_made(tmp_path):
    source = text(HERE / "lab_5.py").replace("measurement_period = 0.5", 'measurement_period = "fast"')
    lab = lab_class(5, source)
    (tmp_path / "rig.toml").write_text(text(HERE / "rig_2.toml"), encoding="utf-8")
    with pytest.raises(ValueError, match=r"Failed to create Experiment instance: `measurement_period` must be a positive number, got 'fast'$"):
        lab.from_config(str(tmp_path / "rig.toml"), root_path=str(tmp_path), gui=False)
