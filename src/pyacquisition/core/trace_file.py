"""The trace file: each data file's traces, in an HDF5 file beside it.

`00.01 sweep.data` has its traces in `00.01 sweep.h5`, made with its first
trace, and in parts after that if it grows past a size (`00.01 sweep.001.h5`,
`.002.h5`, …). Each trace has a group, named after it, and its traces are rows
along a `trace` dimension:

    /                          attrs: pyacquisition_version, data_file, part, created
    /<trace>/                  attrs: name, x_name, x_unit, unit, channels, axis
        trace       (n,)       int64    the trace's number in its data file: the
                                        `<trace>_index` column of its row
        point       (m,)       int64    0 to m - 1
        time_start  (n,)       float64  when it started (Unix seconds, as `time`)
        time        (n,)       float64  when it was fetched
        rows_start  (n,)       int64    rows written to the data file by then
        rows        (n,)       int64
        points      (n,)       int64    each trace's length (NaN past it)
        x_start     (n,)       float64  a linear axis: its ends …
        x_stop      (n,)       float64
        x           (n, m)     float64  … or an explicit one: its values
        <channel>   (n, m)     float32 or float64
        row_start.<column> (n,) float64 the latest row's values when it started
        row.<column>       (n,) float64 … and when it was fetched

`trace` and `point` are HDF5 dimension scales, as NetCDF4 lays out its
dimensions, so `xarray.load_dataset(path, group="spectrum", engine="h5netcdf")`
gives `spectrum(trace, point)` with the rest beside it. A name with a `/` in it
has it replaced by `∕` in the file, and is kept as it was in the `name` or
`column` attribute.

Everything here is plain and synchronous. `TraceScribe` (trace_scribe.py) calls
it from a worker thread.
"""

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

from .trace import TraceData

SUFFIX = ".h5"
PER_TRACE = ("time_start", "time", "rows_start", "rows", "points")
CHUNK_TRACES = 256  # traces to a chunk of the one-dimensional datasets
MAX_CHUNK_POINTS = 1 << 20  # the most points to a chunk of a trace's row


@dataclass
class TraceRecord:
    """One trace, and where it belongs: what `TraceScribe` writes.

    Args:
        name: The trace's name.
        index: Its number in its data file's traces, from 0.
        data: The trace.
        data_file: The name of the data file it belongs to (`"00.01 sweep.data"`).
        time_start, time: When its acquisition started, and when it was fetched
            (Unix seconds).
        rows_start, rows: The rows the scribe had written to the data file then.
        row_start, row: The latest row's numeric values then, by column.
    """

    name: str
    index: int
    data: TraceData
    data_file: str
    time_start: float
    time: float
    rows_start: int = 0
    rows: int = 0
    row_start: dict = field(default_factory=dict)
    row: dict = field(default_factory=dict)

    @property
    def nbytes(self) -> int:
        return self.data.nbytes


def _h5name(name: str) -> str:
    """A name as the file can hold it: no `/`, and not `.` or `..`."""
    name = name.replace("/", "∕")
    return f"_{name}" if name in (".", "..") else name


def trace_path(folder, data_file: str, part: int = 0) -> Path:
    """Where a data file's traces go: `<stem>.h5`, or `<stem>.001.h5` and on."""
    stem = Path(data_file).stem
    return Path(folder) / (f"{stem}{SUFFIX}" if part == 0 else f"{stem}.{part:03d}{SUFFIX}")


def trace_parts(path) -> list[Path]:
    """A data file's trace files that exist, in order: from the data file's
    path, or any of its trace files'."""
    path = Path(path)
    stem = re.sub(r"\.\d{3}$", "", path.stem) if path.suffix == SUFFIX else path.stem
    first = path.parent / f"{stem}{SUFFIX}"
    numbered = re.compile(rf"{re.escape(stem)}\.(\d{{3}}){re.escape(SUFFIX)}")
    later = sorted(
        (int(match.group(1)), p)
        for p in (path.parent.iterdir() if path.parent.is_dir() else [])
        if (match := numbered.fullmatch(p.name))
    )
    return ([first] if first.exists() else []) + [p for _, p in later]


# ------------------------------------------------------------------ writing
class TraceFileBusy(OSError):
    """A trace file that can't be opened for writing: on Windows, another
    program (a notebook, HDFView) has it open."""


def append(path, records: list[TraceRecord], *, part: int = 0) -> None:
    """Appends traces to a trace file, making it if it isn't there: one open,
    and one close, for all of them.

    Raises:
        TraceFileBusy: If the file can't be opened, and so nothing was written.
    """
    try:
        handle = h5py.File(path, "a")
    except OSError as error:
        raise TraceFileBusy(str(error)) from error
    with handle as f:
        if "pyacquisition_version" not in f.attrs:
            from importlib.metadata import PackageNotFoundError, version

            try:
                f.attrs["pyacquisition_version"] = version("pyacquisition")
            except PackageNotFoundError:
                f.attrs["pyacquisition_version"] = "unknown"
            f.attrs["data_file"] = records[0].data_file if records else ""
            f.attrs["part"] = part
            f.attrs["created"] = datetime.datetime.now().isoformat(timespec="seconds")
        for record in records:
            _append_one(f, record)


def _series(g, name, dtype, fill=None):
    """A dataset of one value per trace, attached to the `trace` dimension."""
    n = g["trace"].shape[0]
    kwargs = {"fillvalue": fill} if fill is not None else {}
    ds = g.create_dataset(name, (n,), maxshape=(None,), dtype=dtype, chunks=(CHUNK_TRACES,), **kwargs)
    ds.dims[0].attach_scale(g["trace"])
    return ds


def _grid(g, name, dtype, units=None):
    """A dataset of a row per trace and a column per point, attached to both
    dimensions, NaN where nothing is written."""
    n, m = g["trace"].shape[0], g["point"].shape[0]
    ds = g.create_dataset(
        name,
        (n, m),
        maxshape=(None, None),
        dtype=dtype,
        chunks=(1, max(1, min(m, MAX_CHUNK_POINTS))),
        fillvalue=np.nan,
        compression="gzip",
        compression_opts=4,
        shuffle=True,
    )
    ds.dims[0].attach_scale(g["trace"])
    ds.dims[1].attach_scale(g["point"])
    if units:
        ds.attrs["units"] = units
    return ds


def _new_group(f, record: TraceRecord):
    data = record.data
    g = f.create_group(_h5name(record.name))
    g.attrs["name"] = record.name
    g.attrs["x_name"] = data.x_name
    g.attrs["x_unit"] = data.x_unit or ""
    g.attrs["unit"] = data.unit or ""
    g.attrs["channels"] = list(data.channels)
    g.attrs["axis"] = "linear" if data.linear else "explicit"
    trace = g.create_dataset("trace", (0,), maxshape=(None,), dtype="int64", chunks=(CHUNK_TRACES,))
    trace.make_scale("trace")
    point = g.create_dataset("point", data=np.arange(data.points, dtype="int64"), maxshape=(None,), chunks=True)
    point.make_scale("point")
    for name in PER_TRACE:
        _series(g, name, "int64" if name in ("rows_start", "rows", "points") else "float64")
    g["time"].attrs["units"] = "s"
    g["time_start"].attrs["units"] = "s"
    if data.linear:
        for name in ("x_start", "x_stop"):
            _series(g, name, "float64").attrs["units"] = data.x_unit or ""
    else:
        _grid(g, "x", "float64", data.x_unit)
    for name, values in data.channels.items():
        _grid(g, _h5name(name), values.dtype, data.unit).attrs["name"] = name
    return g


def _grids(g) -> list:
    return [ds for ds in g.values() if isinstance(ds, h5py.Dataset) and ds.ndim == 2]


def _to_explicit(g) -> None:
    """Turns a group's linear axis into an explicit one: every trace's axis
    written out in full."""
    x = _grid(g, "x", "float64", g["x_start"].attrs.get("units") or None)
    points = g["points"][:]
    for i, (start, stop) in enumerate(zip(g["x_start"][:], g["x_stop"][:], strict=True)):
        x[i, : points[i]] = np.linspace(start, stop, points[i])
    for name in ("x_start", "x_stop"):
        g[name].dims[0].detach_scale(g["trace"])
        del g[name]
    g.attrs["axis"] = "explicit"


def _append_one(f, record: TraceRecord) -> None:
    data = record.data
    key = _h5name(record.name)
    g = f[key] if key in f else _new_group(f, record)

    # Room for one more trace, and for its points.
    n = g["trace"].shape[0]
    m = g["point"].shape[0]
    if data.points > m:
        g["point"].resize((data.points,))
        g["point"][m:] = np.arange(m, data.points)
        for ds in _grids(g):
            ds.resize((ds.shape[0], data.points))
    for ds in g.values():
        if isinstance(ds, h5py.Dataset) and ds.name.split("/")[-1] != "point":
            ds.resize((n + 1, *ds.shape[1:]))

    # The axis: a group turns explicit with its first explicit trace.
    if not data.linear and g.attrs["axis"] == "linear":
        _to_explicit(g)
    if g.attrs["axis"] == "linear":
        g["x_start"][n], g["x_stop"][n] = data.x
    else:
        g["x"][n, : data.points] = data.axis()

    # The channels: one that is new here is NaN for the traces before it.
    channels = list(g.attrs["channels"])
    for name, values in data.channels.items():
        h5 = _h5name(name)
        if h5 not in g:
            _grid(g, h5, values.dtype, data.unit).attrs["name"] = name
            channels.append(name)
        g[h5][n, : data.points] = values
    g.attrs["channels"] = channels

    g["trace"][n] = record.index
    g["time_start"][n] = record.time_start
    g["time"][n] = record.time
    g["rows_start"][n] = record.rows_start
    g["rows"][n] = record.rows
    g["points"][n] = data.points

    # The rows' values: a column that is new here is NaN for the traces before.
    for prefix, row in (("row_start.", record.row_start), ("row.", record.row)):
        for column, value in row.items():
            h5 = prefix + _h5name(column)
            if h5 not in g:  # made as long as the others: NaN before this trace
                _series(g, h5, "float64", np.nan).attrs["column"] = column
            try:
                g[h5][n] = float(value)
            except (TypeError, ValueError):
                pass  # not a number: left NaN


# ------------------------------------------------------------------ reading
@dataclass
class Traces:
    """A data file's traces of one name, as `read_traces` gives them.

    Attributes:
        name: The trace's name.
        index: Each trace's number (its `<name>_index` in the data file).
        x: The axis: one dimensional when every trace has the same one, or a
            row per trace (NaN past each trace's length).
        channels: Each channel, a row per trace (NaN past its length).
        info: A row per trace, indexed by its number: `time_start`, `time`,
            `rows_start`, `rows`, `points`, and the rows' values when it started
            and ended, as `row_start.<column>` and `row.<column>`.
        x_name, x_unit, unit: What the axis is, its unit, and the channels'.
    """

    name: str
    index: np.ndarray
    x: np.ndarray
    channels: dict
    info: pd.DataFrame
    x_name: str = "x"
    x_unit: str | None = None
    unit: str | None = None


def _find_group(f, name):
    groups = {g.attrs.get("name", key): g for key, g in f.items() if isinstance(g, h5py.Group)}
    if name is None:
        if len(groups) != 1:
            raise ValueError(f"Say which trace: this file has {', '.join(map(repr, groups))}.")
        return next(iter(groups.values()))
    if name not in groups:
        raise KeyError(f"There is no trace called {name!r}: there is {', '.join(map(repr, groups)) or 'none'}.")
    return groups[name]


def _pad(arrays: list, width: int) -> np.ndarray:
    rows = [np.pad(a, ((0, 0), (0, width - a.shape[1])), constant_values=np.nan) for a in arrays]
    return np.concatenate(rows) if rows else np.empty((0, width))


def read_traces(path, name: str | None = None) -> Traces:
    """Reads a data file's traces of one name, from its trace file and all its
    parts, in order.

    Args:
        path: The data file (`"my_data/00.01 sweep.data"`), or its trace file.
        name: The trace's name. It can be left out when the file has only one.

    Returns:
        Traces: The axis, the channels and the rest, a row per trace.

    Raises:
        FileNotFoundError: If the data file has no traces.
        KeyError: If there is no trace of that name.

    Example:
        traces = read_traces("my_data/00.01 sweep.data", "spectrum")
        plt.pcolormesh(traces.x, traces.info["row.T"], traces.channels["S21"])
    """
    parts = trace_parts(path)
    if not parts:
        raise FileNotFoundError(f"{path} has no trace file beside it.")
    pieces = []
    meta = None
    for part in parts:
        with h5py.File(part, "r") as f:
            try:
                g = _find_group(f, name)
            except KeyError:
                continue  # not in this part
            name = g.attrs.get("name", name)
            if meta is None:
                meta = {
                    "x_name": g.attrs.get("x_name", "x"),
                    "x_unit": g.attrs.get("x_unit") or None,
                    "unit": g.attrs.get("unit") or None,
                }
            channels = {c: g[_h5name(c)][:] for c in g.attrs["channels"]}
            info = {key: g[key][:] for key in PER_TRACE}
            for key, ds in g.items():
                if key.startswith(("row_start.", "row.")):
                    prefix = key.split(".", 1)[0]
                    info[f"{prefix}.{ds.attrs.get('column', key.split('.', 1)[1])}"] = ds[:]
            if g.attrs["axis"] == "linear":
                axis = ("linear", g["x_start"][:], g["x_stop"][:])
            else:
                axis = ("explicit", g["x"][:])
            pieces.append((g["trace"][:], channels, info, axis))
    if not pieces:
        raise KeyError(f"There is no trace called {name!r} in {parts[0]}.")

    index = np.concatenate([p[0] for p in pieces])
    info = pd.concat([pd.DataFrame(p[2]) for p in pieces], ignore_index=True)
    info.index = pd.Index(index, name="trace")
    width = max(max((c.shape[1] for c in p[1].values()), default=0) for p in pieces)
    names = list(dict.fromkeys(n for p in pieces for n in p[1]))
    channels = {
        n: _pad([p[1].get(n, np.full((len(p[0]), 1), np.nan)) for p in pieces], width) for n in names
    }

    points = info["points"].to_numpy()
    if all(p[3][0] == "linear" for p in pieces):
        starts = np.concatenate([p[3][1] for p in pieces])
        stops = np.concatenate([p[3][2] for p in pieces])
        if len(set(zip(starts, stops, points, strict=True))) == 1:
            x = np.linspace(starts[0], stops[0], points[0])
        else:
            x = np.full((len(index), width), np.nan)
            for i, (a, b, k) in enumerate(zip(starts, stops, points, strict=True)):
                x[i, :k] = np.linspace(a, b, k)
    else:
        rows = []
        for p in pieces:
            if p[3][0] == "explicit":
                rows.append(p[3][1])
            else:
                block = np.full((len(p[0]), width), np.nan)
                k = p[2]["points"]
                for i, (a, b) in enumerate(zip(p[3][1], p[3][2], strict=True)):
                    block[i, : k[i]] = np.linspace(a, b, k[i])
                rows.append(block)
        x = _pad(rows, width)
    return Traces(name=name, index=index, x=x, channels=channels, info=info, **meta)
