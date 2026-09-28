"""The page's trace reader (traces.js): the binary form read as the JSON form
says, and a trace followed from mid-run without gaps, against an experiment
with two traces on their clocks."""

import pytest

pytest.importorskip("playwright")

import requests

from pyacquisition.core.trace_source import Trace
from pyacquisition.instruments.software.trace_generator import TraceGenerator
from ui_helpers import Running, SmokeExperiment


class TraceRig(SmokeExperiment):
    def setup(self):
        super().setup()
        long = TraceGenerator("long", points=5000)
        short = TraceGenerator("short", points=300)
        self.add_instrument(long)
        self.add_instrument(short)
        self.add_trace(Trace("spectrum", long.get_spectrum, every=0.2, reduce=["peak_x"]))
        self.add_trace(Trace("other", short.get_spectrum, every=0.3))


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """This module's experiment, in place of the plain one."""
    running = Running(TraceRig, tmp_path_factory.mktemp("traces"))
    yield running.address
    running.stop()


def json_history(server, name="spectrum", **params):
    return requests.get(f"{server}/traces/{name}/history", params={"format": "json", **params},
                        timeout=10).json()["data"]


SUMMARY = """(trace) => ({
    seq: trace.seq, index: trace.index, data_file: trace.data_file, binned: trace.binned,
    length: trace.length, x: Array.from(trace.x),
    values: Object.fromEntries(Object.entries(trace.values).map(([channel, parts]) =>
        [channel, Object.fromEntries(Object.entries(parts).map(([part, array]) =>
            [part, Array.from(array, (v) => (Number.isNaN(v) ? null : v))]))])),
})"""


def same(page_trace, server_trace):
    """Whether the page read a trace as the JSON form gives it."""
    keys = ("seq", "index", "data_file", "binned", "length", "x", "values")
    return {k: page_trace[k] for k in keys} == {k: server_trace[k] for k in keys}


def test_the_binary_form_reads_as_the_json_form_says(page, server):
    requests.get(f"{server}/rack/pause/", timeout=5)  # the clocks wait while paused
    try:
        read = page.page.evaluate(
            f"""async () => {{
                const traces = await import('/ui/js/traces.js');
                const summary = {SUMMARY};
                const history = await traces.fetchHistory('spectrum');
                const full = await traces.fetchLatest('spectrum', {{ full: true }});
                const other = await traces.fetchLatest('other');
                return {{
                    history: history.traces.map(summary), seq: history.seq,
                    full: summary(full.traces[0]), other: summary(other.traces[0]),
                    types: [full.traces[0].x.constructor.name,
                            full.traces[0].values.amplitude.values.constructor.name,
                            history.traces[0].values.amplitude.mean.constructor.name],
                }};
            }}"""
        )
        history = json_history(server)
        full = requests.get(f"{server}/traces/spectrum/latest", timeout=10,
                            params={"format": "json", "full": "true"}).json()["data"]["traces"][0]
        other = json_history(server, "other")["traces"][-1]
    finally:
        requests.get(f"{server}/rack/resume/", timeout=5)

    assert read["seq"] == history["seq"] and len(read["history"]) == len(history["traces"]) > 0
    assert all(same(p, s) for p, s in zip(read["history"], history["traces"]))
    assert read["history"][0]["binned"] and read["history"][0]["length"] == 1024
    assert same(read["full"], full) and read["full"]["length"] == 5000
    assert same(read["other"], other) and not read["other"]["binned"]
    # At full resolution a channel is in its own precision: the generator's is float32.
    assert read["types"] == ["Float64Array", "Float32Array", "Float32Array"]


def test_a_trace_is_followed_from_mid_run_without_gaps(page, server):
    page.page.evaluate(
        """async () => {
            const { TraceStore, traceFeed } = await import('/ui/js/traces.js');
            window.traceStore = new TraceStore('spectrum');
            window.stopTraces = traceFeed(window.traceStore, {});
        }"""
    )
    page.page.wait_for_function("window.traceStore.traces.length >= 3", timeout=10_000)
    first = page.page.evaluate("window.traceStore.latest.seq")
    page.page.wait_for_function(
        f"window.traceStore.traces.filter((t) => t.seq > {first}).length >= 4", timeout=10_000
    )
    requests.get(f"{server}/scribe/next_file", params={"title": "later"}, timeout=5)
    page.page.wait_for_function(
        "window.traceStore.files[1].includes('later') "
        "&& window.traceStore.latest.data_file.includes('later')",
        timeout=10_000,
    )
    read = page.page.evaluate(
        f"""async () => {{
            window.stopTraces();
            await window.traceStore.fetching;
            return window.traceStore.traces.map({SUMMARY});
        }}"""
    )
    history = json_history(server)

    # Every trace the server kept up to the page's latest, once each, in order,
    # read as the server has it.
    kept = [t for t in history["traces"] if t["seq"] <= read[-1]["seq"]]
    assert [t["seq"] for t in read] == [t["seq"] for t in kept]
    assert all(same(p, s) for p, s in zip(read, kept))
    by_file = {}
    for trace in read:
        by_file.setdefault(trace["data_file"], []).append(trace["index"])
    for indices in by_file.values():
        assert indices == list(range(indices[0], indices[0] + len(indices)))
    assert by_file[read[-1]["data_file"]][0] == 0  # the new file counts from 0
