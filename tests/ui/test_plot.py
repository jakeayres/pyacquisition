"""The live plot: one column against another (milestone 4)."""

import json
import math

import pytest

pytest.importorskip("playwright")

from conftest import Page, Running
from playwright.sync_api import expect

from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock


class Rig(Experiment):
    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)
        self.add_measurement(Measurement("time", clock.time, unit="s"))
        self.add_measurement(
            Measurement("T", lambda: 4 + math.sin(clock.time()), unit="K")
        )
        self.add_measurement(Measurement("x", lambda: math.cos(clock.time()), unit="V"))


@pytest.fixture
def rig(tmp_path):
    running = Running(Rig, tmp_path, measurement_period=0.05)
    yield running
    running.stop()


@pytest.fixture
def plot_page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function(
        "window.pyacquisition?.plot && window.pyacquisition.store.current.rows > 5"
    )
    yield page
    assert page.errors == [], f"the page logged errors: {page.errors}"


def plot(page, expression):
    """Something about the uPlot instance, worked out in the page."""
    return page.evaluate(
        f"(() => {{ const u = window.pyacquisition.plot; return {expression}; }})()"
    )


def choose(page, picker, column):
    """Plots `column` against x ("against"), or as the only y column ("Plot")."""
    if picker == "against":
        page.select_option(".picker:has-text('against') select", column)
    else:
        chips = page.locator(".series-chip")
        if column not in chips.all_inner_texts()[0]:
            page.select_option(".series-add", column)
        while page.locator(".series-chip").count() > 1:
            page.locator(".series-chip").filter(has_not_text=column).locator(
                ".series-remove"
            ).first.click()
    page.wait_for_function(
        f"window.pyacquisition.plot.axes[{0 if picker == 'against' else 1}].label"
        f".startsWith({json.dumps(column)})"
    )


# -------------------------------------------------------------- what is plotted
def test_it_starts_with_the_first_column_against_time(plot_page):
    # The units come from the experiment a moment after the data.
    plot_page.page.wait_for_function(
        "window.pyacquisition.plot.axes[0].label === 'time (s)'"
    )
    assert plot(plot_page.page, "u.axes[0].label") == "time (s)"
    assert plot(plot_page.page, "u.axes[1].label") == "T (K)"


def test_any_column_can_be_plotted_against_any_other(plot_page):
    choose(plot_page.page, "against", "T")
    choose(plot_page.page, "Plot", "x")

    assert plot(plot_page.page, "u.axes[0].label") == "T (K)"
    assert plot(plot_page.page, "u.axes[1].label") == "x (V)"
    # The current file's x values are T, as measured.
    rows = plot(plot_page.page, "u.data[2][0].length")
    assert rows > 5


def test_the_choice_lasts_for_the_session(plot_page):
    choose(plot_page.page, "Plot", "x")

    plot_page.page.reload()
    plot_page.page.wait_for_function("window.pyacquisition?.plot")

    assert plot(plot_page.page, "u.axes[1].label") == "x (V)"


def test_the_plot_follows_the_newest_point(plot_page):
    first = plot(plot_page.page, "u.scales.x.max")
    plot_page.page.wait_for_timeout(600)

    newest = plot_page.page.evaluate("window.pyacquisition.store.latest.time")
    x_max = plot(plot_page.page, "u.scales.x.max")
    assert x_max > first
    assert x_max >= newest - 0.2  # within an update of the newest


def test_the_y_range_fits_the_data(plot_page):
    # Read together, so no new row arrives between the range and the data.
    y_min, y_max, values = plot(
        plot_page.page, "[u.scales.y.min, u.scales.y.max, Array.from(u.data[2][1])]"
    )

    assert y_min < min(values) and max(values) < y_max


# -------------------------------------------------------------- the previous file
def test_a_new_file_keeps_the_old_data_as_the_previous_file(plot_page, rig):
    rig.get("/scribe/next_file", title="sweep")
    plot_page.page.wait_for_function(
        "window.pyacquisition.store.current.rows > 3 && window.pyacquisition.store.previous"
    )

    assert plot(plot_page.page, "u.data[1][0].length") > 5  # the previous file
    assert plot(plot_page.page, "u.data[2][0].length") > 0  # the new one
    previous_stroke = plot(plot_page.page, "u.series[1].stroke()")
    current_stroke = plot(plot_page.page, "u.series[2].stroke()")
    assert previous_stroke.startswith("rgba(") and previous_stroke != current_stroke
    assert plot(plot_page.page, "u.series[1].width") < plot(
        plot_page.page, "u.series[2].width"
    )
    expect(plot_page.page.locator(".file-key-previous")).to_contain_text(
        "00.00 start.data"
    )
    expect(plot_page.page.locator(".file-key").first).to_contain_text(
        "00.01 sweep.data"
    )


def test_the_previous_file_can_be_hidden_and_shown(plot_page, rig):
    rig.get("/scribe/next_file", title="sweep")
    key = plot_page.page.locator(".file-key-previous")
    key.wait_for()

    key.click()
    expect(key).to_have_attribute("aria-pressed", "false")
    plot_page.page.wait_for_function(
        "window.pyacquisition.plot.data[1][0].length === 0"
    )

    key.click()
    expect(key).to_have_attribute("aria-pressed", "true")
    plot_page.page.wait_for_function("window.pyacquisition.plot.data[1][0].length > 0")


def test_there_is_no_previous_file_key_before_a_new_file(plot_page):
    expect(plot_page.page.locator(".file-key-previous")).to_have_count(0)


# -------------------------------------------------------------- theme and speed
def test_the_plot_takes_the_colours_of_the_theme(plot_page):
    plot_page.page.emulate_media(color_scheme="light")
    plot_page.page.wait_for_function(
        "document.documentElement.dataset.theme === 'light'"
    )
    plot_page.page.wait_for_timeout(200)
    light = plot(plot_page.page, "u.series[2].stroke()")

    plot_page.page.get_by_role("button", name="Switch to the dark theme").click()
    plot_page.page.wait_for_function(
        f"window.pyacquisition.plot.series[2].stroke() !== {json.dumps(light)}"
    )

    assert light == "#2a78d6"
    assert plot(plot_page.page, "u.series[2].stroke()") == "#3987e5"


def test_an_update_is_quick(plot_page):
    plot_page.page.wait_for_timeout(1000)
    times = plot_page.page.evaluate("Array.from(window.pyacquisition.plotTimes)")

    assert times and sorted(times)[len(times) // 2] < 50


# -------------------------------------------------------------- drawing, alone
def draw(page, expression):
    return page.evaluate(f"import('/ui/js/plot/draw.js').then(d => {expression})")


def test_the_extent_skips_nan(page):
    assert draw(page.page, "d.extent([new Float64Array([NaN, 3, -1, NaN])])") == [-1, 3]
    assert draw(page.page, "d.extent([new Float64Array([NaN])])") is None


def test_a_flat_line_gets_a_band_around_it(page):
    assert draw(page.page, "d.padded([5, 5])") == [4.5, 5.5]
    assert draw(page.page, "d.padded([0, 0])") == [-1, 1]
    assert draw(page.page, "d.padded(null)") == [0, 1]


def test_ascending_ignores_nan(page):
    assert draw(page.page, "d.ascending(new Float64Array([1, NaN, 2, 2, 3]))") is True
    assert draw(page.page, "d.ascending(new Float64Array([1, 3, 2]))") is False


@pytest.mark.parametrize(
    "ticks, labels",
    [
        ([0, 5, 10, 15], ["0", "5", "10", "15"]),
        ([19.992, 19.994, 19.996], ["19.992", "19.994", "19.996"]),
        (
            [-5e-6, 0, 5e-6, 1e-5, 1.5e-5],
            ["-5.0e-6", "0", "5.0e-6", "1.0e-5", "1.5e-5"],
        ),
        ([0, 2e6, 4e6], ["0", "2e+6", "4e+6"]),
        # A step of 2.5 needs a decimal, though it is between 1 and 10.
        ([0, 2.5, 5, 7.5, 10], ["0.0", "2.5", "5.0", "7.5", "10.0"]),
        ([0, 0.25, 0.5], ["0.00", "0.25", "0.50"]),
        ([1e-5, 1.25e-5, 1.5e-5], ["1.00e-5", "1.25e-5", "1.50e-5"]),
    ],
)
def test_tick_labels_share_one_style(page, ticks, labels):
    assert draw(page.page, f"d.tickLabels({json.dumps(ticks)})") == labels
