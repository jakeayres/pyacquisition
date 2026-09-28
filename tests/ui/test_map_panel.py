"""The map panel (plot/map-panel.js) and the colour map it draws with
(plot/colourmap.js): the strips' geometry and the colour scale, through the
pure functions and the pixels drawn, and the panel on a running experiment
(traces milestone 6)."""

import math
import re

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect

from pyacquisition import Measurement
from pyacquisition.core.trace_source import Trace
from pyacquisition.instruments.software.trace_generator import TraceGenerator
from ui_helpers import Page, Running, SmokeExperiment


class MapRig(SmokeExperiment):
    """A spectrum on a clock whose peak follows a temperature ramping from 2 K
    to 18 K and back to 2 K again every 8 s."""

    def setup(self):
        super().setup()
        clock = self.instruments["clock"]
        analyser = TraceGenerator("analyser", points=512, width=0.3, noise=0.01)
        self.add_instrument(analyser)

        def temperature():
            value = 2 + (clock.time() * 2) % 16
            analyser.set_centre(1 + value / 2)  # 2 Hz to 10 Hz
            return value

        self.add_measurement(Measurement("T", temperature, unit="K"))
        self.add_trace(Trace("spectrum", analyser.get_spectrum, every=0.1))


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    running = Running(MapRig, tmp_path_factory.mktemp("map-panel"), measurement_period=0.05)
    yield running
    running.stop()


@pytest.fixture
def map_page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    yield page.page
    assert page.errors == [], f"the page logged errors: {page.errors}"


def add_map(page, name="spectrum"):
    page.get_by_role("button", name="Add plot").click()
    page.get_by_role("menuitem", name=f"Map: {name}").click()
    panel = page.locator(f".map-panel[data-trace='{name}']")
    expect(panel).to_be_visible()
    return panel


def colourmap(page, expression):
    return page.evaluate(f"import('/ui/js/plot/colourmap.js').then((c) => {expression})")


def mapping(page, expression):
    return page.evaluate(f"import('/ui/js/plot/map-panel.js').then((m) => {expression})")


# ------------------------------------------------------------ the strips
def test_even_steps_give_strips_meeting_halfway(page):
    assert colourmap(page.page, "c.strips([1, 2, 3])") == [[0.5, 1.5], [1.5, 2.5], [2.5, 3.5]]


def test_uneven_steps_give_strips_of_matching_heights(page):
    # Steps of 1, 2 and 4: the median is 2, so no half reaches further than 2.
    assert colourmap(page.page, "c.strips([1, 2, 4, 8])") == [[0.5, 1.5], [1.5, 3], [3, 6], [6, 10]]


def test_a_late_trace_after_close_ones_is_a_strip_after_a_gap(page):
    # Three close together, then one much later: not one tall strip.
    # The median step is 1, so the last close one reaches 1 above itself, and
    # the late one 1 either side: a gap from 3 to 99 between them.
    bands = colourmap(page.page, "c.strips([0, 1, 2, 100])")
    assert bands == [[-0.5, 0.5], [0.5, 1.5], [1.5, 3], [99, 101]]


def test_strips_of_a_sweep_back_and_repeats(page):
    # Out of order (a sweep down), and one y twice: the same strip for both.
    bands = colourmap(page.page, "c.strips([3, 2, 1, 2])")
    assert bands == [[2.5, 3.5], [1.5, 2.5], [0.5, 1.5], [1.5, 2.5]]
    assert colourmap(page.page, "c.strips([5])") == [[4.75, 5.25]]
    assert colourmap(page.page, "c.strips([1, NaN, 2])") == [[0.5, 1.5], None, [1.5, 2.5]]


def test_log_strips_are_worked_out_in_powers_of_ten(page):
    low, high = colourmap(page.page, "c.strips([1, 10, 100], { log: true })")[1]
    assert low == pytest.approx(10**0.5) and high == pytest.approx(10**1.5)


# ------------------------------------------------------------ the colour scale
def test_the_colour_scale_clamps_and_leaves_what_has_no_place(page):
    scale = "{min: 0, max: 10, log: false}"
    units = colourmap(page.page, f"[-5, 0, 5, 10, 20, NaN].map((v) => c.colourUnit({scale}, v))")
    assert units[:5] == [0, 0, 0.5, 1, 1] and math.isnan(units[5])
    log = "{min: 1, max: 100, log: true}"
    units = colourmap(page.page, f"[10, 0, -1].map((v) => c.colourUnit({log}, v))")
    assert units[0] == 0.5 and all(math.isnan(u) for u in units[1:])


def test_the_colour_maps_run_from_their_first_stop_to_their_last(page):
    ends = colourmap(
        page.page,
        "Object.keys(c.COLOUR_MAPS).map((n) => [c.pixelColour(c.colourTable(n)[0]),"
        " c.pixelColour(c.colourTable(n)[255])])",
    )
    assert ends == [
        ["rgb(68, 1, 84)", "rgb(253, 231, 37)"],  # viridis
        ["rgb(0, 0, 4)", "rgb(252, 253, 191)"],  # magma
        ["rgb(59, 76, 192)", "rgb(180, 4, 38)"],  # coolwarm
    ]


def test_the_value_range_follows_the_data_or_fixed_limits(page):
    rows = "[{ values: new Float32Array([2, NaN, 8]) }, { values: new Float32Array([-1, 4]) }]"
    assert colourmap(page.page, f"c.valueRange({rows})") == [-1, 8]
    assert colourmap(page.page, f"c.valueRange({rows}, {{ log: true }})") == [2, 8]
    assert mapping(page.page, f"m.colourScale({rows}, {{ log: false, limits: null }})") == {
        "min": -1, "max": 8, "log": False}
    assert mapping(page.page, f"m.colourScale({rows}, {{ log: false, limits: {{ min: 0, max: 1 }} }})") == {
        "min": 0, "max": 1, "log": False}


# ------------------------------------------------------------ the pixels
DRAW = """(() => {{
    const canvas = document.createElement('canvas');
    canvas.width = 100;
    canvas.height = 100;
    const ctx = canvas.getContext('2d');
    const table = c.colourTable('viridis');
    const rows = {rows};
    c.drawMap(ctx, {{ left: 0, top: 0, width: 100, height: 100 }}, rows, {{
        x: {{ min: 0, max: 10, log: false }}, y: {{ min: 0, max: 10, log: false }},
        colour: {{ min: 0, max: 1, log: false }}, table }});
    const at = (x, y) => {{ const d = ctx.getImageData(x, y, 1, 1).data; return d[3] ? `rgb(${{d[0]}}, ${{d[1]}}, ${{d[2]}})` : null; }};
    return {{ low: c.pixelColour(table[0]), high: c.pixelColour(table[255]), points: {points}.map(([x, y]) => at(x, y)) }};
}})()"""


def test_each_row_covers_its_own_x_range_and_its_own_strip(page):
    # Two rows: x 0 to 5 (low values) from y 0 to 5, and x 5 to 10 (high values)
    # from y 5 to 10. Pixel rows count down from the top.
    rows = """[
        { x: new Float64Array([0.5, 1.5, 2.5, 3.5, 4.5]), values: new Float32Array([0, 0, 0, 0, 0]), low: 0, high: 5 },
        { x: new Float64Array([5.5, 6.5, 7.5, 8.5, 9.5]), values: new Float32Array([1, 1, 1, 1, 1]), low: 5, high: 10 },
    ]"""
    points = "[[20, 75], [75, 25], [75, 75], [20, 25]]"
    drawn = colourmap(page.page, DRAW.format(rows=rows, points=points))
    assert drawn["points"] == [drawn["low"], drawn["high"], None, None]


def test_a_value_takes_the_colour_nearest_its_pixel_and_nan_is_left_empty(page):
    rows = """[{ x: new Float64Array([0, 5, 10]), values: new Float32Array([0, NaN, 1]), low: 0, high: 10 }]"""
    points = "[[1, 50], [50, 50], [98, 50]]"
    drawn = colourmap(page.page, DRAW.format(rows=rows, points=points))
    assert drawn["points"] == [drawn["low"], None, drawn["high"]]


def test_a_map_of_500_traces_of_2048_points_draws_within_50_ms(page):
    took = colourmap(
        page.page,
        """(() => {
            const canvas = document.createElement('canvas');
            canvas.width = 800;
            canvas.height = 500;
            const ctx = canvas.getContext('2d');
            const x = Float64Array.from({ length: 2048 }, (_, i) => i / 2047);
            const rows = Array.from({ length: 500 }, (_, r) => ({
                x, values: Float32Array.from(x, (v) => Math.sin(10 * v + r / 20)), low: r, high: r + 1 }));
            const options = { x: { min: 0, max: 1, log: false }, y: { min: 0, max: 500, log: false },
                colour: { min: -1, max: 1, log: false }, table: c.colourTable('magma') };
            const times = [];
            for (let i = 0; i < 5; i++) {
                const start = performance.now();
                c.drawMap(ctx, { left: 0, top: 0, width: 800, height: 500 }, rows, options);
                times.push(performance.now() - start);
            }
            return times.sort((a, b) => a - b)[2];
        })()""",
    )
    assert took < 50, took


def test_y_is_the_midpoint_of_a_column_at_the_start_and_end(page):
    trace = "{ time_start: 100, time: 104, row_start: { T: 4 }, row: { T: 6, B: 1 } }"
    assert mapping(page.page, f"[m.yOf({trace}, 'T'), m.yOf({trace}, 'B'), m.yOf({trace}, m.TAKEN, 100)]") == [
        5, 1, 2]
    assert mapping(page.page, f"m.yChoices([{trace}])") == ["T", "B", "(when taken)"]


# ------------------------------------------------------------ the panel
def map_drawing(page, index=1):
    return page.evaluate(
        f"""(() => {{
            const u = window.pyacquisition.mapPlots?.[{index}];
            const d = u?._drawing;
            if (!d) return null;
            return {{ rows: d.rows.length, drawn: d.drawn, colour: d.colour,
                      ys: d.rows.map((r) => r.y), x: u.axes[0].label, y: u.axes[1].label }};
        }})()"""
    )


def test_a_map_against_time_fills_as_traces_arrive(map_page):
    add_map(map_page)
    map_page.wait_for_function("window.pyacquisition.mapPlots?.[1]?._drawing?.rows.length >= 5", timeout=10_000)
    first = map_drawing(map_page)
    assert first["x"] == "frequency (Hz)" and first["y"] == "time"  # the rig's time has no unit
    assert first["drawn"] == first["rows"]
    map_page.wait_for_function(
        f"window.pyacquisition.mapPlots[1]._drawing.rows.length > {first['rows'] + 5}", timeout=10_000
    )
    ys = map_drawing(map_page)["ys"]
    assert ys == sorted(ys)  # against time, in the order taken
    # The colour bar has a scale that follows the data.
    ticks = map_page.locator(".map-panel .colour-bar-tick")
    expect(ticks.first).to_be_visible()


def test_against_temperature_the_peak_moves_across(map_page):
    panel = add_map(map_page)
    panel.get_by_label("Against").select_option("T")
    map_page.wait_for_function(
        "window.pyacquisition.mapPlots?.[1]?._drawing?.rows.length >= 30", timeout=15_000
    )
    peaks = map_page.evaluate(
        """(() => {
            const rows = window.pyacquisition.mapPlots[1]._drawing.rows;
            return rows.map((r) => {
                let best = 0;
                for (let i = 1; i < r.values.length; i++) if (r.values[i] > r.values[best]) best = i;
                return [r.y, r.x[best]];
            });
        })()"""
    )
    assert map_drawing(map_page)["y"] == "T (K)"
    # The peak is where the temperature put it: a slanted line on the map.
    assert all(abs(x - (1 + t / 2)) < 0.5 for t, x in peaks), peaks


def test_fixed_colour_limits_hold_and_auto_follows_again(map_page):
    panel = add_map(map_page)
    map_page.wait_for_function("window.pyacquisition.mapPlots?.[1]?._drawing?.rows.length >= 3", timeout=10_000)
    panel.get_by_role("button", name="Colour scale").click()
    dialog = map_page.get_by_role("dialog", name="Colour scale")
    dialog.get_by_label("Auto").uncheck()
    dialog.get_by_label("Colour minimum").fill("0.2")
    dialog.get_by_label("Colour maximum").fill("0.6")
    dialog.get_by_label("Colour map").select_option("magma")
    dialog.get_by_role("button", name="Apply").click()
    map_page.wait_for_function("window.pyacquisition.mapPlots[1]._drawing.colour.max === 0.6")
    assert map_drawing(map_page)["colour"] == {"min": 0.2, "max": 0.6, "log": False}
    expect(panel.locator(".colour-bar-tick").first).to_have_text(re.compile(r"0\.2"))

    panel.get_by_role("button", name="Colour scale").click()
    dialog.get_by_label("Auto").check()
    dialog.get_by_role("button", name="Apply").click()
    map_page.wait_for_function("window.pyacquisition.mapPlots[1]._drawing.colour.max > 0.9")


def test_a_bad_colour_limit_is_refused(map_page):
    panel = add_map(map_page)
    panel.get_by_role("button", name="Colour scale").click()
    dialog = map_page.get_by_role("dialog", name="Colour scale")
    dialog.get_by_label("Auto").uncheck()
    dialog.get_by_label("Colour minimum").fill("0")
    dialog.get_by_label("Colour maximum").fill("1")
    dialog.get_by_label("Log colour").check()
    dialog.get_by_role("button", name="Apply").click()
    expect(dialog.get_by_role("alert")).to_have_text("a log axis needs a minimum above zero.")
