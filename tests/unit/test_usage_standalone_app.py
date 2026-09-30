"""Usage › Build a standalone app (docs/usage/standalone_app.md): every command on
the page parses as `pyacquisition` would take it, and builds what the page says,
with PyInstaller faked (a real build is `test_freeze.py`'s, with --slow)."""

import re
import shlex
from pathlib import Path

import pytest

from pyacquisition import _build_parser, freeze

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "usage" / "standalone_app.md"
GETTING_STARTED = ROOT / "examples" / "getting_started"


def commands() -> list[list[str]]:
    """The page's `uv run pyacquisition ...` commands, as argument lists."""
    blocks = re.findall(r"```bash\n(.*?)```", PAGE.read_text(encoding="utf-8"), re.S)
    found = []
    for block in blocks:
        for line in block.splitlines():
            if line.startswith("uv run pyacquisition "):
                found.append(shlex.split(line)[3:])
    return found


def test_the_page_has_its_three_builds():
    assert [c[:2] for c in commands()] == [["build", "--toml"], ["build", "--py"], ["build", "--py"]]


@pytest.mark.parametrize("arguments", commands())
def test_each_command_parses(arguments):
    parsed = _build_parser().parse_args(arguments)
    assert parsed.command == "build"


def test_the_named_folder_build_asks_for_what_the_page_says():
    parsed = _build_parser().parse_args(commands()[2])
    assert (parsed.py, parsed.name, parsed.onedir) == ("lab.py", "My Lab", True)


def test_the_install_line_is_the_build_extra():
    assert 'uv add "pyacquisition[build]"' in PAGE.read_text(encoding="utf-8")


def test_without_pyinstaller_the_build_says_what_to_do(monkeypatch, tmp_path):
    monkeypatch.setattr(freeze, "pyinstaller_available", lambda: False)
    (tmp_path / "rig.toml").write_text((GETTING_STARTED / "rig.toml").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(FileNotFoundError, match=r"^PyInstaller is not installed\. Add it with `uv add pyacquisition\[build\]`"):
        freeze.build_app(toml_file=str(tmp_path / "rig.toml"), out_dir=tmp_path)


def test_a_config_with_a_mistake_is_refused_before_building(monkeypatch, tmp_path):
    monkeypatch.setattr(freeze, "pyinstaller_available", lambda: True)
    rig = tmp_path / "rig.toml"
    rig.write_text('[instruments]\nclock = { instrument = "Clok" }\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"rig\.toml has 1 problem"):
        freeze.build_app(toml_file=str(rig), out_dir=tmp_path)
