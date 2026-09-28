"""Traces from end to end on the server (traces milestone 2): a trace taken on
demand or on its own clock, written to the data file's `.h5`, and linked to the
first row after it by the `<name>_index` column."""

import asyncio
import math
import socket
import time

import numpy as np
import pandas as pd
import pytest
import requests

from pyacquisition import Experiment, Measurement, read_traces
from pyacquisition.core import trace_source
from pyacquisition.core.instrument import SoftwareInstrument, mark_trace
from pyacquisition.core.trace import TraceData
from pyacquisition.core.trace_file import trace_path
from pyacquisition.core.trace_source import Trace
from pyacquisition.instruments.software.trace_generator import TraceGenerator


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


class Rig(Experiment):
    """Rows of `time` (wall clock) and a count, and a TraceGenerator's spectrum."""

    trace_options: dict = {}
    generator_options: dict = {}

    def setup(self):
        self.generator = TraceGenerator("generator", **self.generator_options)
        self.add_instrument(self.generator)
        self.add_measurement(Measurement("time", lambda: time.time()))
        counter = iter(range(10**9))
        self.add_measurement(Measurement("count", lambda: next(counter)))
        self.add_trace(Trace("spectrum", self.generator.get_spectrum, **self.trace_options))


def rig(tmp_path, *, period=0.05, trace=None, generator=None):
    experiment = Rig(
        root_path=str(tmp_path), data_path="data", api_server_port=free_port(),
        measurement_period=period, gui=False,
    )
    experiment.trace_options = trace or {}
    experiment.generator_options = generator or {}
    return experiment


async def until(condition, timeout=10.0):
    end = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > end:
            raise AssertionError("it never happened")
        await asyncio.sleep(0.01)


async def running(experiment, script, settle=0.3):
    """Runs the experiment while `script(experiment)` does its part, then stops
    it, and gives what the script gave."""

    async def drive():
        try:
            await until(lambda: experiment._started)
            await asyncio.sleep(settle)  # some rows first
            return await script(experiment)
        finally:
            experiment._shutdown_event.set()

    _, result = await asyncio.wait_for(asyncio.gather(experiment._run(), drive()), timeout=60)
    return result


def rows(tmp_path, name="00.00 start.data"):
    return pd.read_csv(tmp_path / "data" / name, float_precision="round_trip")  # exactly


@pytest.fixture
def errors(monkeypatch):
    logged = []
    monkeypatch.setattr(trace_source.logger, "error", logged.append)
    return logged


# ------------------------------------------------------------ declaring one
def test_a_trace_needs_a_trace_method():
    generator = TraceGenerator("generator")

    with pytest.raises(TypeError, match="trace method"):
        Trace("spectrum", generator.get_centre)
    with pytest.raises(TypeError, match="trace method"):
        Trace("spectrum", TraceGenerator.get_spectrum)  # not bound to an instrument


def test_a_trace_refuses_an_input_no_phase_takes_and_bad_numbers():
    generator = TraceGenerator("generator")

    with pytest.raises(ValueError, match="'colour' isn't an input"):
        Trace("spectrum", generator.get_spectrum, colour="red")
    with pytest.raises(ValueError, match="`every` must be above 0"):
        Trace("spectrum", generator.get_spectrum, every=0)
    with pytest.raises(ValueError, match="`timeout` must be above 0"):
        Trace("spectrum", generator.get_spectrum, timeout=-1)


def test_mark_trace_records_the_phases_and_the_timeout():
    method = TraceGenerator.get_spectrum
    assert method._is_trace
    assert method._trace_phases == {"start": "start_sweep", "ready": "sweep_done", "stop": "stop_sweep"}
    assert method._trace_timeout == 60
    generator = TraceGenerator("generator")
    assert list(generator.traces) == ["get_spectrum"]
    assert "get_spectrum" not in generator.queries and "get_spectrum" not in generator.commands


def test_a_traces_inputs_go_to_the_phases_that_take_them():
    class Probe(SoftwareInstrument):
        def arm(self, channel: int):
            self.armed = channel

        @mark_trace(start="arm")
        def fetch(self, channel: int, points: int = 3):
            return TraceData({"v": np.full(points, channel, float)}, x=(0, 1))

    probe = Probe("probe")
    trace = Trace("v", probe.fetch, channel=2, points=5)

    assert trace._kwargs == {"start": {"channel": 2}, "fetch": {"channel": 2, "points": 5}}
    assert trace.timeout == trace_source.DEFAULT_TIMEOUT
    assert Trace("v", probe.fetch, timeout=5).timeout == 5


def test_add_trace_refuses_a_name_that_is_taken(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    generator = TraceGenerator("generator")
    experiment.add_measurement(Measurement("spectrum_index", lambda: time.time()))
    experiment.add_trace(Trace("other", generator.get_spectrum))

    with pytest.raises(ValueError, match="'spectrum_index' is taken"):
        experiment.add_trace(Trace("spectrum", generator.get_spectrum))
    with pytest.raises(ValueError, match="'other' is taken"):
        experiment.add_trace(Trace("other", generator.get_spectrum))
    assert [c["name"] for c in experiment._column_info() if c["kind"] == "trace"] == ["other_index"]


# ------------------------------------------------------------ the occasional spectrum
@pytest.mark.asyncio
async def test_spectra_on_demand_are_written_and_each_linked_to_its_row(tmp_path):
    experiment = rig(tmp_path)

    async def script(experiment):
        taken = []
        for _ in range(3):
            taken.append(await experiment.traces["spectrum"].acquire())
            await asyncio.sleep(0.3)
        return taken

    taken = await running(experiment, script)

    traces = read_traces(tmp_path / "data" / "00.00 start.data", "spectrum")
    assert traces.index.tolist() == [0, 1, 2]
    assert traces.channels["amplitude"].shape == (3, 512) and traces.x_unit == "Hz"
    data = rows(tmp_path)
    linked = data[data.spectrum_index.notna()]
    assert linked.spectrum_index.tolist() == [0, 1, 2]
    assert len(data) > 20 and data.spectrum_index.isna().sum() == len(data) - 3
    for record, (position, row) in zip(taken, linked.iterrows(), strict=True):
        # The first row after the trace: measured once it was fetched, and the
        # row before it not after. (Windows' clock ticks in ~16 ms steps, so
        # the times can be equal.)
        assert row.time >= record.time >= data.time[position - 1]
        assert position >= record.rows  # rows written by then all come before it
        # Its end snapshot is a row written before the linked one (found by its
        # count, which reads back exactly, where a long float may be a bit off).
        before = data[data["count"] == record.row["count"]]
        assert len(before) == 1 and before.index[0] < position


@pytest.mark.asyncio
async def test_a_data_file_without_traces_has_no_trace_file_and_a_new_one_counts_from_0(tmp_path):
    experiment = rig(tmp_path)

    async def script(experiment):
        experiment._scribe.next_file("second")
        await asyncio.sleep(0.3)
        await experiment.traces["spectrum"].acquire()
        await experiment.traces["spectrum"].acquire()
        await asyncio.sleep(0.3)

    await running(experiment, script)

    assert not trace_path(tmp_path / "data", "00.00 start.data").exists()
    assert read_traces(tmp_path / "data" / "00.01 second.data").index.tolist() == [0, 1]
    assert rows(tmp_path, "00.01 second.data").spectrum_index.dropna().tolist() == [0, 1]


@pytest.mark.asyncio
async def test_a_trace_on_a_clock_numbers_each_once_in_order(tmp_path):
    experiment = rig(tmp_path, trace={"every": 0.2})

    await running(experiment, lambda e: asyncio.sleep(2.0), settle=0)

    indices = rows(tmp_path).spectrum_index.dropna().astype(int).tolist()
    assert indices == list(range(len(indices)))
    assert 7 <= len(indices) <= 12  # about ten in 2 s
    assert read_traces(tmp_path / "data" / "00.00 start.data").index.tolist()[: len(indices)] == indices


@pytest.mark.asyncio
async def test_two_traces_between_rows_go_on_two_consecutive_rows(tmp_path):
    experiment = rig(tmp_path, period=0.5)

    async def script(experiment):
        await experiment.traces["spectrum"].acquire()
        await experiment.traces["spectrum"].acquire()  # both within one row's period
        await asyncio.sleep(1.5)

    await running(experiment, script, settle=0.6)

    data = rows(tmp_path)
    linked = data[data.spectrum_index.notna()]
    assert linked.spectrum_index.tolist() == [0, 1]
    assert linked.index[1] == linked.index[0] + 1


@pytest.mark.asyncio
async def test_pausing_stops_the_clock_and_a_trace_asked_for_waits_for_a_row(tmp_path):
    experiment = rig(tmp_path, trace={"every": 0.1})

    async def script(experiment):
        await asyncio.sleep(0.5)
        experiment._rack.pause()
        await asyncio.sleep(0.3)  # anything under way finishes
        before = experiment._trace_scribe.written + experiment._trace_scribe.pending
        await asyncio.sleep(0.6)
        during = experiment._trace_scribe.written + experiment._trace_scribe.pending
        record = await experiment.traces["spectrum"].acquire()  # while paused: taken
        rows_paused = experiment._scribe.rows_written
        experiment._rack.resume()
        await asyncio.sleep(0.6)
        return before, during, record, rows_paused

    before, during, record, rows_paused = await running(experiment, script)

    assert during == before  # no clock traces while paused
    data = rows(tmp_path)
    # Its number is on a row after resuming: the first, or the second if a
    # clock trace taken just before the pause was waiting for a row too.
    position = data.index[data.spectrum_index == record.index][0]
    assert rows_paused <= position <= rows_paused + 1
    assert data.spectrum_index[rows_paused:position].tolist() == list(range(record.index - (position - rows_paused), record.index))
    assert data.spectrum_index.dropna().astype(int).tolist()[-1] > record.index  # the clock again


@pytest.mark.asyncio
async def test_a_slow_sweep_leaves_the_rows_running_and_notes_both_ends(tmp_path):
    experiment = rig(tmp_path, generator={"sweep_time": 1.0})

    async def script(experiment):
        rows_before = experiment._scribe.rows_written
        started = time.monotonic()
        record = await experiment.traces["spectrum"].acquire()
        took = time.monotonic() - started
        return record, took, experiment._scribe.rows_written - rows_before

    record, took, rows_meanwhile = await running(experiment, script)

    assert took >= 1.0
    assert rows_meanwhile >= 12  # rows at 0.05 s went on throughout
    assert record.rows - record.rows_start >= 12
    assert record.time - record.time_start >= 1.0
    assert record.row["count"] > record.row_start["count"]  # the two snapshots differ
    info = read_traces(tmp_path / "data" / "00.00 start.data").info
    assert info.loc[0, "row.count"] > info.loc[0, "row_start.count"]


@pytest.mark.asyncio
async def test_cancelling_a_sweep_stops_it_once_and_writes_nothing(tmp_path):
    experiment = rig(tmp_path, generator={"sweep_time": 5.0})

    async def script(experiment):
        taking = asyncio.create_task(experiment.traces["spectrum"].acquire())
        await asyncio.sleep(0.3)
        taking.cancel()
        with pytest.raises(asyncio.CancelledError):
            await taking
        await asyncio.sleep(0.2)
        return experiment.generator.sweeps_stopped

    assert await running(experiment, script) == 1
    assert not trace_path(tmp_path / "data", "00.00 start.data").exists()
    assert rows(tmp_path).spectrum_index.isna().all()


@pytest.mark.asyncio
async def test_a_sweep_longer_than_its_timeout_is_stopped_once_and_logged(tmp_path, errors):
    experiment = rig(tmp_path, trace={"timeout": 0.3}, generator={"sweep_time": 5.0})

    async def script(experiment):
        record = await experiment.traces["spectrum"].acquire()
        return record, experiment.generator.sweeps_stopped

    record, stopped = await running(experiment, script)

    assert record is None and stopped == 1
    assert [e for e in errors if "longer than 0.3 s" in e]
    assert not trace_path(tmp_path / "data", "00.00 start.data").exists()


@pytest.mark.asyncio
async def test_a_trace_that_raises_logs_one_error_and_writes_nothing(tmp_path, errors):
    experiment = rig(tmp_path)

    async def script(experiment):
        def broken():
            raise RuntimeError("the instrument went away")

        experiment.generator.get_spectrum.__func__  # noqa: B018 - it is a bound method
        experiment.traces["spectrum"].trace.phases["fetch"] = broken
        return await experiment.traces["spectrum"].acquire()

    assert await running(experiment, script) is None
    assert [e for e in errors if "the instrument went away" in e] and len(
        [e for e in errors if "Trace spectrum" in e]
    ) == 1
    assert not trace_path(tmp_path / "data", "00.00 start.data").exists()


@pytest.mark.asyncio
async def test_a_trace_method_that_gives_no_trace_data_is_refused(tmp_path, errors):
    experiment = rig(tmp_path)

    async def script(experiment):
        experiment.traces["spectrum"].trace.phases["fetch"] = lambda: [1, 2, 3]
        return await experiment.traces["spectrum"].acquire()

    assert await running(experiment, script) is None
    assert [e for e in errors if "gave a list, not a TraceData" in e]


@pytest.mark.asyncio
async def test_two_asked_for_at_once_are_taken_one_after_the_other(tmp_path):
    experiment = rig(tmp_path, generator={"sweep_time": 0.3})

    async def script(experiment):
        source = experiment.traces["spectrum"]
        return await asyncio.gather(source.acquire(), source.acquire())

    first, second = await running(experiment, script)

    assert (first.index, second.index) == (0, 1)
    assert second.time_start >= first.time  # the second started after the first ended


# ------------------------------------------------------------ the endpoints
@pytest.mark.asyncio
async def test_the_trace_endpoints(tmp_path):
    experiment = rig(tmp_path)
    base = f"http://localhost:{experiment._api_server.port}"

    async def script(experiment):
        get = lambda path: asyncio.to_thread(requests.get, base + path, timeout=10)  # noqa: E731
        before = (await get("/traces")).json()["data"]
        taken = await get("/traces/spectrum/acquire")
        missing = await get("/traces/nothing/acquire")
        after = (await get("/traces")).json()["data"]
        columns = (await get("/experiment/columns")).json()["data"]
        return before, taken, missing, after, columns

    before, taken, missing, after, columns = await running(experiment, script)

    assert before == [{"name": "spectrum", "source": "generator.get_spectrum", "every": None,
                       "column": "spectrum_index", "latest": None}]
    assert taken.status_code == 200 and taken.json()["data"]["index"] == 0
    assert missing.status_code == 404 and "no trace called 'nothing'" in missing.json()["detail"]
    latest = after[0]["latest"]
    assert (latest["index"], latest["points"], latest["channels"], latest["x_unit"], latest["data_file"]) == (
        0, 512, ["amplitude"], "Hz", "00.00 start.data")
    assert {"name": "spectrum_index", "kind": "trace", "source": "spectrum", "unit": None} in columns


# ------------------------------------------------------------ the generator
def test_the_generator_gives_a_lorentzian_where_it_is_told():
    generator = TraceGenerator("generator", centre=3.0, width=0.2, noise=0.0, points=101, start=0, stop=10)

    data = generator.get_spectrum()

    assert data.x == (0.0, 10.0) and data.points == 101
    assert data.axis()[np.argmax(data.channels["amplitude"])] == pytest.approx(3.0)
    generator.set_centre(7.0)
    peak = generator.get_spectrum()
    assert peak.axis()[np.argmax(peak.channels["amplitude"])] == pytest.approx(7.0)
    assert math.isclose(peak.channels["amplitude"].max(), 1.0, rel_tol=1e-6)


def test_the_generators_sweep_takes_its_time_and_can_be_stopped():
    generator = TraceGenerator("generator", sweep_time=0.2)

    generator.start_sweep()
    assert not generator.sweep_done()
    time.sleep(0.25)
    assert generator.sweep_done()
    generator.stop_sweep()
    assert generator.sweeps_stopped == 1
    generator.stop_sweep()  # none under way: not counted
    assert generator.sweeps_stopped == 1
