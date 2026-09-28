"""The trace file (core/trace_file.py) and its writer (core/trace_scribe.py):
the layout, the axes and channels, parts, a file another program holds, and
reading it all back with `read_traces` and with xarray."""

import asyncio
import subprocess
import sys
import time

import h5py
import numpy as np
import pytest

from pyacquisition import read_traces
from pyacquisition.core import trace_scribe
from pyacquisition.core.trace import TraceData
from pyacquisition.core.trace_file import TraceFileBusy, TraceRecord, append, trace_parts, trace_path
from pyacquisition.core.trace_scribe import TraceScribe

DATA = "00.01 sweep.data"


def record(index, data=None, *, name="spectrum", data_file=DATA, row=None, row_start=None):
    data = data or TraceData({"S21": np.arange(4, dtype=np.float32) + index}, x=(1.0, 4.0),
                             x_name="frequency", x_unit="Hz", unit="dB")
    return TraceRecord(
        name=name, index=index, data=data, data_file=data_file,
        time_start=100.0 + index, time=100.5 + index,
        rows_start=10 * index, rows=10 * index + 2,
        row_start=row_start if row_start is not None else {"T": 4.0 + index},
        row=row if row is not None else {"T": 4.1 + index},
    )


# ------------------------------------------------------------ TraceData
def test_trace_data_keeps_float32_and_makes_the_rest_float64():
    data = TraceData({"a": np.zeros(3, np.float32), "b": [1, 2, 3]}, x=(0, 1))

    assert data.channels["a"].dtype == np.float32
    assert data.channels["b"].dtype == np.float64
    assert data.points == 3 and data.linear
    assert list(data.axis()) == [0.0, 0.5, 1.0]


@pytest.mark.parametrize(
    "channels, x, message",
    [
        ({}, (0, 1), "at least one channel"),
        ({"a": [[1, 2]]}, (0, 1), "one dimensional"),
        ({"a": [1, 2], "b": [1, 2, 3]}, (0, 1), "as long as each other"),
        ({"a": ["x", "y"]}, (0, 1), "real numbers"),
        ({"a": [1, 2]}, [1, 2, 3], "a value for each of the 2 points"),
        ({"a": [1, 2]}, (0, 1, 2), r"\(start, stop\)"),
        ({"time": [1, 2]}, (0, 1), "the trace file uses that name"),
        ({"row.T": [1, 2]}, (0, 1), "the trace file uses that name"),
        ({"a": []}, (0, 1), "at least one point"),
    ],
)
def test_trace_data_refuses_what_wont_do(channels, x, message):
    with pytest.raises(ValueError, match=message):
        TraceData(channels, x=x)


# ------------------------------------------------------------ the layout
def test_the_layout_and_its_attributes(tmp_path):
    path = trace_path(tmp_path, DATA)
    append(path, [record(0), record(1)])

    assert path.name == "00.01 sweep.h5"
    with h5py.File(path, "r") as f:
        assert f.attrs["data_file"] == DATA and f.attrs["part"] == 0
        assert "pyacquisition_version" in f.attrs and "created" in f.attrs
        g = f["spectrum"]
        assert dict(g.attrs) | {"channels": list(g.attrs["channels"])} == {
            "name": "spectrum", "x_name": "frequency", "x_unit": "Hz", "unit": "dB",
            "channels": ["S21"], "axis": "linear",
        }
        assert list(g["trace"][:]) == [0, 1] and list(g["point"][:]) == [0, 1, 2, 3]
        assert list(g["time_start"][:]) == [100.0, 101.0] and list(g["time"][:]) == [100.5, 101.5]
        assert list(g["rows_start"][:]) == [0, 10] and list(g["rows"][:]) == [2, 12]
        assert list(g["x_start"][:]) == [1.0, 1.0] and list(g["x_stop"][:]) == [4.0, 4.0]
        assert g["S21"].dtype == np.float32 and g["S21"].shape == (2, 4)
        assert g["S21"].attrs["units"] == "dB"
        assert list(g["row_start.T"][:]) == [4.0, 5.0] and list(g["row.T"][:]) == [4.1, 5.1]
        # Named dimensions, as NetCDF4 has them.
        assert g["S21"].dims[0][0] == g["trace"] and g["S21"].dims[1][0] == g["point"]
        assert g["row.T"].dims[0][0] == g["trace"]


def test_xarray_reads_it_with_named_dimensions(tmp_path):
    xarray = pytest.importorskip("xarray")
    pytest.importorskip("h5netcdf")
    path = trace_path(tmp_path, DATA)
    append(path, [record(i) for i in range(3)])

    ds = xarray.load_dataset(path, group="spectrum", engine="h5netcdf")

    assert ds["S21"].dims == ("trace", "point")
    assert list(ds["trace"].values) == [0, 1, 2]
    assert list(ds["row.T"].values) == [4.1, 5.1, 6.1]
    assert ds["S21"].attrs["units"] == "dB" and ds.attrs["x_unit"] == "Hz"
    assert np.array_equal(ds["S21"].values[2], [2, 3, 4, 5])


# ------------------------------------------------------------ axes and channels
def test_an_explicit_axis_is_kept_whole(tmp_path):
    path = trace_path(tmp_path, DATA)
    data = TraceData({"S21": [1.0, 2.0, 3.0]}, x=[1.0, 2.0, 5.0])
    append(path, [record(0, data), record(1, data)])

    traces = read_traces(tmp_path / DATA)

    assert traces.x.shape == (2, 3)
    assert list(traces.x[1]) == [1.0, 2.0, 5.0]


def test_an_explicit_trace_turns_a_linear_group_explicit(tmp_path):
    path = trace_path(tmp_path, DATA)
    append(path, [record(0)])  # linear, 1 to 4 Hz over 4 points
    append(path, [record(1, TraceData({"S21": [9.0, 9.0]}, x=[10.0, 20.0]))])

    with h5py.File(path, "r") as f:
        g = f["spectrum"]
        assert g.attrs["axis"] == "explicit"
        assert "x_start" not in g and "x_stop" not in g
    traces = read_traces(path)
    assert np.array_equal(traces.x[0], [1.0, 2.0, 3.0, 4.0])
    assert list(traces.x[1][:2]) == [10.0, 20.0] and np.isnan(traces.x[1][2:]).all()


def test_a_linear_axis_that_changes_is_given_a_row_per_trace(tmp_path):
    path = trace_path(tmp_path, DATA)
    append(path, [record(0), record(1, TraceData({"S21": [1.0, 2.0, 3.0, 4.0]}, x=(2.0, 8.0)))])

    traces = read_traces(path)

    assert traces.x.shape == (2, 4)
    assert list(traces.x[1]) == [2.0, 4.0, 6.0, 8.0]


def test_several_channels_of_float32_and_float64(tmp_path):
    path = trace_path(tmp_path, DATA)
    data = TraceData({"X": np.ones(3, np.float32), "Y": np.full(3, 2.0)}, x=(0, 2))
    append(path, [record(0, data)])

    with h5py.File(path, "r") as f:
        assert (f["spectrum/X"].dtype, f["spectrum/Y"].dtype) == (np.float32, np.float64)
        assert list(f["spectrum"].attrs["channels"]) == ["X", "Y"]
    traces = read_traces(path)
    assert set(traces.channels) == {"X", "Y"}


def test_a_longer_trace_widens_the_rest_with_nan(tmp_path):
    path = trace_path(tmp_path, DATA)
    append(path, [record(0)])  # 4 points
    append(path, [record(1, TraceData({"S21": np.arange(6.0)}, x=(1.0, 6.0)))])

    traces = read_traces(path)

    assert traces.channels["S21"].shape == (2, 6)
    assert np.isnan(traces.channels["S21"][0, 4:]).all()
    assert list(traces.info["points"]) == [4, 6]
    with h5py.File(path, "r") as f:
        assert list(f["spectrum/point"][:]) == [0, 1, 2, 3, 4, 5]


def test_a_column_that_appears_later_is_nan_before_it(tmp_path):
    path = trace_path(tmp_path, DATA)
    append(path, [record(0)])
    append(path, [record(1, row={"T": 5.0, "B": 0.5}, row_start={"T": 4.9, "B": 0.4})])

    info = read_traces(path).info

    assert np.isnan(info.loc[0, "row.B"]) and info.loc[1, "row.B"] == 0.5
    assert np.isnan(info.loc[0, "row_start.B"]) and info.loc[1, "row_start.B"] == 0.4


def test_a_value_that_isnt_a_number_is_left_nan(tmp_path):
    path = trace_path(tmp_path, DATA)
    append(path, [record(0, row={"T": 4.0, "label": "ok"})])

    assert np.isnan(read_traces(path).info.loc[0, "row.label"])


def test_names_with_other_characters(tmp_path):
    path = trace_path(tmp_path, "00.00 température.data")
    data = TraceData({"Ω/cm": [1.0, 2.0]}, x=(0, 1), unit="µV")
    append(path, [record(0, data, name="spectre/é", data_file="00.00 température.data",
                         row={"température (K)": 4.2, "a/b": 1.0})])

    traces = read_traces(tmp_path / "00.00 température.data", "spectre/é")

    assert traces.name == "spectre/é" and traces.unit == "µV"
    assert list(traces.channels) == ["Ω/cm"]
    assert traces.info.loc[0, "row.température (K)"] == 4.2 and traces.info.loc[0, "row.a/b"] == 1.0


def test_several_traces_in_one_file_are_read_by_name(tmp_path):
    path = trace_path(tmp_path, DATA)
    append(path, [record(0), record(0, name="capture")])

    with pytest.raises(ValueError, match="Say which trace"):
        read_traces(path)
    with pytest.raises(KeyError, match="no trace called 'other'"):
        read_traces(path, "other")
    assert read_traces(path, "capture").name == "capture"


def test_a_data_file_with_no_traces_has_nothing_to_read(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_traces(tmp_path / DATA)


# ------------------------------------------------------------ the writer
def write(scribe, records):
    """Runs a scribe until what it is given is written."""

    async def main():
        worker = asyncio.create_task(scribe.run())
        for r in records:
            scribe.add(r)
        await scribe.flush(timeout=20)
        scribe.shutdown()
        await worker

    asyncio.run(main())


def test_the_writer_keeps_the_order_and_writes_each_to_its_data_files_file(tmp_path):
    scribe = TraceScribe(tmp_path)
    records = [record(i) for i in range(20)]
    records[10:10] = [record(0, data_file="00.02 next.data")]

    write(scribe, records)

    assert list(read_traces(tmp_path / DATA).index) == list(range(20))
    assert list(read_traces(tmp_path / "00.02 next.data").index) == [0]
    assert scribe.written == 21


def test_a_data_file_rolls_over_into_parts_that_are_read_as_one(tmp_path):
    big = [record(i, TraceData({"S21": np.random.rand(4000)}, x=(0, 1))) for i in range(12)]

    for r in big:  # one at a time, so each write sees the size so far
        write(TraceScribe(tmp_path, file_mb=0.05), [r])  # 50 kB

    parts = trace_parts(tmp_path / DATA)
    assert [p.name for p in parts][:2] == ["00.01 sweep.h5", "00.01 sweep.001.h5"]
    assert len(parts) >= 3
    with h5py.File(parts[1], "r") as f:
        assert f.attrs["part"] == 1
    traces = read_traces(tmp_path / DATA)
    assert list(traces.index) == list(range(12))
    assert np.array_equal(traces.channels["S21"][7], big[7].data.channels["S21"])
    assert read_traces(parts[1]).index.tolist() == list(range(12))  # from any part


class Logged:
    def __init__(self, monkeypatch):
        self.warnings, self.errors, self.infos = [], [], []
        monkeypatch.setattr(trace_scribe.logger, "warning", self.warnings.append)
        monkeypatch.setattr(trace_scribe.logger, "error", self.errors.append)
        monkeypatch.setattr(trace_scribe.logger, "info", self.infos.append)


def test_a_file_another_program_holds_waits_and_is_written_after(tmp_path, monkeypatch):
    logged = Logged(monkeypatch)
    path = trace_path(tmp_path, DATA)
    append(path, [record(0)])
    holder = subprocess.Popen(
        [sys.executable, "-c",
         "import h5py, sys, time\n"
         f"f = h5py.File(r'{path}', 'r')\nprint('holding', flush=True)\nsys.stdin.readline()\nf.close()"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    assert holder.stdout.readline().strip() == "holding"
    scribe = TraceScribe(tmp_path, retry_every=0.2)

    async def main():
        worker = asyncio.create_task(scribe.run())
        for i in range(1, 4):
            scribe.add(record(i))
        await asyncio.sleep(1.0)
        held = scribe.pending
        holder.stdin.write("\n")
        holder.stdin.flush()
        holder.wait(timeout=10)
        await scribe.flush(timeout=10)
        scribe.shutdown()
        await worker
        return held

    try:
        held = asyncio.run(main())
    finally:
        holder.kill()

    if sys.platform == "win32":  # Windows' HDF5 refuses a writer while a reader holds the file
        assert held == 3
        assert len(logged.warnings) == 1 and "another program has it open" in logged.warnings[0]
        assert any("written again" in m for m in logged.infos)
    assert list(read_traces(path).index) == [0, 1, 2, 3]


def test_the_oldest_waiting_traces_are_dropped_past_the_limit(tmp_path, monkeypatch):
    logged = Logged(monkeypatch)
    busy = {"on": True}
    real = trace_scribe.append

    def append_unless_busy(*args, **kwargs):
        if busy["on"]:
            raise TraceFileBusy("held")
        return real(*args, **kwargs)

    monkeypatch.setattr(trace_scribe, "append", append_unless_busy)
    scribe = TraceScribe(tmp_path, pending_mb=0.1, retry_every=0.05)  # 100 kB
    big = [record(i, TraceData({"S21": np.zeros(5000)}, x=(0, 1))) for i in range(5)]  # 40 kB each

    async def main():
        worker = asyncio.create_task(scribe.run())
        for r in big:
            scribe.add(r)
            await asyncio.sleep(0.02)
        busy["on"] = False
        await scribe.flush(timeout=10)
        scribe.shutdown()
        await worker

    asyncio.run(main())

    assert any("dropped" in m for m in logged.errors)
    assert list(read_traces(tmp_path / DATA).index) == [3, 4]  # the newest kept
    assert len(logged.warnings) == 1


def test_a_trace_that_cant_be_written_for_another_reason_is_dropped_and_logged(tmp_path, monkeypatch):
    logged = Logged(monkeypatch)
    real = trace_scribe.append
    calls = {"n": 0}

    def fail_once(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("the disk is full")
        return real(*args, **kwargs)

    monkeypatch.setattr(trace_scribe, "append", fail_once)

    write(TraceScribe(tmp_path), [record(0)])
    write(TraceScribe(tmp_path), [record(1)])

    assert any("the disk is full" in m for m in logged.errors)
    assert list(read_traces(tmp_path / DATA).index) == [1]


def test_the_writer_doesnt_hold_up_the_event_loop(tmp_path):
    scribe = TraceScribe(tmp_path)
    big = [record(i, TraceData({"S21": np.random.rand(2_000_000)}, x=(0, 1))) for i in range(3)]
    ticks = []

    async def main():
        worker = asyncio.create_task(scribe.run())
        for r in big:
            scribe.add(r)
        start = time.perf_counter()
        while scribe.pending:
            ticks.append(time.perf_counter() - start)
            await asyncio.sleep(0.01)
        scribe.shutdown()
        await worker

    asyncio.run(main())

    gaps = np.diff(ticks)
    assert len(ticks) > 5 and gaps.max() < 0.2  # the loop ran on while it wrote
