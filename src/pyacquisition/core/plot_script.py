"""A plot as a Python script: code that reads the data files and draws the plot
again with matplotlib, for a paper or a slide.

`plot_script` writes the script from a plot's settings (a `PlotRequest`) and
from where its data is. It is kept apart from the experiment so that it can be
tested without one: the experiment's `/experiment/plot_script` endpoint gathers
the files, the folder, the delimiter and the units, and calls it.

The script is meant to be read and changed by people who aren't expert
programmers, so it is plain, top-to-bottom code: constants, a small `read()`,
then one `ax.plot(...)` line for each series drawn from each file. The names in
it (columns and files) are the user's data, and are only ever written as string
literals, so no name can break the script or add code to it.
"""

import math
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

MAX_SERIES = 8
COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")

# How each way of drawing is written: the format string, and each file's
# markersize (the previous file's a little smaller, as on screen).
FORMATS = {"lines": "-", "points": "o", "both": "-o"}
MARKERSIZE = {"current": 3, "previous": 2.5}
LINEWIDTH = {"current": 1.5, "previous": 1}
PREVIOUS_ALPHA = 0.35


class Series(BaseModel):
    """A column drawn against x, in the colour it has on screen."""

    name: str
    colour: str = Field(description="The colour it is drawn in, as #rrggbb.")


class PlotRequest(BaseModel):
    """A plot panel's settings: what it draws and how."""

    x: str = Field(description="The x column.")
    series: list[Series] = Field(
        description="The shown y columns in order, each with its #rrggbb colour. 1 to 8."
    )
    marks: Literal["lines", "points", "both"] = Field(
        "lines", description="How the data is drawn."
    )
    log_x: bool = Field(False, description="Whether the x axis is logarithmic.")
    log_y: bool = Field(False, description="Whether the y axis is logarithmic.")
    x_limits: list[float] | None = Field(
        None, description="The x axis's range, [min, max], or null to fit the data."
    )
    y_limits: list[float] | None = Field(
        None, description="The y axis's range, [min, max], or null to fit the data."
    )
    previous: bool = Field(False, description="Whether the previous file is drawn too.")


class PlotScriptError(ValueError):
    """A request the script can't be written for. Its message says why, to be
    shown as it is."""


def plot_script(
    request: PlotRequest,
    *,
    folder: str,
    current_file: str,
    previous_file: str | None,
    delimiter: str,
    units: dict[str, str | None],
    columns: dict[str, set[str] | None],
    now: datetime,
) -> str:
    """The text of a script that draws the plot the request describes.

    Args:
        request: The plot's settings.
        folder: The folder the data files are in.
        current_file: The name of the current data file.
        previous_file: The name of the file before it, or None. It is only
            drawn if `request.previous` is true too.
        delimiter: The data files' delimiter.
        units: The unit of each column that has one.
        columns: The columns each file has, by its name. A series is drawn from
            a file only if the file has it and x. A file given None, or left out
            (one with no rows yet), is taken to have them all.
        now: When the plot was exported, for the script's docstring.

    Raises:
        PlotScriptError: The request can't be drawn: no series, or more than
            8; a colour that isn't #rrggbb; limits that aren't two finite
            numbers, the smaller first, or that reach 0 or below on a log axis;
            or x or a series that isn't a column of any file it would read.
    """
    previous_file = previous_file if request.previous else None
    _check(request, [columns.get(f) for f in (current_file, previous_file) if f])
    names = [s.name for s in request.series]

    def drawn(file: str) -> list[Series]:
        known = columns.get(file)
        if known is None:
            return list(request.series)
        if request.x not in known:
            return []
        return [s for s in request.series if s.name in known]

    current = drawn(current_file)
    previous = drawn(previous_file) if previous_file else []
    if not current and not previous:
        raise PlotScriptError(
            f"No data file has both {request.x!r} and one of the series, to draw it."
        )
    fmt = _literal(FORMATS[request.marks])

    def line(frame: str, series: Series, which: str) -> str:
        style = [f"color={_literal(series.colour.lower())}", f"linewidth={LINEWIDTH[which]}"]
        if request.marks != "lines":
            style.append(f"markersize={MARKERSIZE[which]}")
        if which == "previous":
            style.append(f"alpha={PREVIOUS_ALPHA}")
        else:
            style.append(f"label={_literal(_label(series.name, units))}")
        return (
            f"ax.plot({frame}[{_literal(request.x)}], {frame}[{_literal(series.name)}], "
            f"{fmt}, {', '.join(style)})"
        )

    summary = f"{', '.join(map(_plain, names))} against {_plain(request.x)}"
    docstring = (
        f"A plot exported from pyacquisition on {now:%Y-%m-%d} at {now:%H:%M}: {summary}.\n"
        "\n"
        "Run it with Python to draw the plot, then change anything you like. It reads\n"
        "the data files named below, and needs pandas and matplotlib\n"
        "(`pip install pandas matplotlib`).\n"
    )
    out = [
        f'"""{_docstring_text(docstring)}"""',
        "",
        "from pathlib import Path",
        "",
        "import matplotlib.pyplot as plt",
        "import pandas as pd",
        "",
        "# The data files. If they aren't in FOLDER, they are looked for beside this script.",
        f"FOLDER = Path({_path_literal(folder)})",
        f"FILE = {_literal(current_file)}",
    ]
    if previous:
        out.append(f"PREVIOUS_FILE = {_literal(previous_file)}  # None to leave it out")
    out += [
        f"DELIMITER = {_literal(delimiter)}",
        "",
        "",
        "def read(name):",
        '    """One data file, as a pandas DataFrame."""',
        "    for folder in (FOLDER, Path(__file__).resolve().parent):",
        "        if (folder / name).exists():",
        "            return pd.read_csv(folder / name, sep=DELIMITER)",
        '    raise FileNotFoundError(f"{name} is in neither {FOLDER} nor this script\'s folder")',
        "",
        "",
        "data = read(FILE)",
    ]
    if previous:
        out.append("previous = read(PREVIOUS_FILE) if PREVIOUS_FILE else None")
    out += ["", "fig, ax = plt.subplots()", ""]
    if previous:
        out.append("# The previous file, fainter, behind the current one.")
        out.append("if previous is not None:")
        out += [f"    {line('previous', s, 'previous')}" for s in previous]
        out.append("")
    out += [line("data", s, "current") for s in current]
    out += [
        "",
        f"ax.set_xlabel({_literal(_label(request.x, units))})",
        f"ax.set_ylabel({_literal(', '.join(_label(n, units) for n in names))})",
    ]
    if request.log_x:
        out.append('ax.set_xscale("log")')
    if request.log_y:
        out.append('ax.set_yscale("log")')
    if request.x_limits is not None:
        low, high = request.x_limits
        out.append(
            f"ax.set_xlim({float(low)!r}, {float(high)!r})"
            "  # as the plot showed it; delete for all the data"
        )
    if request.y_limits is not None:
        low, high = request.y_limits
        out.append(f"ax.set_ylim({float(low)!r}, {float(high)!r})")
    out += ["ax.legend()", "fig.tight_layout()", "plt.show()", ""]
    return "\n".join(out)


def _check(request: PlotRequest, known: list[set[str] | None]) -> None:
    """Raises a PlotScriptError saying what is wrong with the request, if
    anything is. `known` is the columns of each file it would read."""
    if not request.series:
        raise PlotScriptError("There are no series to draw.")
    if len(request.series) > MAX_SERIES:
        raise PlotScriptError(
            f"A plot draws at most {MAX_SERIES} series, not {len(request.series)}."
        )
    for series in request.series:
        if not COLOUR.match(series.colour):
            raise PlotScriptError(
                f"The colour of {series.name!r} is {series.colour!r}, not #rrggbb."
            )
    for axis, limits, log in (
        ("x", request.x_limits, request.log_x),
        ("y", request.y_limits, request.log_y),
    ):
        if limits is None:
            continue
        if len(limits) != 2 or not all(math.isfinite(v) for v in limits):
            raise PlotScriptError(f"The {axis} limits must be two finite numbers.")
        if not limits[0] < limits[1]:
            raise PlotScriptError(f"The {axis} limits must be given smaller first.")
        if log and limits[0] <= 0:
            raise PlotScriptError(f"The {axis} axis is logarithmic, so its limits must be above 0.")
    if any(k is None for k in known):
        return  # a file's columns aren't known yet: it may have any of them
    everything = set().union(*known)
    for name in [request.x] + [s.name for s in request.series]:
        if name not in everything:
            raise PlotScriptError(f"{name!r} isn't a column of the data files.")


def _label(name: str, units: dict[str, str | None]) -> str:
    """An axis's or a line's label, as the page writes it: the name, and its
    unit in brackets if it has one."""
    unit = units.get(name)
    return f"{name} ({unit})" if unit else name


def _literal(text: str) -> str:
    """A string literal for the text: its `repr()`, in double quotes where
    that needs no escaping, as people usually write them."""
    literal = repr(text)
    if literal.startswith("'") and '"' not in text:
        return f'"{literal[1:-1]}"'
    return literal


def _path_literal(folder: str) -> str:
    """A string literal for a folder: a raw string, so a Windows path reads as
    it is written, unless that can't hold it."""
    if '"' in folder or folder.endswith("\\") or not folder.isprintable():
        return _literal(folder)
    return f'r"{folder}"'


def _plain(name: str) -> str:
    """A name, to be written in the docstring: on one line, a space for anything
    that doesn't print."""
    return "".join(c if c.isprintable() else " " for c in name)


def _docstring_text(text: str) -> str:
    """The text, to go between triple quotes: the column names in it are
    anyone's, so their backslashes and quotes are escaped."""
    return text.replace("\\", "\\\\").replace('"', '\\"')
