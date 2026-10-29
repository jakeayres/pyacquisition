"""The Pythons the package is tested on: the `3.N` classifiers in `pyproject.toml`.

The install check (`test_install_wheels.py`) runs on each of them, and on the
next one as an expected failure. `test_python_list.py` keeps `requires-python`
and the installation page in step with them."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLASSIFIER = re.compile(r"Programming Language :: Python :: (3\.\d+)")


def _project() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def listed() -> list[str]:
    """The listed Pythons, oldest first, such as `["3.11", "3.12"]`."""
    found = [m.group(1) for c in _project().get("classifiers", []) if (m := CLASSIFIER.fullmatch(c))]
    return sorted(found, key=lambda version: int(version.split(".")[1]))


def next_after(versions: list[str]) -> str:
    """The minor version after the last of `versions`: `"3.15"` after `"3.14"`."""
    major, minor = versions[-1].split(".")
    return f"{major}.{int(minor) + 1}"


def requires_python() -> str:
    return _project()["requires-python"]
