"""A plot as a Python script: code that reads the data files and draws the plot
again with matplotlib, for a paper or a slide.

`plot_script` writes the script from a plot's settings (a `PlotRequest`) and
from where its data is. It is kept apart from the experiment so that it can be
tested without one: the experiment's `/experiment/plot_script` endpoint gathers
the files, the folder, the delimiter and the units, and calls it.

There are two styles. `"screen"` draws the plot as the page does, in
matplotlib's own style. `"aps"` draws it as a figure for an APS journal (PRB,
PRL): one column wide and square, STIX serif fonts, inward ticks on all four
sides, and each axis scaled for tidy numbers (see `axis_scale`), and it saves a
PDF beside the script.

The script is meant to be read and changed by people who aren't expert
programmers, so it is plain, top-to-bottom code: constants, a small `read()`,
then one `ax.plot(...)` line for each series drawn from each file. The names in
it (columns and files) are the user's data, and are only ever written as string
literals, so no name can break the script or add code to it.
"""

import math
import re
from collections.abc import Sequence
from datetime import datetime
from typing import Literal, NamedTuple

import numpy as np
from pydantic import BaseModel, Field

MAX_SERIES = 8
COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")

# How each way of drawing is written: the format string, and each file's
# markersize (the previous file's a little smaller, as on screen).
FORMATS = {"lines": "-", "points": "o", "both": "-o"}
MARKERSIZE = {"current": 3, "previous": 2.5}
LINEWIDTH = {"current": 1.5, "previous": 1}
PREVIOUS_ALPHA = 0.35

# The APS figure: one column wide (3.375 in), square.
APS_SIZE = 3.375
# Its style, as the script writes it: one setting a line, each easy to change.
APS_STYLE = [
    ("font.family", "STIXGeneral"),
    ("mathtext.fontset", "stix"),
    ("font.size", 9),
    ("axes.labelsize", 9),
    ("xtick.labelsize", 8),
    ("ytick.labelsize", 8),
    ("legend.fontsize", 8),
    ("axes.linewidth", 0.6),
    ("xtick.direction", "in"),
    ("ytick.direction", "in"),
    ("xtick.top", True),
    ("ytick.right", True),
    ("xtick.minor.visible", True),
    ("ytick.minor.visible", True),
    ("xtick.major.size", 3.5),
    ("ytick.major.size", 3.5),
    ("xtick.minor.size", 2),
    ("ytick.minor.size", 2),
    ("xtick.major.width", 0.6),
    ("ytick.major.width", 0.6),
    ("xtick.minor.width", 0.5),
    ("ytick.minor.width", 0.5),
    ("xtick.major.pad", 3),
    ("ytick.major.pad", 3),
    ("axes.labelpad", 4),
    ("axes.formatter.use_mathtext", True),
    ("lines.linewidth", 1.0),
    ("lines.markersize", 3),
    ("lines.markeredgewidth", 0.5),
    ("legend.frameon", False),
    ("pdf.fonttype", 42),
]

# The units an SI prefix can be put in front of, without being misread. Any
# other unit (one with a prefix already, or a compound one) is scaled by a
# power of ten written in its label instead.
BASE_UNITS = {"V", "A", "K", "s", "Hz", "T", "W", "J", "C", "S", "F", "H", "Pa", "m", "g", "Ω", "Ohm"}
PREFIXES = {-12: "p", -9: "n", -6: "µ", -3: "m", 3: "k", 6: "M", 9: "G"}
# An axis whose spread is less than this part of its largest value (such as
# Unix time) isn't scaled: matplotlib's offset shows its changes better.
OFFSET_SPREAD = 1e-3


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
    style: Literal["screen", "aps"] = Field(
        "screen",
        description='"screen" to draw it as the page does, or "aps" for a figure '
        "in the style of an APS journal.",
    )


class Scale(NamedTuple):
    """How an axis of an APS figure is scaled: its values are multiplied by
    10 to the power of `-exponent` (a multiple of 3; 0 for not at all), and its
    label's unit becomes `unit`, as matplotlib text (a `$` in it escaped)."""

    exponent: int
    unit: str | None


def axis_scale(largest: float, spread: float, unit: str | None) -> Scale:
    """How to scale an axis whose largest absolute value is `largest`, whose
    values span `spread`, and whose unit is `unit` (or None): by a power of
    1000 that brings `largest` between 1 and 1000, with the SI prefix put in
    front of a base unit (`µV`), or the power of ten written in the label for
    any other unit, or none (`10$^{-3}$ Ω cm`, `10$^{3}$`). Not at all if the
    values are all 0, or sit far from 0 compared with their spread."""
    unscaled = Scale(0, _math_safe(unit) if unit else None)
    if not (math.isfinite(largest) and largest > 0) or spread < OFFSET_SPREAD * largest:
        return unscaled
    exponent = 3 * math.floor(math.log10(largest) / 3)
    if largest / 10.0**exponent >= 1000:  # log10 rounds down short of a power
        exponent += 3
    elif largest / 10.0**exponent < 1:
        exponent -= 3
    exponent = max(min(PREFIXES), min(max(PREFIXES), exponent))
    if exponent == 0:
        return unscaled
    if unit in BASE_UNITS:
        return Scale(exponent, f"{PREFIXES[exponent]}{unit}")
    power = f"10$^{{{exponent}}}$"
    return Scale(exponent, f"{power} {_math_safe(unit)}" if unit else power)


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
    scales: dict[str, Scale] | None = None,
) -> str:
    """The text of a script that draws the plot the request describes, in its
    style.

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
        scales: For the "aps" style, how each axis ("x" and "y") is scaled
            (see `axis_scale`). An axis left out isn't. The "screen" style
            ignores it.

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
    if request.style == "aps":
        return _aps_script(
            request,
            folder=folder,
            current_file=current_file,
            previous_file=previous_file if previous else None,
            delimiter=delimiter,
            units=units,
            current=current,
            previous=previous,
            scales=scales or {},
            now=now,
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
    out += [f"DELIMITER = {_literal(delimiter)}", "", "", *READ, "", "", "data = read(FILE)"]
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


# The script's reader of a data file, in both styles.
READ = [
    "def read(name):",
    '    """One data file, as a pandas DataFrame."""',
    "    for folder in (FOLDER, Path(__file__).resolve().parent):",
    "        if (folder / name).exists():",
    "            return pd.read_csv(folder / name, sep=DELIMITER)",
    '    raise FileNotFoundError(f"{name} is in neither {FOLDER} nor this script\'s folder")',
]


def _aps_script(
    request: PlotRequest,
    *,
    folder: str,
    current_file: str,
    previous_file: str | None,
    delimiter: str,
    units: dict[str, str | None],
    current: list[Series],
    previous: list[Series],
    scales: dict[str, Scale],
    now: datetime,
) -> str:
    """The script for an APS figure (see `plot_script`). `current` and
    `previous` are the series drawn from each file; `previous_file` is None
    if none are drawn from it."""
    names = [s.name for s in request.series]
    one_unit = len({units.get(n) or None for n in names}) == 1
    x_scale = scales.get("x") or axis_scale(0, 0, units.get(request.x))
    y_scale = scales.get("y") if one_unit else None
    y_scale = y_scale or axis_scale(0, 0, units.get(names[0]) if one_unit else None)

    def with_unit(name: str, unit: str | None) -> str:
        return f"{_math_safe(name)} ({unit})" if unit else _math_safe(name)

    if one_unit:
        y_label = with_unit(", ".join(names), y_scale.unit)
    else:
        y_label = ", ".join(with_unit(n, _math_safe(units.get(n) or "") or None) for n in names)

    def value(frame: str, column: str, constant: str, scale: Scale) -> str:
        scaled = f" * {constant}" if scale.exponent else ""
        return f"{frame}[{_literal(column)}]{scaled}"

    fmt = _literal(FORMATS[request.marks])

    def line(frame: str, series: Series) -> str:
        style = [f"color={_literal(series.colour.lower())}"]
        if frame == "previous":
            style.append(f"alpha={PREVIOUS_ALPHA}")
        else:
            label = _math_safe(series.name) if one_unit else with_unit(series.name, _math_safe(units.get(series.name) or "") or None)
            style.append(f"label={_literal(label)}")
        return (
            f"ax.plot({value(frame, request.x, 'X_SCALE', x_scale)}, "
            f"{value(frame, series.name, 'Y_SCALE', y_scale)}, {fmt}, {', '.join(style)})"
        )

    def limits(axis: str, pair: list[float], scale: Scale) -> str:
        low, high = (f"{float(v)!r}" for v in pair)
        if scale.exponent:
            low, high = f"{low} * {axis.upper()}_SCALE", f"{high} * {axis.upper()}_SCALE"
        return f"ax.set_{axis}lim({low}, {high})"

    summary = f"{', '.join(map(_plain, names))} against {_plain(request.x)}"
    docstring = (
        f"A figure exported from pyacquisition on {now:%Y-%m-%d} at {now:%H:%M}: {summary}.\n"
        "\n"
        "Drawn in the style of an APS journal (PRB, PRL): one column wide, square,\n"
        "serif fonts. Run it with Python to draw the figure and save it as a PDF beside\n"
        "this script, then change anything you like. It reads the data files named\n"
        "below, and needs pandas and matplotlib (`pip install pandas matplotlib`).\n"
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
    if previous_file:
        out.append(f"PREVIOUS_FILE = None  # {_literal(previous_file)} to draw it too, fainter")
    out += [
        f"DELIMITER = {_literal(delimiter)}",
        "",
        f"# The figure: one APS column wide ({APS_SIZE} in), square. 7.0 in is two columns.",
        f"WIDTH = {APS_SIZE}",
        f"HEIGHT = {APS_SIZE}",
        "",
    ]
    scaled = [(a, s) for a, s in (("x", x_scale), ("y", y_scale)) if s.exponent]
    if scaled:
        out.append("# The axes' labels, and the scales their values are multiplied by, for tidy numbers.")
    else:
        out.append("# The axes' labels.")
    for axis, scale in scaled:
        column = request.x if axis == "x" else names[0]
        unit = units.get(column)
        why = f"{unit} to {scale.unit}" if unit in BASE_UNITS else f"in units of 10^{scale.exponent}"
        out.append(f"{axis.upper()}_SCALE = 1e{-scale.exponent}  # {why}")
    out += [
        f"X_LABEL = {_literal(with_unit(request.x, x_scale.unit))}",
        f"Y_LABEL = {_literal(y_label)}",
        "",
        "plt.rcParams.update({",
        *(f"    {_literal(key)}: {_python(v)}," for key, v in APS_STYLE),
        "})",
        "",
        "",
        *READ,
        "",
        "",
        "data = read(FILE)",
    ]
    if previous_file:
        out.append("previous = read(PREVIOUS_FILE) if PREVIOUS_FILE else None")
    out += ["", "fig, ax = plt.subplots(figsize=(WIDTH, HEIGHT))", ""]
    if previous_file:
        out.append("# The previous file, fainter, behind the current one.")
        out.append("if previous is not None:")
        out += [f"    {line('previous', s)}" for s in previous]
        out.append("")
    out += [line("data", s) for s in current]
    out += ["", "ax.set_xlabel(X_LABEL)", "ax.set_ylabel(Y_LABEL)"]
    if request.log_x:
        out.append('ax.set_xscale("log")')
    if request.log_y:
        out.append('ax.set_yscale("log")')
    linear = [axis for axis, log in (("x", request.log_x), ("y", request.log_y)) if not log]
    if linear:
        which = "" if len(linear) == 2 else f'axis="{linear[0]}", '
        out.append(
            f"ax.locator_params({which}nbins=5)  # about 5 numbered ticks, so they don't crowd"
        )
    if request.x_limits is not None:
        out.append(
            limits("x", request.x_limits, x_scale)
            + "  # as the plot showed it; delete for all the data"
        )
    if request.y_limits is not None:
        out.append(limits("y", request.y_limits, y_scale))
    if len(current) > 1:
        out.append("ax.legend()")
    out += [
        "fig.tight_layout()",
        'fig.savefig(Path(__file__).with_suffix(".pdf"), bbox_inches="tight")',
        "plt.show()",
        "",
    ]
    return "\n".join(out)


def figure_scales(
    request: PlotRequest, values: dict[str, Sequence[float]], units: dict[str, str | None]
) -> dict[str, Scale]:
    """How each axis of an APS figure is scaled (see `axis_scale`): from its
    limits, if it is held, or else from `values`, each drawn column's values
    (NaN where there are none). The y axis isn't scaled if its series have
    different units, since one scale can't suit them all."""
    names = [s.name for s in request.series]

    def extent(limits: list[float] | None, columns: list[str]) -> tuple[float, float]:
        if limits is not None and len(limits) == 2 and all(map(math.isfinite, limits)):
            return max(abs(v) for v in limits), abs(limits[1] - limits[0])
        found = [np.asarray(values[c], dtype=float) for c in columns if c in values]
        finite = np.concatenate(found) if found else np.array([])
        finite = finite[np.isfinite(finite)]
        if not finite.size:
            return 0.0, 0.0
        return float(np.abs(finite).max()), float(finite.max() - finite.min())

    scales = {"x": axis_scale(*extent(request.x_limits, [request.x]), units.get(request.x))}
    if len({units.get(n) or None for n in names}) == 1:
        scales["y"] = axis_scale(*extent(request.y_limits, names), units.get(names[0]))
    return scales


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


def _math_safe(text: str) -> str:
    """Text for matplotlib to show as it is: a `$` would start maths."""
    return text.replace("$", r"\$")


def _python(value) -> str:
    """A setting's value as Python source."""
    return _literal(value) if isinstance(value, str) else repr(value)


def _plain(name: str) -> str:
    """A name, to be written in the docstring: on one line, a space for anything
    that doesn't print."""
    return "".join(c if c.isprintable() else " " for c in name)


def _docstring_text(text: str) -> str:
    """The text, to go between triple quotes: the column names in it are
    anyone's, so their backslashes and quotes are escaped."""
    return text.replace("\\", "\\\\").replace('"', '\\"')
