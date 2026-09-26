"""Each quantity has one colour, the same in the Values tab and in every plot."""

import math

import pytest

pytest.importorskip("playwright")

from ui_helpers import Page, Running
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
        self.add_measurement(Measurement("y", lambda: math.sin(clock.time())))
        for n in range(6):  # ten quantities in all: more than the eight colours
            self.add_measurement(Measurement(f"c{n}", lambda n=n: n + 1.0))
        self.add_measurement(Measurement("time_ms", clock.timestamp_ms))


@pytest.fixture
def rig(tmp_path):
    running = Running(Rig, tmp_path, measurement_period=0.05)
    yield running
    running.stop()


@pytest.fixture
def colour_page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function(
        "window.pyacquisition?.plot && window.pyacquisition.store.current.rows > 10"
    )
    page.page.locator(".value-tile").first.wait_for()
    yield page
    assert page.errors == [], f"the page logged errors: {page.errors}"


def rgb(hex_colour):
    n = int(hex_colour.lstrip("#"), 16)
    return f"rgb({(n >> 16) & 255}, {(n >> 8) & 255}, {n & 255})"


def token(page, name):
    return rgb(
        page.evaluate(
            f"getComputedStyle(document.documentElement).getPropertyValue('{name}').trim()"
        )
    )


def tile_colour(page, column):
    return page.locator(f".value-tile[data-column='{column}'] .value-key").evaluate(
        "e => getComputedStyle(e).backgroundColor"
    )


def spark_colour(page, column):
    return page.locator(f".value-tile[data-column='{column}'] .spark path").evaluate(
        "e => getComputedStyle(e).stroke"
    )


def plot_colour(page, index=0, series=2):
    return rgb(
        page.evaluate(f"window.pyacquisition.plots[{index}].series[{series}].stroke()")
    )


# -------------------------------------------------------------- the Values tab
def test_each_tile_has_its_quantitys_colour_in_order(colour_page):
    page = colour_page.page
    assert tile_colour(page, "T") == token(page, "--series-1")
    assert tile_colour(page, "x") == token(page, "--series-2")
    assert tile_colour(page, "y") == token(page, "--series-3")
    assert spark_colour(page, "x") == token(page, "--series-2")


def test_time_columns_are_neutral(colour_page):
    page = colour_page.page
    assert tile_colour(page, "time") == token(page, "--series-other")
    assert tile_colour(page, "time_ms") == token(page, "--series-other")


def test_quantities_past_the_eighth_are_neutral(colour_page):
    page = colour_page.page
    assert tile_colour(page, "c4") == token(page, "--series-8")  # the eighth
    assert tile_colour(page, "c5") == token(page, "--series-other")


def test_the_values_stay_in_the_text_colour(colour_page):
    page = colour_page.page
    number = page.locator(".value-tile[data-column='x'] .value-number")
    assert number.evaluate("e => getComputedStyle(e).color") == token(page, "--text")


# -------------------------------------------------------------- the plots match
def test_a_plotted_quantity_has_the_colour_of_its_tile(colour_page):
    page = colour_page.page
    page.locator(".series-add").select_option("x")
    page.get_by_role("button", name="Remove T", exact=True).click()
    page.wait_for_function("window.pyacquisition.plot.axes[1].label === 'x (V)'")

    assert plot_colour(page) == tile_colour(page, "x")
    chip = page.locator(".series-chip .key-line").first
    assert chip.evaluate("e => getComputedStyle(e).backgroundColor") == tile_colour(
        page, "x"
    )


def test_the_order_columns_are_added_in_does_not_change_their_colours(colour_page):
    page = colour_page.page
    page.locator(".series-add").select_option("y")
    page.locator(".series-add").select_option("x")
    page.wait_for_function("window.pyacquisition.plot.series.length === 7")

    # Plotted T, y, x: series 2, 4 and 6 are their current-file lines.
    assert plot_colour(page, series=2) == tile_colour(page, "T")
    assert plot_colour(page, series=4) == tile_colour(page, "y")
    assert plot_colour(page, series=6) == tile_colour(page, "x")


def test_a_quantity_has_the_same_colour_in_every_plot(colour_page):
    page = colour_page.page
    page.get_by_role("button", name="+ Add plot").click()  # plots x
    page.wait_for_function("window.pyacquisition.plots[1]?.axes[1].label === 'x (V)'")
    second = page.locator(".plot-panel").nth(1)
    second.locator(".series-add").select_option("T")
    page.wait_for_function("window.pyacquisition.plots[1].series.length === 5")

    # T is first in one plot and second in the other, and blue in both.
    assert plot_colour(page, 0, 2) == plot_colour(page, 1, 4) == tile_colour(page, "T")
    assert plot_colour(page, 1, 2) == tile_colour(page, "x")


def test_the_previous_file_is_the_same_colour_faded(colour_page, rig):
    page = colour_page.page
    rig.get("/scribe/next_file", title="sweep")
    page.locator(".file-key-previous").wait_for()

    faded = page.evaluate("window.pyacquisition.plot.series[1].stroke()")
    red, green, blue = tile_colour(page, "T")[4:-1].split(", ")
    assert faded.startswith(f"rgba({red}, {green}, {blue}, ")


def test_the_colours_follow_the_theme(colour_page):
    page = colour_page.page
    page.emulate_media(color_scheme="light")
    page.wait_for_function("document.documentElement.dataset.theme === 'light'")
    light = tile_colour(page, "T")

    page.get_by_role("button", name="Switch to the dark theme").click()

    expect(page.locator(".value-tile[data-column='T'] .value-key")).not_to_have_css(
        "background-color", light
    )
    page.wait_for_function(
        "window.pyacquisition.plot.series[2].stroke() === "
        "getComputedStyle(document.documentElement).getPropertyValue('--series-1').trim()"
    )
    assert plot_colour(page) == tile_colour(page, "T")


# -------------------------------------------------------------- the rule itself
@pytest.mark.parametrize(
    "name, is_time",
    [
        ("time", True),
        ("time_ms", True),
        ("timestamp", True),
        ("timestamp_ms", True),
        ("elapsed_time", True),
        ("Time", True),
        ("T", False),
        ("timer_count", False),
        ("lifetime", False),
    ],
)
def test_which_columns_count_as_times(page, name, is_time):
    assert (
        page.page.evaluate(
            f"import('/ui/js/colours.js').then(c => c.isTimeColumn('{name}'))"
        )
        is is_time
    )


def test_colours_are_given_in_order_skipping_times(page):
    slots = page.page.evaluate(
        "import('/ui/js/colours.js').then(c => Object.fromEntries("
        "c.colourSlots(['time', 'a', 'b', 'time_ms', 'c']).entries()))"
    )
    assert slots == {"time": None, "a": 1, "b": 2, "time_ms": None, "c": 3}
