"""The Reference section of the docs lists what the code has: every driver, task,
calculation, adapter, option, command-line option and endpoint, so that none is
missing and none is out of date."""

import argparse
import inspect
import re
import shutil
import tomllib
from pathlib import Path

import pytest

from pyacquisition import Experiment, Task, main  # noqa: F401 - the CLI's module
from pyacquisition import tasks as included_tasks
from pyacquisition.core import settings
from pyacquisition.core.adapters import ADAPTERS
from pyacquisition.core.calculations import calculation_map
from pyacquisition.instruments import instrument_map

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "docs" / "reference"
NAV = tomllib.loads((ROOT / "zensical.toml").read_text(encoding="utf-8"))["project"]["nav"]


def page(name: str) -> str:
    return (REFERENCE / name).read_text(encoding="utf-8")


def nav_pages(items=NAV) -> list:
    """Every page in the nav, as its path under docs/."""
    found = []
    for item in items:
        for value in item.values():
            found += nav_pages(value) if isinstance(value, list) else [value]
    return found


def rows(text: str) -> dict:
    """A table's rows, by the name in backticks in their first cell."""
    return {
        m[1]: [cell.strip() for cell in m[2].split("|")]
        for m in re.finditer(r"^\| `([^`]+)` \|(.*)\|$", text, flags=re.M)
    }


# -------------------------------------------------------------- instruments
@pytest.mark.parametrize("name, driver", instrument_map.items())
def test_each_driver_has_a_page_in_the_nav(name, driver):
    pages = [p for p in (REFERENCE / "instruments").glob("*.md")
             if re.search(rf"^::: [\w.]*\b{driver.__name__}$", p.read_text(encoding="utf-8"), re.M)]
    assert pages, f"no page shows {driver.__name__}"
    assert f"reference/instruments/{pages[0].name}" in nav_pages()
    assert f"**{name}**" in page("instruments/overview.md"), f"{name} isn't on the overview"


# -------------------------------------------------------------- tasks
INCLUDED = sorted(
    name for name, cls in vars(included_tasks).items()
    if inspect.isclass(cls) and issubclass(cls, Task) and cls is not Task
)


@pytest.mark.parametrize("name", INCLUDED)
def test_each_included_task_has_a_page_in_the_nav(name):
    pages = [p for p in (REFERENCE / "tasks").glob("*.md")
             if re.search(rf"^::: [\w.]*\b{name}$", p.read_text(encoding="utf-8"), re.M)]
    assert pages, f"no page shows {name}"
    assert f"reference/tasks/{pages[0].name}" in nav_pages()
    assert f"**{name}**" in page("tasks/overview.md"), f"{name} isn't on the overview"


# -------------------------------------------------------------- calculations and adapters
@pytest.mark.parametrize("name", calculation_map)
def test_each_calculation_that_a_config_can_name_has_a_section(name):
    assert f"## `{name}`" in page("calculations.md")


@pytest.mark.parametrize("name", ADAPTERS)
def test_each_adapter_has_a_section(name):
    assert f"## `{name}`" in page("adapters.md")


# -------------------------------------------------------------- experiment options
@pytest.mark.parametrize("setting", settings.SETTINGS.values(), ids=lambda s: s.name)
def test_each_option_is_listed_once_with_its_help_and_key(setting):
    text = page("experiment_options.md")
    assert text.count(f"| `{setting.name}` |") == 1
    meaning, _default, key = rows(text)[setting.name]
    assert meaning == setting.help
    assert key == f"`[{setting.section}] {setting.key}`"


# -------------------------------------------------------------- the command line
def options(parser: argparse.ArgumentParser) -> set:
    """A parser's options and positional arguments, without --help."""
    found = set()
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction | argparse._SubParsersAction):
            continue
        found.update(action.option_strings or [action.dest])
    return found


def test_every_command_and_option_of_pyacquisition_is_listed():
    import pyacquisition

    text = page("command_line.md")
    parser = pyacquisition._build_parser()
    commands = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    for command, subparser in commands.choices.items():
        assert f"## `pyacquisition {command}`" in text
        section = text.split(f"## `pyacquisition {command}`")[1].split("\n## ")[0]
        for option in options(subparser):
            assert f"`{option}" in section, f"pyacquisition {command} {option}"


def test_every_option_of_the_verification_tool_is_listed():
    from pyacquisition.verify.__main__ import build_parser

    section = page("command_line.md").split("## `python -m pyacquisition.verify`")[1]
    for option in options(build_parser()):
        assert f"`{option}" in section, option


# -------------------------------------------------------------- the web API
def routes(tmp_path) -> set:
    """The paths a running experiment serves, registered as `Experiment._run` does."""
    shutil.copy(ROOT / "examples" / "getting_started" / "rig.toml", tmp_path / "rig.toml")
    experiment = Experiment.from_config(str(tmp_path / "rig.toml"), root_path=str(tmp_path), gui=False)
    api = experiment._api_server
    experiment._register_endpoints(api)
    for component in (
        api, experiment._rack, experiment._calculations, experiment._scribe,
        experiment._history, experiment._log_history, experiment._trace_scribe,
        *experiment.task_managers.values(),
    ):
        component._register_endpoints(api)
    experiment._register_instrument_tasks()
    experiment._register_instrument_calls()
    return {route.path for route in api.app.routes}


def test_every_endpoint_on_the_page_is_served(tmp_path):
    served = routes(tmp_path)
    patterns = [re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", path) + "$") for path in served]
    listed = set(re.findall(r"`(/[^`\s]*)`", page("web_api.md")))
    assert len(listed) > 30
    # The page's placeholders, as this experiment has them
    examples = {"<instrument>": "clock", "<method>": "time", "<task>": "waitfor", "<trace>": "spectrum"}
    for path in listed:
        if path.startswith("/managers/<name>/") or path.endswith("/..."):
            continue  # another task manager's, which this experiment hasn't, or a family
        path = path.split("?")[0]
        for placeholder, example in examples.items():
            path = path.replace(placeholder, example)
        assert "<" not in path, f"{path}: a placeholder the test doesn't know"
        assert any(p.match(path) for p in patterns), path
