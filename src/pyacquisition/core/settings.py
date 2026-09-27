"""The options of an experiment, described once.

Every option is a class attribute of `Experiment`, so a subclass sets it by
naming it:

    class MyExperiment(Experiment):
        data_path = "my_data"
        measurement_period = 0.5

The table below is the single description of those options: the built-in
default, what counts as a valid value, and where the option sits in a TOML file.
It provides the defaults of `Experiment`, checks the values an experiment ends up
with, reads them out of a TOML file, and catches a misspelt option in a subclass.

A value is taken from the first of these that gives one:

1. An argument to `Experiment(...)` or `Experiment.from_config(...)`.
2. The TOML file.
3. A class attribute of the subclass.
4. The built-in default here.
"""

import difflib
import math
import os
from dataclasses import dataclass
from typing import Any, Callable

from .logging import logger

LOG_LEVELS = ("TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL")


def _text(name, value):
    if not isinstance(value, str):
        raise ValueError(f"`{name}` must be text, got {value!r}")
    return value


def _path(name, value):
    if not isinstance(value, (str, os.PathLike)):
        raise ValueError(f"`{name}` must be a path, got {value!r}")
    return value


def _level(name, value):
    if not isinstance(value, str) or value.upper() not in LOG_LEVELS:
        raise ValueError(
            f"`{name}` must be one of {', '.join(LOG_LEVELS)}, got {value!r}"
        )
    return value.upper()


def _port(name, value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
        raise ValueError(
            f"`{name}` must be a port number from 1 to 65535, got {value!r}"
        )
    return value


def _ports(name, value):
    """A list of port numbers (a TOML array, or a list or tuple in Python)."""
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"`{name}` must be a list of port numbers, got {value!r}")
    for port in value:
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError(
                f"`{name}` must be a list of port numbers from 1 to 65535, "
                f"got {port!r} in it"
            )
    return tuple(value)


def _seconds(name, value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"`{name}` must be a positive number, got {value!r}")
    return value


def _count(name, value, minimum=2, maximum=10_000):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise ValueError(
            f"`{name}` must be a whole number from {minimum} to {maximum}, got {value!r}"
        )
    return value


def _history_points(name, value):
    return _count(name, value, minimum=100, maximum=100_000_000)


def _flag(name, value):
    if not isinstance(value, bool):
        raise ValueError(f"`{name}` must be True or False, got {value!r}")
    return value


GUIS = ("new",)
DEFAULT_GUI = "new"  # the GUI that `gui = True` runs

# GUIs that have gone, and what to say to anyone who still asks for one.
REMOVED_GUIS = {
    "classic": (
        "The classic GUI (Dear PyGui) has been removed. `gui = True` runs the "
        "web GUI that replaced it, so use that (or leave the option out)."
    ),
}


def _gui(name, value):
    """True (the default GUI), False (none), or the name of a GUI."""
    if isinstance(value, str) and value.lower() in REMOVED_GUIS:
        raise ValueError(f"`{name}`: {REMOVED_GUIS[value.lower()]}")
    if isinstance(value, str) and value.lower() in GUIS:
        return value.lower()
    if not isinstance(value, bool):
        raise ValueError(
            f"`{name}` must be True, False or {' or '.join(map(repr, GUIS))}, "
            f"got {value!r}"
        )
    return value


def gui_to_run(value) -> str | None:
    """The name of the GUI that the value of the `gui` option runs, or None."""
    if value is True:
        return DEFAULT_GUI
    return value or None


@dataclass(frozen=True)
class Setting:
    """One option of an experiment.

    Attributes:
        name: The class attribute and constructor argument.
        default: The value when nothing else gives one.
        check: Returns the value if it is valid, and raises `ValueError` if not.
        section: The TOML section it is read from.
        key: The key within that section.
    """

    name: str
    default: Any
    check: Callable[[str, Any], Any]
    section: str
    key: str


SETTINGS = {
    setting.name: setting
    for setting in (
        Setting("root_path", ".", _path, "experiment", "root_path"),
        Setting("data_path", ".", _path, "data", "path"),
        Setting("data_file_extension", "data", _text, "data", "file_extension"),
        Setting("data_delimiter", ",", _text, "data", "delimiter"),
        Setting("history_points", 500_000, _history_points, "data", "history_points"),
        Setting("log_path", ".", _path, "logging", "path"),
        Setting("log_file_name", "debug.log", _text, "logging", "file_name"),
        Setting("console_log_level", "DEBUG", _level, "logging", "console_level"),
        Setting("file_log_level", "DEBUG", _level, "logging", "file_level"),
        Setting("gui_log_level", "DEBUG", _level, "logging", "gui_level"),
        Setting("api_server_host", "localhost", _text, "api_server", "host"),
        Setting("api_server_port", 8000, _port, "api_server", "port"),
        Setting(
            "api_server_fallback_ports", (), _ports, "api_server", "fallback_ports"
        ),
        Setting("measurement_period", 0.25, _seconds, "rack", "period"),
        Setting("gui", True, _gui, "gui", "run"),
        Setting("auto_tasks", True, _flag, "experiment", "auto_tasks"),
    )
}

# TOML keys that did something once, and now do nothing. A file that still has
# one works, with a warning, rather than being refused as a mistake.
REMOVED_KEYS = {
    ("gui", "sparkline_points"): "it set the classic GUI's small graphs, which have gone",
}


def resolve(experiment, arguments: dict) -> dict:
    """The value of every option for an experiment, checked.

    Args:
        experiment: The experiment being built. Its class attributes, which
            include any the subclass sets, are used for options not in `arguments`.
        arguments: The options that were passed in. `None` means not given.

    Returns:
        dict: The value of each option, by name.

    Raises:
        ValueError: If a value is not valid.
    """
    values = {}
    for name, setting in SETTINGS.items():
        value = arguments.get(name)
        if value is None:
            value = getattr(experiment, name)
        values[name] = setting.check(name, value)
    return values


def from_config(config: dict) -> dict:
    """The options a parsed TOML file sets. Options it leaves out are not included.

    Raises:
        ValueError: If a section holds a key that is not an option, or is not a table.
    """
    values = {}
    for section in dict.fromkeys(setting.section for setting in SETTINGS.values()):
        table = config.get(section, {})
        if not isinstance(table, dict):
            raise ValueError(f"[{section}] must be a table")
        keys = {s.key: s for s in SETTINGS.values() if s.section == section}
        for key, value in table.items():
            if (section, key) in REMOVED_KEYS:
                logger.warning(
                    f"'{key}' in [{section}] does nothing now "
                    f"({REMOVED_KEYS[section, key]}), so it can be removed."
                )
                continue
            if key not in keys:
                raise ValueError(
                    f"Unknown key '{key}' in [{section}]"
                    f"{_suggestion(key, keys)}. Valid keys: {', '.join(keys)}."
                )
            values[keys[key].name] = value
    return values


def check_subclass(cls) -> None:
    """Raises if a subclass of `Experiment` sets a name that looks like a misspelt option.

    An attribute set on a subclass that is not an option is fine, unless its name
    is close to one: `data_pth = "my_data"` would otherwise be ignored without a
    word, and the data would go to the wrong folder.

    Raises:
        TypeError: If a name is close to an option's name but is not it.
    """
    inherited = {name for base in cls.__mro__[1:] for name in vars(base)}
    for name in vars(cls):
        if name.startswith("_") or name in SETTINGS or name in inherited:
            continue
        close = difflib.get_close_matches(name.lower(), SETTINGS, n=1, cutoff=0.8)
        if close:
            raise TypeError(
                f"`{name}` in {cls.__name__} looks like a misspelling of the "
                f"option `{close[0]}`, so it would do nothing. Use `{close[0]}`, "
                f"or give `{name}` a different name if it is something else."
            )


def _suggestion(name, options) -> str:
    close = difflib.get_close_matches(name, options, n=1, cutoff=0.6)
    return f" (did you mean '{close[0]}'?)" if close else ""
