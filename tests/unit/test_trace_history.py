"""The recent traces, thinned for the page (core/trace_history.py): binning, the
memory budget, the seq protocol, and the endpoints' two forms."""

import json
import math
import struct
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pyacquisition.core.consumer import Consumer
from pyacquisition.core.trace import TraceData
from pyacquisition.core.trace_file import TraceRecord
from pyacquisition.core.trace_history import BINS, TraceHistory, bin_starts


def record(values, name="spectrum", index=0, data_file="00.00 start.data", x=None, **channels):
    channels = {"amplitude": values, **channels}
    points = len(values)
    data = TraceData(channels, x=(0.0, 10.0) if x is None else x, x_name="frequency", x_unit="Hz", unit="V")
    return TraceRecord(name=name, index=index, data=data, data_file=data_file, time_start=1.0,
                       time=2.0 + index, rows_start=3, rows=4, row_start={"T": 1.5}, row={"T": 1.75},
                       columns={f"{name}_mean": float(np.mean(values)) if points else math.nan})


def client(history, names=("spectrum",)):
    app = FastAPI()
    history._register_endpoints(SimpleNamespace(app=app), lambda: dict.fromkeys(names))
    return TestClient(app)


def parse(buffer: bytes) -> dict:
    """The binary form, as the page reads it: each trace's arrays by part."""
    (length,) = struct.unpack_from("<I", buffer)
    assert (4 + length) % 8 == 0
    header = json.loads(buffer[4 : 4 + length])
    start = 4 + length
    for trace in header["traces"]:
        trace["x"], trace["values"] = None, {}
        for block in trace.pop("blocks"):
            assert block["offset"] % 8 == 0
            array = np.frombuffer(buffer, dtype="<" + block["dtype"], count=block["length"],
                                  offset=start + block["offset"])
            if block["part"] == "x":
                trace["x"] = array
            else:
                trace["values"].setdefault(block["channel"], {})[block["part"]] = array
    return header


# ------------------------------------------------------------ thinning
def test_a_long_trace_is_binned_with_its_spikes_and_means():
    rng = np.random.default_rng(1)
    values = rng.normal(size=1_000_000)
    values[123_457] = 100.0  # a spike of a single point
    history = TraceHistory()
    history.add(record(values))

    (trace,) = parse(client(history).get("/traces/spectrum/latest").content)["traces"]

    assert trace["binned"] and trace["points"] == 1_000_000 and trace["length"] == BINS
    parts = trace["values"]["amplitude"]
    assert {k: len(v) for k, v in parts.items()} == {"min": BINS, "max": BINS, "mean": BINS}
    starts = bin_starts(1_000_000, BINS)
    spike_bin = np.searchsorted(starts, 123_457, side="right") - 1
    assert parts["max"][spike_bin] == 100.0
    assert parts["max"].max() == 100.0 and np.sum(parts["max"] > 10) == 1
    bins = np.split(values, starts[1:])
    assert np.allclose(parts["mean"], [b.mean() for b in bins], rtol=1e-5, atol=1e-6)
    assert np.allclose(parts["min"], [b.min() for b in bins], rtol=1e-6)
    # Each bin's x is the mean of its points' axis values.
    axis = np.linspace(0, 10, 1_000_000)
    assert np.allclose(trace["x"], [b.mean() for b in np.split(axis, starts[1:])])
    assert {len(b) for b in bins} == {976, 977}


def test_a_short_trace_is_kept_whole():
    values = np.sin(np.arange(500))
    history = TraceHistory()
    history.add(record(values))

    (trace,) = parse(client(history).get("/traces/spectrum/latest").content)["traces"]

    assert not trace["binned"] and trace["length"] == trace["points"] == 500
    assert list(trace["values"]["amplitude"]) == ["values"]
    assert np.array_equal(trace["values"]["amplitude"]["values"], values.astype(np.float32))
    assert np.allclose(trace["x"], np.linspace(0, 10, 500))
    assert trace["axis"] == {"kind": "linear", "start": 0.0, "stop": 10.0}
    assert (trace["row_start"], trace["row"]) == ({"T": 1.5}, {"T": 1.75})
    assert trace["columns"] == {"spectrum_mean": pytest.approx(np.mean(values))}


def test_nan_is_left_out_of_a_bin_and_a_bin_of_nan_is_nan():
    values = np.arange(2048.0)
    values[0] = np.nan
    values[2:4] = np.nan  # the whole of bin 1
    history = TraceHistory()
    history.add(record(values))

    (trace,) = history.history("spectrum")
    parts = trace.values["amplitude"]
    assert (parts["min"][0], parts["max"][0], parts["mean"][0]) == (1.0, 1.0, 1.0)
    assert all(math.isnan(parts[p][1]) for p in ("min", "max", "mean"))


def test_an_explicit_axis_and_several_channels():
    x = np.geomspace(1, 1e6, 3000)
    history = TraceHistory()
    history.add(record(np.ones(3000), x=x, phase=np.zeros(3000)))

    (trace,) = parse(client(history).get("/traces/spectrum/latest").content)["traces"]

    assert trace["axis"] == {"kind": "explicit"} and trace["channels"] == ["amplitude", "phase"]
    assert trace["x"].dtype == np.float64
    assert np.allclose(trace["x"], [b.mean() for b in np.split(x, bin_starts(3000, BINS)[1:])])
    assert set(trace["values"]) == {"amplitude", "phase"}


def test_full_gives_every_point_in_its_own_precision():
    values = np.random.default_rng(2).normal(size=1_000_000)
    history = TraceHistory()
    history.add(record(values))
    api = client(history)

    (binary,) = parse(api.get("/traces/spectrum/latest", params={"full": "true"}).content)["traces"]
    (text,) = api.get("/traces/spectrum/latest", params={"full": "true", "format": "json"}).json()["data"]["traces"]

    assert not binary["binned"] and binary["length"] == 1_000_000
    assert np.array_equal(binary["values"]["amplitude"]["values"], values)
    assert np.array_equal(text["values"]["amplitude"]["values"], values)
    assert len(text["x"]) == 1_000_000


# ------------------------------------------------------------ the two forms
def test_json_matches_the_binary_form():
    values = np.random.default_rng(3).normal(size=5000)
    values[7] = np.nan
    history = TraceHistory()
    history.add(record(values, index=0))
    history.add(record(values[:300], index=1))
    api = client(history)

    for path in ("/traces/spectrum/latest", "/traces/spectrum/history"):
        binary = parse(api.get(path).content)
        text = api.get(path, params={"format": "json"}).json()["data"]
        assert binary["seq"] == text["seq"] == 2 and len(binary["traces"]) == len(text["traces"])
        for b, t in zip(binary["traces"], text["traces"]):
            assert {k: v for k, v in b.items() if k not in ("x", "values")} == {
                k: v for k, v in t.items() if k not in ("x", "values")
            }
            assert np.array_equal(b["x"], np.array(t["x"], dtype=float))
            for channel, parts in b["values"].items():
                for part, array in parts.items():
                    listed = np.array([np.nan if v is None else v for v in t["values"][channel][part]])
                    assert np.array_equal(array.astype(float), listed, equal_nan=True)


def test_a_trace_there_isnt_or_none_yet_is_404():
    api = client(TraceHistory())

    assert "no trace called 'other'" in api.get("/traces/other/latest").json()["detail"]
    assert "No spectrum trace has been taken yet" in api.get("/traces/spectrum/latest").json()["detail"]
    assert api.get("/traces/spectrum/history", params={"format": "json"}).json()["data"]["traces"] == []


# ------------------------------------------------------------ what is kept
def test_the_history_stays_within_its_budget_dropping_the_oldest():
    # The latest at full size (0.8 MB), and about 20 binned ones of 20 kB.
    history = TraceHistory(budget_mb=1.2)
    for index in range(60):
        history.add(record(np.ones(100_000), index=index))
        assert history.nbytes <= history.budget

    kept = [t.record.index for t in history.history("spectrum")]
    assert kept == list(range(60 - len(kept), 60)) and 15 < len(kept) < 25


def test_the_latest_is_kept_even_past_the_budget():
    history = TraceHistory(budget_mb=0.001)
    history.add(record(np.ones(100_000), index=0))
    history.add(record(np.ones(100_000), index=1))
    history.add(record(np.ones(100), name="other"))

    assert [t.record.index for t in history.history("spectrum")] == [1]
    assert history.latest("other") is not None


def test_a_new_file_drops_the_traces_of_files_before_the_one_before():
    history = TraceHistory()
    for file in ("a.data", "b.data", "c.data"):
        history.new_file(file)
        history.add(record(np.ones(10), data_file=file))
        history.add(record(np.ones(10), data_file=file))
    assert [t.record.data_file for t in history.history("spectrum")] == ["b.data"] * 2 + ["c.data"] * 2

    # Files with no traces of their own: the latest trace is kept anyway.
    history.new_file("d.data")
    history.new_file("e.data")
    assert [t.record.data_file for t in history.history("spectrum")] == ["c.data"]


# ------------------------------------------------------------ following it
def test_a_page_connecting_mid_run_follows_without_gaps():
    history = TraceHistory()
    history.new_file("00.00 start.data")  # as the scribe does at setup
    stream = Consumer(callbacks=[], async_callbacks=[])
    for index in range(3):
        history.add(record(np.ones(10), index=index))
    history.add(record(np.ones(10), name="other"))
    history.subscribe(stream)  # the page connects
    history.add(record(np.ones(10), index=3))  # held, until the snapshot
    api = client(history, names=("spectrum", "other"))

    snapshot = api.get("/traces/spectrum/history", params={"format": "json"}).json()["data"]
    history.add(record(np.ones(10), index=4))
    history.new_file("next.data")
    history.add(record(np.ones(10), name="other", index=1))
    history.add(record(np.ones(10), index=0, data_file="next.data"))

    # The page's side of it: drop what the snapshot has, check each follows on,
    # and fetch what's new of its own trace.
    held = [stream.queue.get_nowait() for _ in range(stream.queue.qsize())]
    seq, kept = snapshot["seq"], [(t["data_file"], t["index"]) for t in snapshot["traces"]]
    last = snapshot["traces"][-1]["seq"]
    for event in held:
        if event["seq"] <= seq:
            continue
        assert event["seq"] == seq + 1
        seq = event["seq"]
        if event["type"] == "trace" and event["name"] == "spectrum":
            new = api.get("/traces/spectrum/history", params={"format": "json", "after": last}).json()["data"]
            kept += [(t["data_file"], t["index"]) for t in new["traces"]]
            last = new["traces"][-1]["seq"] if new["traces"] else last  # none: fetched already

    assert kept == [("00.00 start.data", i) for i in range(5)] + [("next.data", 0)]
    assert seq == history.seq
