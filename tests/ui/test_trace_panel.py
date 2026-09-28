"""The trace panel (plot/trace-panel.js), the **+ Add plot** menu, and a sparse
column (an occasional trace's reduction) drawn as dots and kept in the Values
tab (traces milestone 5)."""

import re
import statistics

import pytest

pytest.importorskip("playwright")

import requests
from playwright.sync_api import expect

from pyacquisition.core.trace_source import Trace
from pyacquisition.instruments.software.trace_generator import TraceGenerator
from ui_helpers import Page, Running, SmokeExperiment


class TraceRig(SmokeExperiment):
    """A spectrum of 2048 points (binned) on a clock, a short one taken only
    when asked (reduced to its mean), and a slow one of a 6 s sweep."""

    def setup(self):
        super().setup()
        analyser = TraceGenerator("analyser", points=2048)
        scope = TraceGenerator("scope", points=300, centre=3)
        slow = TraceGenerator("slow", points=100, sweep_time=6)
        for instrument in (analyser, scope, slow):
            self.add_instrument(instrument)
        self.add_trace(Trace("spectrum", analyser.get_spectrum, every=0.15))
        self.add_trace(Trace("short", scope.get_spectrum, reduce=["mean"]))
        self.add_trace(Trace("slow", slow.get_spectrum, timeout=30))


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    running = Running(TraceRig, tmp_path_factory.mktemp("trace-panel"), measurement_period=0.1)
    yield running
    running.stop()


@pytest.fixture
def trace_page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    yield page.page
    assert page.errors == [], f"the page logged errors: {page.errors}"


def add_trace_panel(page, name):
    page.get_by_role("button", name="Add plot").click()
    page.get_by_role("menuitem", name=f"Trace: {name}").click()
    panel = page.locator(f".trace-panel[data-trace='{name}']")
    expect(panel).to_be_visible()
    return panel


def drawing(page, index=1):
    """What the trace panel at `index` last drew."""
    return page.evaluate(
        f"""(() => {{
            const u = window.pyacquisition.tracePlots?.[{index}];
            const d = u?._drawing;
            if (!d) return null;
            return {{
                seqs: d.traces.map((t) => t.seq), binned: d.traces.map((t) => t.binned),
                overlay: d.overlay, x: u.axes[0].label, y: u.axes[1].label,
                xs: [u.scales.x.min, u.scales.x.max],
            }};
        }})()"""
    )


def test_the_add_menu_offers_a_plot_or_each_trace(trace_page):
    trace_page.get_by_role("button", name="Add plot").click()
    menu = trace_page.get_by_role("menu", name="Add a plot")
    assert [i.inner_text() for i in menu.get_by_role("menuitem").all()] == [
        "Plot of columns", "Trace: spectrum", "Trace: short", "Trace: slow"]
    menu.get_by_role("menuitem", name="Plot of columns").click()
    expect(trace_page.locator(".plot-panel:not(.trace-panel)")).to_have_count(2)


def test_a_trace_panel_follows_the_latest_with_three_behind(trace_page):
    add_trace_panel(trace_page, "spectrum")
    trace_page.wait_for_function(
        "window.pyacquisition.tracePlots?.[1]?._drawing?.traces.length === 4", timeout=10_000
    )
    first = drawing(trace_page)
    assert first["overlay"] == 3 and first["x"] == "frequency (Hz)" and first["y"] == "amplitude (V)"
    assert first["xs"][0] <= 0 and first["xs"][1] >= 10  # the generator's axis
    assert first["binned"] == [True] * 4  # 2048 points: binned, as band and mean
    # A new trace moves them all along.
    trace_page.wait_for_function(
        f"window.pyacquisition.tracePlots[1]._drawing.traces.at(-1).seq > {first['seqs'][-1]}",
        timeout=5_000,
    )
    later = drawing(trace_page)
    assert len(later["seqs"]) == 4 and later["seqs"][0] > first["seqs"][0]
    expect(trace_page.locator(".trace-note")).to_contain_text(re.compile(r"#\d+ at .*2,048 points, binned"))


def test_acquire_now_takes_one_at_once(trace_page, rig):
    panel = add_trace_panel(trace_page, "short")
    expect(panel.locator(".trace-waiting")).to_have_text("Waiting for the first short trace")
    panel.get_by_role("button", name="Acquire now").click()
    trace_page.wait_for_function(
        "window.pyacquisition.tracePlots?.[1]?._drawing?.traces.length >= 1", timeout=5_000
    )
    assert drawing(trace_page)["binned"][-1] is False  # 300 points: sent whole
    expect(panel.locator(".trace-waiting")).to_have_count(0)


def test_acquire_now_waits_for_a_slow_sweep(trace_page):
    panel = add_trace_panel(trace_page, "slow")
    button = panel.get_by_role("button", name=re.compile("Acquire now|Acquiring"))
    button.click()
    expect(button).to_have_text("Acquiring…")
    # Longer than a request's usual 5 s, and still no error.
    trace_page.wait_for_function(
        "window.pyacquisition.tracePlots?.[1]?._drawing?.traces.length >= 1", timeout=15_000
    )
    expect(button).to_have_text("Acquire now")
    expect(panel.get_by_role("alert")).to_have_count(0)


def test_ten_overlays_of_a_2048_point_trace_draw_within_a_frame(trace_page):
    panel = add_trace_panel(trace_page, "spectrum")
    panel.get_by_label("Earlier traces shown behind").select_option("10")
    trace_page.wait_for_function(
        "window.pyacquisition.tracePlots?.[1]?._drawing?.traces.length === 11", timeout=15_000
    )
    # Some draws of all eleven, then how long they took.
    trace_page.wait_for_timeout(1500)
    times = trace_page.evaluate("window.pyacquisition.traceTimes.slice(-5)")
    assert statistics.median(times) < 16, times


def test_a_hidden_channel_and_log_y_are_kept_in_the_panel(trace_page):
    panel = add_trace_panel(trace_page, "spectrum")
    panel.get_by_role("button", name="amplitude (V)").click()
    panel.get_by_role("button", name="Axis settings").click()
    trace_page.get_by_label("Log y").check()
    trace_page.get_by_role("button", name="Apply").click()
    saved = trace_page.evaluate("JSON.parse(sessionStorage.getItem('pyacquisition:plots'))")
    trace = next(p for p in saved["panels"] if p.get("kind") == "trace")
    assert trace["trace"] == "spectrum" and trace["hidden"] == ["amplitude"] and trace["logY"] is True


def test_the_latest_trace_exports_as_csv_at_full_resolution(trace_page):
    add_trace_panel(trace_page, "spectrum")
    trace_page.wait_for_function("window.pyacquisition.tracePlots?.[1]?._drawing?.traces.length >= 1")
    csv = trace_page.evaluate(
        """async () => {
            const { fetchLatest } = await import('/ui/js/traces.js');
            const { traceCsv } = await import('/ui/js/plot/trace-panel.js');
            return traceCsv((await fetchLatest('spectrum', { full: true })).traces[0]);
        }"""
    )
    lines = csv.strip().split("\r\n")
    assert lines[0] == "frequency (Hz),amplitude (V)" and len(lines) == 2049
    assert lines[1].startswith("0,")


# ------------------------------------------------------------ a sparse column
def test_an_occasional_traces_reduction_is_three_dots_and_keeps_its_last_value(trace_page, rig):
    for _ in range(3):
        requests.get(f"{rig.address}/traces/short/acquire", timeout=10)
        trace_page.wait_for_timeout(400)  # a few rows between them
    trace_page.evaluate(
        """new Promise((resolve) => window.dispatchEvent(new CustomEvent('pyacquisition:add-series',
            { detail: { column: 'short_mean', plot: 1, done: resolve } })))"""
    )
    trace_page.wait_for_function(
        """(() => { const u = window.pyacquisition.plot;
            return u && u.series.some((s) => s._paths?.stroke?.dots >= 3); })()""",
        timeout=5_000,
    )
    dots = trace_page.evaluate(
        "window.pyacquisition.plot.series.map((s) => s._paths?.stroke?.dots ?? 0)"
    )
    assert max(dots) >= 3  # this test's three, and any taken before it

    trace_page.get_by_role("tab", name="Values").click()
    tile = trace_page.locator(".value-tile[data-column='short_mean']")
    expect(tile).to_have_class(re.compile("value-stale"))
    expect(tile.locator(".value-age")).to_have_text(re.compile(r"^\d+ s ago$"))
    expect(tile.locator(".value-number")).not_to_have_text("—")


def test_an_experiment_with_no_traces_has_no_menu(page):
    page.page.get_by_role("button", name="Add plot").click()
    expect(page.page.get_by_role("menu")).to_have_count(0)
    expect(page.page.locator(".plot-panel")).to_have_count(2)
