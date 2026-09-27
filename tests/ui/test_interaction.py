"""Zooming, panning, pausing, several series, the readout and log axes
(milestone 5)."""

import math

import pytest

pytest.importorskip("playwright")

from ui_helpers import Page, Running, set_log
from playwright.sync_api import expect

from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock


class Rig(Experiment):
    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)
        self.add_measurement(Measurement("time", clock.time, unit="s"))
        self.add_measurement(
            Measurement("T", lambda: 5 + math.sin(clock.time()), unit="K")
        )
        self.add_measurement(Measurement("x", lambda: math.cos(clock.time()), unit="V"))
        self.add_measurement(
            Measurement("y", lambda: math.sin(clock.time()) / 2, unit="V")
        )
        # Enough columns to fill all eight colours.
        for n in range(6):
            self.add_measurement(Measurement(f"c{n}", lambda n=n: n + 1.0))
        # Values far below what a log axis can label, between ordinary ones.
        self.add_measurement(
            Measurement("tiny", lambda: 1e-35 if int(clock.time() * 20) % 2 else 1.0)
        )


# One rig for the whole module: the tests only look at its data, and starting
# one for each test, and waiting for its rows, cost a few seconds a test.
@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    running = Running(Rig, tmp_path_factory.mktemp("interaction"), measurement_period=0.05)
    yield running
    running.stop()


@pytest.fixture
def plot_page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    # Three seconds of data, so the range grows only a little during a gesture
    # while the plot is still following.
    page.page.wait_for_function(
        "window.pyacquisition?.plot && window.pyacquisition.store.current.rows > 60",
        timeout=15000,
    )
    yield page
    assert page.errors == [], f"the page logged errors: {page.errors}"


def plot(page, expression):
    return page.evaluate(
        f"(() => {{ const u = window.pyacquisition.plot; return {expression}; }})()"
    )


def x_range(page):
    return plot(page, "[u.scales.x.min, u.scales.x.max]")


def y_range(page):
    return plot(page, "[u.scales.y.min, u.scales.y.max]")


def over(page):
    # Waited for: changing what is plotted draws the plot afresh, and for a
    # moment there is none.
    surface = page.locator(".u-over")
    surface.wait_for(state="visible")
    return surface.bounding_box()


def drag(page, start, end, button="left", shift=False):
    """Drags across the plot, from and to fractions of its width and height."""
    box = over(page)
    def at(f):
        return box["x"] + f[0] * box["width"], box["y"] + f[1] * box["height"]

    if shift:
        page.keyboard.down("Shift")
    page.mouse.move(*at(start))
    page.mouse.down(button=button)
    page.mouse.move(*at(end), steps=6)
    page.mouse.up(button=button)
    if shift:
        page.keyboard.up("Shift")


def wheel(page, dx, dy, modifier=None):
    box = over(page)
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    if modifier:
        page.keyboard.down(modifier)
    page.mouse.wheel(dx, dy)
    if modifier:
        page.keyboard.up(modifier)
    page.wait_for_timeout(50)


def plot_size(page):
    return page.evaluate(
        "(() => { const o = document.querySelector('.u-over');"
        " return [o.clientWidth, o.clientHeight]; })()"
    )


# Shown while an axis is not scaling to the data, with the way back.
def autoscale_off(page):
    return page.locator(".autoscale-off")


def autoscale(page):
    page.get_by_role("button", name="Autoscale", exact=True).click()


# -------------------------------------------------------------- zooming
def test_dragging_a_box_zooms_into_it_and_turns_autoscale_off(plot_page):
    page = plot_page.page
    before_x, before_y = x_range(page), y_range(page)

    drag(page, (0.25, 0.25), (0.75, 0.75))

    expect(autoscale_off(page)).to_contain_text("Autoscale off: x, y")
    after_x, after_y = x_range(page), y_range(page)
    # About the middle half of what was shown (which grew a little meanwhile).
    width = before_x[1] - before_x[0]
    assert after_x[1] - after_x[0] == pytest.approx(width * 0.5, rel=0.1)
    assert before_x[0] < after_x[0] < after_x[1] < before_x[1] + 0.1 * width
    assert after_y[1] - after_y[0] < (before_y[1] - before_y[0]) * 0.6


def test_a_zoomed_view_holds_while_data_arrives(plot_page):
    page = plot_page.page
    drag(page, (0.2, 0.2), (0.6, 0.8))
    held = x_range(page), y_range(page)
    rows = page.evaluate("window.pyacquisition.store.current.rows")

    page.wait_for_function(f"window.pyacquisition.store.current.rows > {rows + 5}")

    assert (x_range(page), y_range(page)) == held


def test_the_new_data_is_still_drawn_while_autoscale_is_off(plot_page):
    page = plot_page.page
    drag(page, (0.05, 0.05), (0.95, 0.95))
    rows = plot(page, "u.data[2][0].length")

    page.wait_for_function(f"window.pyacquisition.plot.data[2][0].length > {rows + 5}")


def test_autoscale_scales_to_the_data_again(plot_page):
    page = plot_page.page
    drag(page, (0.1, 0.1), (0.4, 0.9))
    zoomed_max = x_range(page)[1]

    autoscale(page)

    expect(autoscale_off(page)).to_have_count(0)
    page.wait_for_function(f"window.pyacquisition.plot.scales.x.max > {zoomed_max}")
    newest = page.evaluate("window.pyacquisition.store.latest.time")
    assert x_range(page)[1] >= newest - 0.2


def test_a_double_click_turns_autoscale_back_on(plot_page):
    page = plot_page.page
    drag(page, (0.1, 0.1), (0.4, 0.9))
    expect(autoscale_off(page)).to_be_visible()

    box = over(page)
    page.mouse.dblclick(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    expect(autoscale_off(page)).to_have_count(0)


def test_a_thin_drag_zooms_x_only_and_fits_y_to_what_is_left(plot_page):
    page = plot_page.page
    before_x = x_range(page)

    drag(page, (0.5, 0.5), (0.9, 0.51))

    after_x = x_range(page)
    assert after_x[1] - after_x[0] < (before_x[1] - before_x[0]) * 0.5
    # y fits the points in the new x range, with a little room.
    fitted = plot(
        page,
        "(() => { const [xs, ys] = u.data[2]; let lo = Infinity, hi = -Infinity;"
        " for (let i = 0; i < xs.length; i++) if (xs[i] >= u.scales.x.min &&"
        " xs[i] <= u.scales.x.max) { lo = Math.min(lo, ys[i]); hi = Math.max(hi, ys[i]); }"
        " return [lo, hi]; })()",
    )
    low, high = y_range(page)
    assert low <= fitted[0] and fitted[1] <= high
    assert high - low < (fitted[1] - fitted[0]) * 1.5 + 1e-9


def test_a_click_does_not_zoom(plot_page):
    page = plot_page.page
    box = over(page)
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    expect(autoscale_off(page)).to_have_count(0)


# -------------------------------------------------------------- panning
def test_shift_dragging_pans_and_turns_autoscale_off(plot_page):
    page = plot_page.page
    before = x_range(page)

    drag(page, (0.6, 0.5), (0.4, 0.5), shift=True)

    expect(autoscale_off(page)).to_be_visible()
    after = x_range(page)
    width = before[1] - before[0]
    # The same span, moved on by about a fifth of it (dragged left: later times).
    assert after[1] - after[0] == pytest.approx(width, rel=0.1)
    assert after[0] - before[0] == pytest.approx(0.2 * width, rel=0.25)


def test_the_middle_button_pans_too(plot_page):
    page = plot_page.page
    _, before = held(page)

    drag(page, (0.5, 0.4), (0.5, 0.6), button="middle")

    after = y_range(page)
    assert after[0] > before[0]  # dragged down: the view moves up


def held(page):
    """Holds the view still (a scroll that moves nothing much), so the ranges
    measured next do not grow as data arrives."""
    wheel(page, 1, 1)
    expect(autoscale_off(page)).to_be_visible()
    return x_range(page), y_range(page)


def test_scrolling_up_and_down_pans_y(plot_page):
    page = plot_page.page
    (x0, y0) = held(page)
    _, height = plot_size(page)

    wheel(page, 0, 100)  # down: the view moves down by as far as it was scrolled

    span = y0[1] - y0[0]
    assert x_range(page) == x0
    y1 = y_range(page)
    assert y1[1] - y1[0] == pytest.approx(span, rel=1e-6)
    assert y0[0] - y1[0] == pytest.approx(span * 100 / height, rel=1e-3)


def test_scrolling_sideways_pans_x(plot_page):
    page = plot_page.page
    (x0, y0) = held(page)
    width, _ = plot_size(page)

    wheel(page, 100, 0)

    span = x0[1] - x0[0]
    assert y_range(page) == y0
    x1 = x_range(page)
    assert x1[1] - x1[0] == pytest.approx(span, rel=1e-6)
    assert x1[0] - x0[0] == pytest.approx(span * 100 / width, rel=1e-3)


def test_shift_with_a_wheel_pans_x(plot_page):
    page = plot_page.page
    (x0, y0) = held(page)

    wheel(page, 0, 100, "Shift")

    assert x_range(page)[0] > x0[0]
    assert y_range(page) == y0


def test_a_diagonal_scroll_pans_both_axes(plot_page):
    # As a trackpad does.
    page = plot_page.page
    (x0, y0) = held(page)

    wheel(page, 60, 60)

    assert x_range(page)[0] > x0[0]
    assert y_range(page)[0] < y0[0]


def test_ctrl_wheel_zooms_about_the_pointer(plot_page):
    page = plot_page.page
    before = x_range(page)

    wheel(page, 0, -100, "Control")  # in

    after = x_range(page)
    assert after[1] - after[0] < before[1] - before[0]
    middle = (before[0] + before[1]) / 2
    assert after[0] < middle < after[1]
    expect(autoscale_off(page)).to_be_visible()


# -------------------------------------------------------------- several series
def chips(page):
    return page.locator(".series-chip")


def test_a_column_can_be_added_to_the_plot_with_its_own_colour(plot_page):
    page = plot_page.page
    page.select_option(".series-add", "x")

    expect(chips(page)).to_have_count(2)
    page.wait_for_function("window.pyacquisition.plot.series.length === 5")
    assert plot(page, "u.series[2].stroke()") != plot(page, "u.series[4].stroke()")
    assert plot(page, "u.axes[1].label") == "T (K), x (V)"


def test_a_colour_stays_with_its_column_when_another_is_removed(plot_page):
    page = plot_page.page
    page.select_option(".series-add", "x")
    page.select_option(".series-add", "y")
    page.wait_for_function("window.pyacquisition.plot.series.length === 7")
    y_colour = plot(page, "u.series[6].stroke()")

    page.get_by_role("button", name="Remove T", exact=True).click()
    page.wait_for_function("window.pyacquisition.plot.series.length === 5")

    assert (
        plot(page, "u.series[4].stroke()") == y_colour
    )  # y, now second, kept its colour
    # T, added back last, has its own colour again (the quantity's, not a place's).
    page.select_option(".series-add", "T")
    page.wait_for_function("window.pyacquisition.plot.series.length === 7")
    assert plot(page, "u.series[6].stroke()") == page.evaluate(
        "getComputedStyle(document.documentElement).getPropertyValue('--series-1').trim()"
    )


def test_clicking_a_legend_entry_hides_and_shows_its_column(plot_page):
    page = plot_page.page
    page.select_option(".series-add", "x")
    toggle = chips(page).filter(has_text="x").locator(".series-toggle")

    toggle.click()
    expect(toggle).to_have_attribute("aria-pressed", "false")
    page.wait_for_function("window.pyacquisition.plot.data[4][1].length === 0")

    toggle.click()
    page.wait_for_function("window.pyacquisition.plot.data[4][1].length > 0")


def test_at_most_eight_columns_can_be_plotted(plot_page):
    page = plot_page.page
    for name in ["x", "y", "c0", "c1", "c2", "c3", "c4"]:
        page.select_option(".series-add", name)

    expect(chips(page)).to_have_count(8)
    expect(page.locator(".series-add")).to_be_disabled()


def test_the_last_column_cannot_be_removed(plot_page):
    expect(chips(plot_page.page).locator(".series-remove")).to_have_count(0)


# -------------------------------------------------------------- the readout
def hover(page, fx, fy):
    box = over(page)
    page.mouse.move(box["x"] + fx * box["width"], box["y"] + fy * box["height"])


def test_hovering_shows_the_values_of_the_nearest_row(plot_page):
    page = plot_page.page
    page.select_option(".series-add", "x")
    drag(page, (0.05, 0.05), (0.95, 0.95))  # hold the view still
    hover(page, 0.5, 0.5)

    tip = page.locator(".plot-tip")
    expect(tip).to_be_visible()
    rows = tip.locator(".plot-tip-row")
    expect(rows).to_have_count(3)  # time, then T and x
    expect(rows.nth(0)).to_contain_text("time")
    expect(rows.nth(1)).to_contain_text("T")
    expect(rows.nth(2)).to_contain_text("x")
    expect(page.locator(".plot-dot")).to_have_count(2)
    expect(page.locator(".plot-crosshair")).to_be_visible()

    # The row shown is the one nearest the pointer's time, and its values match.
    shown_time = float(rows.nth(0).locator("strong").inner_text())
    x_middle = sum(x_range(page)) / 2
    times = plot(page, "Array.from(u.data[2][0])")
    nearest = min(times, key=lambda t: abs(t - x_middle))
    assert shown_time == pytest.approx(nearest, rel=1e-4)


def test_the_readout_goes_when_the_pointer_leaves(plot_page):
    page = plot_page.page
    hover(page, 0.5, 0.5)
    expect(page.locator(".plot-tip")).to_be_visible()

    page.mouse.move(5, 5)

    expect(page.locator(".plot-tip")).to_be_hidden()
    expect(page.locator(".plot-dot")).to_have_count(0)


def test_the_readout_finds_the_nearest_point_when_x_is_not_sorted(plot_page):
    page = plot_page.page
    page.select_option(
        ".picker:has-text('against') select", "x"
    )  # T against x: a circle
    page.wait_for_function("window.pyacquisition.plot.axes[0].label.startsWith('x')")
    drag(page, (0.02, 0.02), (0.98, 0.98))
    hover(page, 0.5, 0.05)  # near the top of the circle

    tip = page.locator(".plot-tip")
    expect(tip).to_be_visible()
    t_shown = float(tip.locator(".plot-tip-row").nth(1).locator("strong").inner_text())
    low, high = y_range(page)
    assert t_shown > low + 0.5 * (high - low)  # a point near the top, not the bottom


# -------------------------------------------------------------- log axes
def test_log_y_makes_the_y_axis_logarithmic(plot_page):
    page = plot_page.page
    set_log(page, "y")

    page.wait_for_function("window.pyacquisition.plot.scales.y.distr === 3")
    assert y_range(page)[0] > 0
    settings = page.get_by_role("button", name="Axis settings")
    expect(settings).to_have_attribute("aria-pressed", "true")
    expect(settings).to_have_attribute("title", "Axis settings: log y")


def test_a_narrow_log_axis_still_has_several_labels(plot_page):
    # T only goes between 4 and 6, less than a decade: uPlot's own log ticks
    # gave it a single label.
    page = plot_page.page
    set_log(page, "y")
    page.wait_for_function("window.pyacquisition.plot.scales.y.distr === 3")

    labels = [label for label in plot(page, "u.axes[1]._values") if label]
    assert len(labels) >= 3


def test_a_log_axis_is_not_stretched_beyond_the_data(plot_page):
    # A log range was forced to span at least a decade, squashing the data.
    page = plot_page.page
    set_log(page, "y")
    page.wait_for_function("window.pyacquisition.plot.scales.y.distr === 3")

    low, high = y_range(page)
    assert high / low < 2  # T is 4 to 6


def test_values_at_or_below_zero_are_left_off_a_log_axis(plot_page):
    page = plot_page.page
    page.select_option(".series-add", "x")  # cos(t): half its values below zero
    page.get_by_role("button", name="Remove T", exact=True).click()
    set_log(page, "y")
    page.wait_for_function("window.pyacquisition.plot.scales.y.distr === 3")

    low, high = y_range(page)
    positive = [v for v in plot(page, "Array.from(u.data[2][1])") if v > 0]
    assert 0 < low <= min(positive) and max(positive) <= high


def test_a_log_axis_copes_with_values_far_too_small_to_label(plot_page):
    # uPlot's log ticks run away below about 1e-22, until the page runs out of memory.
    page = plot_page.page
    page.select_option(".series-add", "tiny")
    page.get_by_role("button", name="Remove T", exact=True).click()
    set_log(page, "y")

    page.wait_for_function("window.pyacquisition.plot.scales.y.distr === 3")
    low, high = y_range(page)
    assert low >= 1e-20 and high > 1
    # (The fixture fails the test if the page logged an error.)


def test_log_x_makes_the_x_axis_logarithmic(plot_page):
    page = plot_page.page
    set_log(page, "x")

    page.wait_for_function("window.pyacquisition.plot.scales.x.distr === 3")
    assert x_range(page)[0] > 0


# -------------------------------------------------------------- drawing, alone
def draw(page, expression):
    return page.evaluate(f"import('/ui/js/plot/draw.js').then(d => {expression})")


def test_places_on_a_log_scale(page):
    scale = "{min: 1, max: 1000, log: true}"
    assert draw(page.page, f"d.unitOf({scale}, 10)") == pytest.approx(1 / 3)
    assert draw(page.page, f"d.valueAt({scale}, 2 / 3)") == pytest.approx(100)
    assert draw(page.page, f"Number.isNaN(d.unitOf({scale}, 0))") is True


def test_a_log_scale_is_kept_within_what_can_be_labelled(page):
    kept = draw(page.page, "d.withinLimits({min: 1e-40, max: 1e40, log: true})")
    assert (kept["min"], kept["max"]) == (1e-20, 1e25)
    assert draw(page.page, "d.withinLimits({min: -5, max: 5, log: false})") == {
        "min": -5,
        "max": 5,
        "log": False,
    }
    low, high = draw(page.page, "d.padded([1e-35, 1], 0.05, {log: true})")
    assert low == 1e-20 and high > 1


def test_a_log_range_is_padded_in_powers_of_ten(page):
    low, high = draw(page.page, "d.padded([10, 1000], 0.1, {log: true})")
    assert low == pytest.approx(10**0.8) and high == pytest.approx(10**3.2)
    assert draw(
        page.page, "d.extent([new Float64Array([-1, 0, 2, 5])], {log: true})"
    ) == [2, 5]


def test_the_nearest_value_in_a_sorted_column_steps_over_nan(page):
    xs = "new Float64Array([0, 1, NaN, NaN, 4, 5])"
    assert draw(page.page, f"d.nearestInSorted({xs}, 1.4)") == 1
    assert draw(page.page, f"d.nearestInSorted({xs}, 3.1)") == 4
    assert draw(page.page, f"d.nearestInSorted({xs}, 99)") == 5
    assert draw(page.page, "d.nearestInSorted(new Float64Array([NaN]), 1)") == -1


def test_the_nearest_point_in_two_dimensions(page):
    result = draw(
        page.page,
        "d.nearestPoint(new Float64Array([0, 1, 0]), [new Float64Array([0, 0, 1])],"
        " 0.1, 0.9, v => v, v => v)",
    )
    assert result["index"] == 2


def test_panning_and_zooming_a_scale(page):
    scale = "{min: 0, max: 10, log: false}"
    assert draw(page.page, f"d.panned({scale}, 0.1)") == {
        "min": 1,
        "max": 11,
        "log": False,
    }
    zoomed = draw(page.page, f"d.zoomedAbout({scale}, 0.5, 0.2)")
    assert (zoomed["min"], zoomed["max"]) == pytest.approx((1, 6))


def test_log_tick_labels(page):
    assert draw(page.page, "d.tickLabels([1e-6, 1e-3, 1, 1000, 1e7], {log: true})") == [
        "1e-6",
        "0.001",
        "1",
        "1000",
        "1e+7",
    ]


def test_ticks_that_uplot_leaves_unlabelled_get_no_label(page):
    assert draw(
        page.page, "d.tickLabels([1, null, null, 10, null, 100], {log: true})"
    ) == [
        "1",
        "",
        "",
        "10",
        "",
        "100",
    ]
    assert draw(page.page, "d.tickLabels([0, null, 10])") == ["0", "", "10"]


def test_the_y_extent_within_an_x_range(page):
    assert draw(
        page.page,
        "d.extentWithin(new Float64Array([0, 1, 2, 3]), [new Float64Array([9, 4, 6, 8])],"
        " {min: 1, max: 2})",
    ) == [4, 6]
