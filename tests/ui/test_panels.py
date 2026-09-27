"""Several plot panels (milestone 6)."""

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
        self.add_measurement(Measurement("y", lambda: 100 * math.sin(clock.time())))


@pytest.fixture
def rig(tmp_path):
    running = Running(Rig, tmp_path, measurement_period=0.05)
    yield running
    running.stop()


@pytest.fixture
def plots_page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function(
        "window.pyacquisition?.plot && window.pyacquisition.store.current.rows > 40",
        timeout=15000,
    )
    yield page
    assert page.errors == [], f"the page logged errors: {page.errors}"


def panels(page):
    return page.locator(".plot-panel")


def add(page, count=1):
    for _ in range(count):
        before = panels(page).count()
        page.get_by_role("button", name="+ Add plot").click()
        expect(panels(page)).to_have_count(before + 1)
    page.wait_for_function(
        f"(window.pyacquisition.plots || []).filter(Boolean).length === {panels(page).count()}"
    )


def plot(page, index, expression):
    return page.evaluate(
        f"(() => {{ const u = window.pyacquisition.plots[{index}]; return {expression}; }})()"
    )


def x_range(page, index):
    return plot(page, index, "[u.scales.x.min, u.scales.x.max]")


def y_range(page, index):
    return plot(page, index, "[u.scales.y.min, u.scales.y.max]")


def box_zoom(page, index, start=(0.2, 0.2), end=(0.6, 0.8)):
    box = panels(page).nth(index).locator(".u-over").bounding_box()
    def at(f):
        return box["x"] + f[0] * box["width"], box["y"] + f[1] * box["height"]

    page.mouse.move(*at(start))
    page.mouse.down()
    page.mouse.move(*at(end), steps=6)
    page.mouse.up()


def boxes(page):
    return [panels(page).nth(i).bounding_box() for i in range(panels(page).count())]


# -------------------------------------------------------------- the grid
def test_there_is_one_plot_to_start_with(plots_page):
    page = plots_page.page
    expect(panels(page)).to_have_count(1)
    expect(page.get_by_role("button", name="Remove this plot")).to_have_count(0)
    expect(page.get_by_role("button", name="Link x-axes")).to_have_count(0)


def test_two_plots_sit_side_by_side(plots_page):
    page = plots_page.page
    add(page)

    first, second = boxes(page)
    assert first["y"] == pytest.approx(second["y"], abs=2)
    assert second["x"] > first["x"] + first["width"] - 2
    assert first["width"] == pytest.approx(second["width"], abs=3)


def test_the_last_of_three_plots_spans_its_row(plots_page):
    page = plots_page.page
    add(page, 2)

    first, second, third = boxes(page)
    assert third["y"] > first["y"] + first["height"] - 2
    assert third["width"] == pytest.approx(first["width"] + second["width"], abs=4)


def test_four_plots_make_a_two_by_two_grid(plots_page):
    page = plots_page.page
    add(page, 3)

    a, b, c, d = boxes(page)
    assert a["y"] == pytest.approx(b["y"], abs=2) and c["y"] == pytest.approx(
        d["y"], abs=2
    )
    assert a["x"] == pytest.approx(c["x"], abs=2) and b["x"] == pytest.approx(
        d["x"], abs=2
    )


def test_there_are_at_most_six_plots(plots_page):
    page = plots_page.page
    add(page, 5)

    expect(page.get_by_role("button", name="+ Add plot")).to_be_disabled()
    expect(page.get_by_role("button", name="Duplicate this plot")).to_have_count(0)


def test_a_new_plot_shows_a_column_no_plot_shows_yet(plots_page):
    page = plots_page.page
    add(page, 2)

    labels = [plot(page, i, "u.axes[1].label") for i in range(3)]
    assert labels == ["T (K)", "x (V)", "y"]


def test_a_plot_can_be_removed(plots_page):
    page = plots_page.page
    add(page)

    panels(page).nth(0).get_by_role("button", name="Remove this plot").click()

    expect(panels(page)).to_have_count(1)
    page.wait_for_function("window.pyacquisition.plots[0]?.axes[1].label === 'x (V)'")


def test_a_plot_can_be_duplicated_and_then_changed_on_its_own(plots_page):
    page = plots_page.page
    panels(page).nth(0).get_by_role("button", name="Duplicate this plot").click()
    expect(panels(page)).to_have_count(2)
    page.wait_for_function("window.pyacquisition.plots[1]?.axes[1].label === 'T (K)'")

    panels(page).nth(1).locator(".series-add").select_option("x")

    page.wait_for_function(
        "window.pyacquisition.plots[1].axes[1].label === 'T (K), x (V)'"
    )
    assert plot(page, 0, "u.axes[1].label") == "T (K)"


# -------------------------------------------------------------- each on its own
def test_each_plot_has_its_own_x(plots_page):
    page = plots_page.page
    add(page)

    panels(page).nth(1).locator(".picker select").select_option("T")

    page.wait_for_function("window.pyacquisition.plots[1].axes[0].label === 'T (K)'")
    assert plot(page, 0, "u.axes[0].label") == "time (s)"


def test_each_plot_zooms_and_pauses_on_its_own(plots_page):
    page = plots_page.page
    add(page)

    box_zoom(page, 0)

    expect(panels(page).nth(0).locator(".autoscale-off")).to_be_visible()
    expect(panels(page).nth(1).locator(".autoscale-off")).to_have_count(0)
    held = x_range(page, 0)
    following = x_range(page, 1)[1]
    page.wait_for_timeout(500)
    assert x_range(page, 0) == held
    assert x_range(page, 1)[1] > following


# -------------------------------------------------------------- linked x axes
def test_linked_plots_zoom_their_x_axes_together(plots_page):
    page = plots_page.page
    add(page)
    page.get_by_role("button", name="Link x-axes").click()

    box_zoom(page, 0)

    page.wait_for_function(
        "window.pyacquisition.plots[1].scales.x.min === window.pyacquisition.plots[0].scales.x.min"
    )
    assert x_range(page, 1) == x_range(page, 0)
    # Each fits its own y to what is in the range: x (volts) is not T (kelvin).
    assert y_range(page, 1) != y_range(page, 0)
    in_view = plot(
        page,
        1,
        "(() => { const [xs, ys] = u.data[2]; return Array.from(ys).filter((v, i) =>"
        " xs[i] >= u.scales.x.min && xs[i] <= u.scales.x.max); })()",
    )
    low, high = y_range(page, 1)
    assert low <= min(in_view) and max(in_view) <= high
    # Only its x is held: its y still scales to the data in the range.
    expect(panels(page).nth(1).locator(".autoscale-state")).to_have_text(
        "Autoscale off: x"
    )
    expect(panels(page).nth(0).locator(".autoscale-state")).to_have_text(
        "Autoscale off: x, y"
    )


def test_autoscale_in_one_linked_plot_frees_them_all(plots_page):
    page = plots_page.page
    add(page)
    page.get_by_role("button", name="Link x-axes").click()
    box_zoom(page, 0)
    expect(panels(page).nth(1).locator(".autoscale-off")).to_be_visible()

    panels(page).nth(1).locator(".autoscale-button").click()

    expect(page.locator(".autoscale-off")).to_have_count(0)


def test_plots_against_another_x_are_not_linked(plots_page):
    page = plots_page.page
    add(page)
    panels(page).nth(1).locator(".picker select").select_option("T")
    page.wait_for_function("window.pyacquisition.plots[1]?.axes[0].label === 'T (K)'")
    page.get_by_role("button", name="Link x-axes").click()

    box_zoom(page, 0)

    expect(panels(page).nth(0).locator(".autoscale-off")).to_be_visible()
    expect(panels(page).nth(1).locator(".autoscale-off")).to_have_count(0)


def test_unlinked_plots_zoom_alone(plots_page):
    page = plots_page.page
    add(page)
    before = x_range(page, 1)

    box_zoom(page, 0)

    expect(panels(page).nth(1).locator(".autoscale-off")).to_have_count(0)
    assert x_range(page, 1)[1] >= before[1]


# -------------------------------------------------------------- shared, and kept
def test_the_previous_file_is_shown_or_hidden_in_every_plot(plots_page, rig):
    page = plots_page.page
    add(page)
    rig.get("/scribe/next_file", title="sweep")
    key = page.locator(".file-key-previous")
    key.wait_for()
    page.wait_for_function(
        "window.pyacquisition.plots.every(u => !u || u.data[1][0].length > 0)"
    )

    key.click()

    page.wait_for_function(
        "window.pyacquisition.plots.every(u => !u || u.data[1][0].length === 0)"
    )


def test_the_plots_are_remembered_for_the_session(plots_page):
    page = plots_page.page
    add(page, 2)
    panels(page).nth(2).locator(".picker select").select_option("T")
    page.wait_for_function("window.pyacquisition.plots[2]?.axes[0].label === 'T (K)'")

    page.reload()
    # The units come from the experiment a moment after the plots are first made.
    page.wait_for_function(
        "(window.pyacquisition?.plots || []).filter(Boolean).length === 3"
        " && window.pyacquisition.plots[2].axes[0].label === 'T (K)'"
        " && window.pyacquisition.plots[0].axes[1].label === 'T (K)'",
        timeout=15000,
    )

    assert [plot(page, i, "u.axes[1].label") for i in range(3)] == [
        "T (K)",
        "x (V)",
        "y",
    ]
    assert plot(page, 2, "u.axes[0].label") == "T (K)"


def test_four_plots_stream_without_lag(plots_page):
    page = plots_page.page
    add(page, 3)
    page.evaluate("window.pyacquisition.plotTimes.length = 0")
    rows = page.evaluate("window.pyacquisition.store.current.rows")

    page.wait_for_function(f"window.pyacquisition.store.current.rows > {rows + 20}")

    times = page.evaluate("Array.from(window.pyacquisition.plotTimes)")
    assert len(times) >= 20  # every plot kept updating
    assert sorted(times)[len(times) // 2] < 50
    # And every plot is showing the newest data.
    newest = page.evaluate("window.pyacquisition.store.latest.time")
    for i in range(4):
        assert x_range(page, i)[1] >= newest - 0.3


# -------------------------------------------------------------- the grid's shape
@pytest.mark.parametrize(
    "count, shape",
    [
        (1, {"columns": 1, "rows": 1, "lastSpan": 1}),
        (2, {"columns": 2, "rows": 1, "lastSpan": 1}),
        (3, {"columns": 2, "rows": 2, "lastSpan": 2}),
        (4, {"columns": 2, "rows": 2, "lastSpan": 1}),
        (5, {"columns": 3, "rows": 2, "lastSpan": 2}),
        (6, {"columns": 3, "rows": 2, "lastSpan": 1}),
    ],
)
def test_the_grid_is_as_square_as_it_can_be(page, count, shape):
    assert (
        page.page.evaluate(
            f"import('/ui/js/plot/area.js').then(a => a.gridShape({count}))"
        )
        == shape
    )
