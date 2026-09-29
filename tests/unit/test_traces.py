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
                       "every_rows": None, "timeout": 60, "channels": ["amplitude"], "column": "spectrum_index",
                       "columns": [], "latest": None}]
    assert taken.status_code == 200 and taken.json()["data"]["index"] == 0
    assert taken.json()["data"]["seq"] == after[0]["latest"]["seq"] == experiment._trace_history.seq
    assert missing.status_code == 404 and "no trace called 'nothing'" in missing.json()["detail"]
    latest = after[0]["latest"]
    assert (latest["index"], latest["points"], latest["channels"], latest["x_unit"], latest["data_file"]) == (
        0, 512, ["amplitude"], "Hz", "00.00 start.data")
    assert {"name": "spectrum_index", "kind": "trace", "source": "spectrum", "unit": None} in columns


@pytest.mark.asyncio
async def test_the_trace_stream_and_the_latest_on_a_running_experiment(tmp_path):
    from aiohttp import ClientSession

    experiment = rig(tmp_path)
    port = experiment._api_server.port

    async def script(experiment):
        async with ClientSession() as session:
            async with session.ws_connect(f"ws://localhost:{port}/stream/traces") as ws:
                await experiment.traces["spectrum"].acquire()
                event = await asyncio.wait_for(ws.receive_json(), timeout=5)
                async with session.get(f"http://localhost:{port}/scribe/next_file?title=sweep"):
                    pass
                new_file = await asyncio.wait_for(ws.receive_json(), timeout=5)
            async with session.get(f"http://localhost:{port}/traces/spectrum/latest?format=json") as response:
                latest = (await response.json())["data"]
        return event, new_file, latest

    event, new_file, latest = await running(experiment, script)

    assert event == {"type": "trace", "seq": event["seq"], "name": "spectrum", "index": 0,
                     "time": experiment.traces["spectrum"].latest.time}
    assert new_file == {"type": "new_file", "seq": event["seq"] + 1, "file": "00.01 sweep.data"}
    (trace,) = latest["traces"]
    assert (trace["seq"], trace["points"], trace["binned"], trace["channels"]) == (event["seq"], 512, False, ["amplitude"])
    assert latest["seq"] == new_file["seq"]


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


# ------------------------------------------------------------ row mode
@pytest.mark.asyncio
async def test_with_every_row_each_row_has_its_trace_and_its_mean(tmp_path):
    experiment = rig(tmp_path, trace={"every_rows": 1, "reduce": {"mean": np.mean}})

    await running(experiment, lambda e: asyncio.sleep(1.0), settle=0)

    data = rows(tmp_path)
    assert len(data) >= 15
    assert data.spectrum_index.notna().all() and data.spectrum_mean.notna().all()
    assert data.spectrum_index.astype(int).tolist() == list(range(len(data)))
    traces = read_traces(tmp_path / "data" / "00.00 start.data")
    means = np.mean(traces.channels["amplitude"], axis=1)
    assert np.allclose(data.spectrum_mean.to_numpy(), means[: len(data)], rtol=1e-6)
    # A fast trace keeps the rows at their period.
    assert experiment._rack.loop_time < 0.08


@pytest.mark.asyncio
async def test_a_slow_trace_with_every_row_slows_the_rows_and_none_misses_it(tmp_path):
    experiment = rig(tmp_path, trace={"every_rows": 1}, generator={"sweep_time": 0.2})

    await running(experiment, lambda e: asyncio.sleep(1.5), settle=0.5)

    data = rows(tmp_path)
    assert data.spectrum_index.notna().all()
    gaps = np.diff(data.time.to_numpy())
    assert np.median(gaps) >= 0.19  # the rows wait for their traces
    assert experiment._rack.loop_time >= 0.19


@pytest.mark.asyncio
async def test_every_fourth_row(tmp_path):
    experiment = rig(tmp_path, trace={"every_rows": 4, "reduce": ["max"]})

    await running(experiment, lambda e: asyncio.sleep(1.0), settle=0)

    data = rows(tmp_path)
    linked = data.index[data.spectrum_index.notna()].tolist()
    assert linked == list(range(0, len(data), 4))
    assert data.spectrum_max.notna().tolist() == data.spectrum_index.notna().tolist()


@pytest.mark.asyncio
async def test_a_row_mode_trace_that_fails_leaves_its_row_empty_and_the_next_tries(tmp_path, errors):
    calls = {"n": 0}

    class Glitching(Rig):
        def setup(self):
            super().setup()
            trace = self.traces["spectrum"].trace
            real = trace.phases["fetch"]

            def fails_the_second():
                calls["n"] += 1
                if calls["n"] == 2:
                    raise RuntimeError("a glitch")
                return real()

            trace.phases["fetch"] = fails_the_second

    experiment = Glitching(root_path=str(tmp_path), data_path="data", api_server_port=free_port(),
                           measurement_period=0.05, gui=False)
    experiment.trace_options = {"every_rows": 4, "reduce": ["mean"]}

    await running(experiment, lambda e: asyncio.sleep(1.0), settle=0)

    data = rows(tmp_path)
    linked = data.index[data.spectrum_index.notna()].tolist()
    # Rows 0 and 4 due; 4 failed, so 5 tried again, then every fourth from there.
    assert linked[:2] == [0, 5] and data.spectrum_mean[4] != data.spectrum_mean[4]
    assert [e for e in errors if "a glitch" in e]


# ------------------------------------------------------------ reductions
class TwoChannels(SoftwareInstrument):
    @mark_trace(channels=["X", "Y"])
    def capture(self):
        return TraceData({"X": [1.0, 3.0, 2.0], "Y": [4.0, 4.0, 1.0]}, x=(0.0, 2.0), x_unit="s", unit="V")

    @mark_trace
    def undeclared(self):
        return self.capture()


def reduce_now(trace):
    source = trace_source.TraceSource(trace)
    return source._reduce(trace.method())


def test_the_built_in_reductions_of_one_channel():
    generator = TraceGenerator("generator", noise=0.0, centre=4.0, points=101, start=0.0, stop=10.0)
    trace = Trace("spectrum", generator.get_spectrum, reduce=list(trace_source.REDUCTIONS))

    values = reduce_now(trace)

    data = generator.get_spectrum()
    amplitude = data.channels["amplitude"].astype(float)
    assert trace.columns == ["spectrum_index"] + [f"spectrum_{r}" for r in trace_source.REDUCTIONS]
    assert values["spectrum_mean"] == pytest.approx(amplitude.mean(), rel=1e-6)
    assert values["spectrum_min"] == pytest.approx(amplitude.min())
    assert values["spectrum_max"] == pytest.approx(1.0)
    assert values["spectrum_sum"] == pytest.approx(amplitude.sum(), rel=1e-6)
    assert values["spectrum_std"] == pytest.approx(amplitude.std(), rel=1e-5)
    assert values["spectrum_peak_x"] == pytest.approx(4.0)
    assert values["spectrum_integral"] == pytest.approx(np.trapezoid(amplitude, data.axis()), rel=1e-6)


def test_reductions_of_several_channels_are_named_by_channel_with_their_units():
    probe = TwoChannels("probe")
    trace = Trace("capture", probe.capture, reduce=["max", "peak_x", "integral"])

    values = reduce_now(trace)

    assert trace.columns == [
        "capture_index", "capture_X_max", "capture_Y_max", "capture_X_peak_x",
        "capture_Y_peak_x", "capture_X_integral", "capture_Y_integral",
    ]
    assert values["capture_X_max"] == 3.0 and values["capture_Y_max"] == 4.0
    assert values["capture_X_peak_x"] == 1.0 and values["capture_Y_peak_x"] == 0.0
    assert values["capture_Y_integral"] == pytest.approx(np.trapezoid([4.0, 4.0, 1.0], [0.0, 1.0, 2.0]))
    assert trace.column_units("V", "s") == {
        "capture_X_max": "V", "capture_Y_max": "V", "capture_X_peak_x": "s", "capture_Y_peak_x": "s",
    }
    assert Trace("c", probe.capture, reduce=["max"], unit="mV", reduce_units={"max": "dB"}).column_units() == {
        "c_X_max": "dB", "c_Y_max": "dB"}


def test_a_function_reduces_each_channel_and_can_have_the_axis():
    probe = TwoChannels("probe")

    def centroid(values, x):
        return float(np.sum(values * x) / np.sum(values))

    trace = Trace("capture", probe.capture, reduce={"first": lambda values: values[0], "centroid": centroid})
    values = reduce_now(trace)

    assert values["capture_X_first"] == 1.0 and values["capture_Y_first"] == 4.0
    assert values["capture_X_centroid"] == pytest.approx((0 * 1 + 1 * 3 + 2 * 2) / 6)


def test_a_reduction_that_fails_is_empty_and_logged_once(errors):
    probe = TwoChannels("probe")
    trace = Trace("capture", probe.capture, reduce={"bad": lambda values: 1 / 0}, channels=["X"])
    source = trace_source.TraceSource(trace)

    first = source._reduce(probe.capture())
    second = source._reduce(probe.capture())

    assert math.isnan(first["capture_bad"]) and math.isnan(second["capture_bad"])
    assert len([e for e in errors if "Reduction 'bad' failed" in e]) == 1


def test_undeclared_channels_are_taken_as_one_and_the_first_is_reduced(monkeypatch):
    warnings = []
    monkeypatch.setattr(trace_source.logger, "warning", warnings.append)
    probe = TwoChannels("probe")
    trace = Trace("capture", probe.undeclared, reduce=["max"])

    values = reduce_now(trace)

    assert trace.columns == ["capture_index", "capture_max"]
    assert values["capture_max"] == 3.0  # X's
    assert len(warnings) == 1 and "none were declared" in warnings[0]


def test_an_unknown_reduction_and_both_modes_are_refused():
    generator = TraceGenerator("generator")

    with pytest.raises(ValueError, match="no reduction called 'median'"):
        Trace("s", generator.get_spectrum, reduce=["median"])
    with pytest.raises(ValueError, match="not both"):
        Trace("s", generator.get_spectrum, every=1, every_rows=1)
    with pytest.raises(ValueError, match="whole number from 1"):
        Trace("s", generator.get_spectrum, every_rows=0)


@pytest.mark.asyncio
async def test_an_occasional_traces_reduction_is_on_its_row_and_empty_on_the_others(tmp_path):
    experiment = rig(tmp_path, trace={"reduce": ["peak_x"]})

    async def script(experiment):
        await experiment.traces["spectrum"].acquire()
        await asyncio.sleep(0.3)

    await running(experiment, script)

    data = rows(tmp_path)
    assert data.spectrum_peak_x.notna().tolist() == data.spectrum_index.notna().tolist()
    assert data.spectrum_peak_x.dropna().iloc[0] == pytest.approx(5.0, abs=0.2)
    history = experiment._history.current.columns
    kept = [not math.isnan(v) for v in history["spectrum_peak_x"]]
    assert kept == [not math.isnan(v) for v in history["spectrum_index"]] and sum(kept) == 1
    peak = next(c for c in experiment._column_info() if c["name"] == "spectrum_peak_x")
    assert peak == {"name": "spectrum_peak_x", "kind": "trace", "source": "spectrum", "unit": "Hz"}


# ------------------------------------------------------------ TOML
def toml_rig(tmp_path, traces, monkeypatch):
    from pyacquisition.instruments import instrument_map

    # Not offered in configs until the feature is shown (milestone 7).
    monkeypatch.setitem(instrument_map, "TraceGenerator", TraceGenerator)
    config = tmp_path / "rig.toml"
    config.write_text(
        f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n'
        '[data]\npath = "data"\n[rack]\nperiod = 0.05\n'
        '[instruments]\nclock = {instrument = "Clock"}\ngenerator = {instrument = "TraceGenerator"}\n'
        '[measurements]\ntime = {instrument = "clock", method = "time"}\n'
        f"[traces]\n{traces}\n",
        encoding="utf-8",
    )
    return Experiment.from_config(str(config), gui=False, api_server_port=free_port())


@pytest.mark.asyncio
async def test_a_toml_trace_with_every_row_reduced_to_its_mean(tmp_path, monkeypatch):
    experiment = toml_rig(tmp_path, 'spectrum = {instrument = "generator", method = "get_spectrum", '
                                    'every_rows = 1, reduce = ["mean"], unit = "mV"}', monkeypatch)

    await running(experiment, lambda e: asyncio.sleep(0.6), settle=0)

    data = rows(tmp_path)
    assert list(data.columns) == ["time", "spectrum_index", "spectrum_mean"]
    assert data.spectrum_index.astype(int).tolist() == list(range(len(data)))
    traces = read_traces(tmp_path / "data" / "00.00 start.data")
    assert traces.unit == "mV"
    assert np.allclose(data.spectrum_mean, np.mean(traces.channels["amplitude"], axis=1)[: len(data)], rtol=1e-6)


def test_a_toml_trace_takes_the_methods_inputs_and_its_options(tmp_path, monkeypatch):
    experiment = toml_rig(tmp_path, 'spectrum = {instrument = "generator", method = "get_spectrum", '
                                    'every = 2, timeout = 5, channels = ["amplitude"]}', monkeypatch)

    trace = experiment.traces["spectrum"].trace
    assert (trace.every, trace.timeout, trace.channels, trace.source) == (
        2, 5, ["amplitude"], "generator.get_spectrum")


@pytest.mark.parametrize(
    "entry, message",
    [
        ('{instrument = "generator", method = "get_centre"}', "TraceGenerator has no trace 'get_centre'. Its traces are get_spectrum"),
        ('{instrument = "generator", method = "get_spectrum", args = {colour = "red"}}', "get_spectrum takes no `colour`"),
        ('{instrument = "nothing", method = "get_spectrum"}', "no instrument 'nothing'"),
        ('{instrument = "generator", method = "get_spectrum", reduce = ["median"]}', "no reduction 'median'"),
        ('{instrument = "generator", method = "get_spectrum", every = 1, every_rows = 1}', "not both"),
        ('{instrument = "generator", method = "get_spectrum", period = 1}', "'period', which a trace doesn't take"),
        ('{instrument = "generator"}', "needs `method`"),
        ('{instrument = "generator", method = "get_spectrum", every = 0}', "`every` must be"),
    ],
)
def test_a_bad_toml_trace_stops_it_naming_the_entry(tmp_path, monkeypatch, entry, message):
    with pytest.raises(Exception, match=message) as error:
        toml_rig(tmp_path, f"spectrum = {entry}", monkeypatch)
    assert "spectrum" in str(error.value)


# ------------------------------------------------------------ the task
@pytest.mark.asyncio
async def test_acquire_trace_between_setpoints_takes_one_per_step_with_its_row(tmp_path):
    from pyacquisition.core.task_manager.instrument_call import InstrumentCall
    from pyacquisition.tasks.traces import AcquireTrace
    from pyacquisition.tasks import WaitFor

    class SweepRig(Rig):
        def setup(self):
            super().setup()
            self.add_measurement(Measurement("centre", self.generator.get_centre))

    experiment = SweepRig(root_path=str(tmp_path), data_path="data", api_server_port=free_port(),
                          measurement_period=0.05, gui=False)
    experiment.generator_options = {"noise": 0.0}

    async def script(experiment):
        manager = experiment._task_managers["main"]
        for centre in (3.0, 6.0):
            manager.add_task(InstrumentCall(instrument="generator", method="set_centre", arguments={"centre": centre}))
            manager.add_task(WaitFor(seconds=1))  # the row sees the new setpoint
            manager.add_task(AcquireTrace(trace="spectrum"))
        await until(lambda: experiment._trace_scribe.written == 2, timeout=20)

    await running(experiment, script)

    traces = read_traces(tmp_path / "data" / "00.00 start.data")
    assert traces.info["row.centre"].tolist() == [3.0, 6.0]
    peaks = traces.x[np.argmax(traces.channels["amplitude"], axis=1)]
    assert peaks.tolist() == pytest.approx([3.0, 6.0], abs=0.05)


def test_acquire_trace_is_registered_only_with_traces_and_names_the_one(tmp_path):
    from fastapi.testclient import TestClient

    lone = rig(tmp_path / "one")
    lone.setup()
    lone._register_trace_tasks()
    paths = TestClient(lone._api_server.app).get("/openapi.json").json()["paths"]
    assert paths["/tasks/acquiretrace"]["get"].get("parameters", []) == []  # its one trace, filled in

    class TwoTraces(Rig):
        def setup(self):
            super().setup()
            self.add_trace(Trace("again", self.generator.get_spectrum))

    both = TwoTraces(root_path=str(tmp_path / "two"), gui=False)
    both.setup()
    both._register_trace_tasks()
    (name,) = TestClient(both._api_server.app).get("/openapi.json").json()["paths"]["/tasks/acquiretrace"]["get"]["parameters"]
    assert name["name"] == "trace"
    assert name["schema"]["enum"] == ["spectrum", "again"]

    none = Experiment(root_path=str(tmp_path / "none"), gui=False)
    none._register_trace_tasks()
    assert "/tasks/acquiretrace" not in TestClient(none._api_server.app).get("/openapi.json").json()["paths"]


def test_the_trace_options_reach_the_scribe_and_the_history(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False, trace_history_mb=1.5,
                            trace_file_mb=20, trace_pending_mb=8)

    assert experiment._trace_history.budget == 1.5e6
    assert (experiment._trace_scribe.file_mb, experiment._trace_scribe.pending_mb) == (20, 8)
    with pytest.raises(ValueError, match="positive number of megabytes"):
        Experiment(root_path=str(tmp_path), gui=False, trace_history_mb=0)
