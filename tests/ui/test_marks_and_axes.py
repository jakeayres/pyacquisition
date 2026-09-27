"""Lines or points, fixed axis limits, and panning with the right button."""

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
        "window.pyacquisition?.plot && window.pyacquisition.store.current.rows > 40",
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


def open_axes(page):
    page.get_by_role("button", name="Axis settings").click()
    menu = page.get_by_role("dialog", name="Axis settings")
    expect(menu).to_be_visible()
    return menu


def fix(page, axis, low, high):
    menu = open_axes(page)
    row = menu.locator(".axes-row").nth(0 if axis == "x" else 1)
    row.get_by_label("Auto").uncheck()
    menu.get_by_label(f"{axis.upper()} minimum").fill(str(low))
    menu.get_by_label(f"{axis.upper()} maximum").fill(str(high))
    menu.get_by_role("button", name="Apply").click()
    expect(menu).to_have_count(0)


# -------------------------------------------------------------- lines or points
def test_lines_are_drawn_to_start_with(plot_page):
    page = plot_page.page
    expect(page.get_by_role("button", name="Lines")).to_have_attribute(
        "aria-pressed", "true"
    )
    assert plot(page, "u._marks") == "lines"


@pytest.mark.parametrize("marks, label", [("points", "Points"), ("both", "Both")])
def test_the_data_can_be_drawn_as_points_or_both(plot_page, marks, label):
    page = plot_page.page
    page.get_by_role("button", name=label).click()

    page.wait_for_function(f"window.pyacquisition.plot._marks === '{marks}'")
    expect(page.get_by_role("button", name=label)).to_have_attribute(
        "aria-pressed", "true"
    )
    # The dots are filled in the column's colour.
    assert plot(page, "u.series[2].fill()") == plot(page, "u.series[2].stroke()")


def test_the_choice_of_marks_is_per_plot_and_kept(plot_page):
    page = plot_page.page
    page.get_by_role("button", name="+ Add plot").click()
    page.wait_for_function(
        "(window.pyacquisition.plots || []).filter(Boolean).length === 2"
    )
    page.locator(".plot-panel").nth(1).get_by_role("button", name="Points").click()
    page.wait_for_function("window.pyacquisition.plots[1]._marks === 'points'")

    assert page.evaluate("window.pyacquisition.plots[0]._marks") == "lines"
    page.reload()
    page.wait_for_function(
        "window.pyacquisition?.plots?.[1]?._marks === 'points'", timeout=15000
    )


# -------------------------------------------------------------- fixed limits
def test_the_y_limits_can_be_fixed(plot_page):
    page = plot_page.page
    fix(page, "y", 3.5, 6.5)

    page.wait_for_function("window.pyacquisition.plot.scales.y.min === 3.5")
    assert y_range(page) == [3.5, 6.5]
    expect(page.get_by_role("button", name="Axis settings")).to_have_attribute(
        "aria-pressed", "true"
    )
    # x still follows the data.
    before = x_range(page)[1]
    page.wait_for_timeout(500)
    assert x_range(page)[1] > before
    assert y_range(page) == [3.5, 6.5]


def test_fixing_x_alone_fits_y_to_what_is_within_it(plot_page):
    page = plot_page.page
    fix(page, "x", 0, 1)

    page.wait_for_function("window.pyacquisition.plot.scales.x.min === 0")
    assert x_range(page) == [0, 1]
    inside = plot(
        page,
        "(() => { const [xs, ys] = u.data[2]; return Array.from(ys).filter((v, i) =>"
        " xs[i] >= 0 && xs[i] <= 1); })()",
    )
    low, high = y_range(page)
    assert low <= min(inside) and max(inside) <= high
    assert high - low < (max(inside) - min(inside)) * 1.5 + 1e-9


def test_auto_goes_back_to_scaling_to_the_data(plot_page):
    page = plot_page.page
    fix(page, "y", 0, 100)
    page.wait_for_function("window.pyacquisition.plot.scales.y.max === 100")

    menu = open_axes(page)
    menu.get_by_role("button", name="Autoscale both").click()

    page.wait_for_function("window.pyacquisition.plot.scales.y.max < 10")
    expect(page.get_by_role("button", name="Axis settings")).to_have_attribute(
        "aria-pressed", "false"
    )


def test_the_menu_starts_from_what_the_axes_show(plot_page):
    page = plot_page.page
    # Hold the axes still (a tiny scroll), so new data cannot rescale them
    # between reading them here and the menu reading them.
    box = page.locator(".u-over").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.wheel(1, 1)
    expect(page.locator(".autoscale-off")).to_be_visible()
    low, high = y_range(page)

    menu = open_axes(page)

    assert float(menu.get_by_label("Y minimum").input_value()) == pytest.approx(
        low, rel=1e-4
    )
    assert float(menu.get_by_label("Y maximum").input_value()) == pytest.approx(
        high, rel=1e-4
    )
    expect(menu.get_by_label("Y minimum")).to_be_disabled()  # not fixed, so "Auto"


def test_use_current_view_fixes_what_a_zoom_shows(plot_page):
    page = plot_page.page
    drag(page, (0.2, 0.2), (0.6, 0.8))
    zoomed_x, zoomed_y = x_range(page), y_range(page)

    menu = open_axes(page)
    menu.get_by_role("button", name="Use current view").click()
    menu.get_by_role("button", name="Apply").click()

    expect(page.get_by_role("button", name="Axis settings")).to_have_attribute(
        "aria-pressed", "true"
    )
    assert x_range(page) == pytest.approx(zoomed_x, rel=1e-4)
    assert y_range(page) == pytest.approx(zoomed_y, rel=1e-4)
    expect(page.locator(".autoscale-off")).to_contain_text("Autoscale off: x, y")


@pytest.mark.parametrize(
    "low, high, message",
    [
        ("", "1", "give a number"),
        ("abc", "1", "give a number"),
        ("2", "1", "below the maximum"),
        ("1", "1", "below the maximum"),
    ],
)
def test_limits_that_make_no_sense_are_refused(plot_page, low, high, message):
    page = plot_page.page
    menu = open_axes(page)
    menu.locator(".axes-row").nth(1).get_by_label("Auto").uncheck()
    menu.get_by_label("Y minimum").fill(low)
    menu.get_by_label("Y maximum").fill(high)
    menu.get_by_role("button", name="Apply").click()

    expect(menu.get_by_role("alert")).to_contain_text(message)
    expect(menu).to_be_visible()


def test_a_log_axis_needs_a_minimum_above_zero(plot_page):
    page = plot_page.page
    menu = open_axes(page)
    menu.get_by_label("Log y").check()
    menu.locator(".axes-row").nth(1).get_by_label("Auto").uncheck()
    menu.get_by_label("Y minimum").fill("0")
    menu.get_by_label("Y maximum").fill("10")
    menu.get_by_role("button", name="Apply").click()

    expect(menu.get_by_role("alert")).to_contain_text("above zero")


def test_escape_closes_the_menu_without_changing_anything(plot_page):
    page = plot_page.page
    menu = open_axes(page)
    menu.locator(".axes-row").nth(1).get_by_label("Auto").uncheck()
    page.keyboard.press("Escape")

    expect(menu).to_have_count(0)
    expect(page.get_by_role("button", name="Axis settings")).to_have_attribute(
        "aria-pressed", "false"
    )


@pytest.mark.parametrize("axis, shown", [("x", "x"), ("y", "y")])
def test_a_fixed_axis_shows_autoscale_off_for_that_axis(plot_page, axis, shown):
    page = plot_page.page
    fix(page, axis, 0, 10)

    expect(page.locator(".autoscale-off")).to_have_text(
        f"Autoscale off: {shown}Autoscale"
    )


def test_autoscale_clears_a_zoom_and_fixed_limits_together(plot_page):
    page = plot_page.page
    fix(page, "y", 3.5, 6.5)
    page.wait_for_function("window.pyacquisition.plot.scales.y.min === 3.5")
    drag(page, (0.2, 0.2), (0.6, 0.8))

    page.get_by_role("button", name="Autoscale", exact=True).click()

    expect(page.locator(".autoscale-off")).to_have_count(0)
    expect(page.get_by_role("button", name="Axis settings")).to_have_attribute(
        "aria-pressed", "false"
    )
    page.wait_for_function("window.pyacquisition.plot.scales.y.min > 3.5")


def test_the_log_scales_are_in_the_axis_settings_not_the_toolbar(plot_page):
    page = plot_page.page
    expect(
        page.locator(".plot-toolbar").get_by_role("button", name="Log y")
    ).to_have_count(0)

    menu = open_axes(page)

    expect(menu.get_by_label("Log x")).not_to_be_checked()
    expect(menu.get_by_label("Log y")).not_to_be_checked()


def test_log_and_limits_are_applied_together(plot_page):
    page = plot_page.page
    menu = open_axes(page)
    menu.get_by_label("Log y").check()
    menu.locator(".axes-row").nth(1).get_by_label("Auto").uncheck()
    menu.get_by_label("Y minimum").fill("1")
    menu.get_by_label("Y maximum").fill("100")
    menu.get_by_role("button", name="Apply").click()

    page.wait_for_function(
        "window.pyacquisition.plot.scales.y.distr === 3"
        " && window.pyacquisition.plot.scales.y.min === 1"
    )
    assert y_range(page) == [1, 100]
    expect(page.get_by_role("button", name="Axis settings")).to_have_attribute(
        "title", "Axis settings: y fixed, log y"
    )


def test_nothing_changes_until_apply(plot_page):
    page = plot_page.page
    menu = open_axes(page)
    menu.get_by_label("Log y").check()
    page.wait_for_timeout(300)

    assert plot(page, "u.scales.y.distr") == 1
    page.keyboard.press("Escape")
    assert plot(page, "u.scales.y.distr") == 1


def test_limits_that_do_not_suit_a_new_log_axis_are_refused(plot_page):
    page = plot_page.page
    fix(page, "y", -1, 1)
    page.wait_for_function("window.pyacquisition.plot.scales.y.min === -1")

    menu = open_axes(page)
    menu.get_by_label("Log y").check()
    menu.get_by_role("button", name="Apply").click()

    expect(menu.get_by_role("alert")).to_contain_text("above zero")
    assert plot(page, "u.scales.y.distr") == 1  # left as it was


def test_the_axis_settings_icon_shows_when_something_is_set(plot_page):
    page = plot_page.page
    button = page.get_by_role("button", name="Axis settings")
    expect(button.locator(".axes-badge")).to_have_count(0)
    expect(button).to_have_attribute("title", "Axis settings")

    set_log(page, "x")

    expect(button.locator(".axes-badge")).to_have_count(1)
    expect(button).to_have_attribute("title", "Axis settings: log x")


def test_fixed_limits_are_kept_for_the_session(plot_page):
    page = plot_page.page
    fix(page, "y", 3.5, 6.5)
    page.wait_for_function("window.pyacquisition.plot.scales.y.min === 3.5")

    page.reload()

    page.wait_for_function(
        "window.pyacquisition?.plot?.scales.y.min === 3.5", timeout=15000
    )


# -------------------------------------------------------------- the right button
def drag(page, start, end, button="left"):
    box = page.locator(".u-over").bounding_box()
    at = lambda f: (box["x"] + f[0] * box["width"], box["y"] + f[1] * box["height"])
    page.mouse.move(*at(start))
    page.mouse.down(button=button)
    page.mouse.move(*at(end), steps=6)
    page.mouse.up(button=button)


def test_dragging_with_the_right_button_pans(plot_page):
    page = plot_page.page
    before = x_range(page)

    drag(page, (0.6, 0.5), (0.4, 0.5), button="right")

    expect(page.locator(".autoscale-off")).to_be_visible()
    after = x_range(page)
    width = before[1] - before[0]
    assert after[1] - after[0] == pytest.approx(width, rel=0.1)
    assert after[0] - before[0] == pytest.approx(0.2 * width, rel=0.25)


def test_the_browser_menu_does_not_open_over_the_plot(plot_page):
    blocked = plot_page.page.evaluate(
        "(() => { const e = new MouseEvent('contextmenu', {bubbles: true, cancelable: true});"
        " document.querySelector('.u-over').dispatchEvent(e); return e.defaultPrevented; })()"
    )
    assert blocked is True


# -------------------------------------------------------------- drawing, alone
def test_points_are_drawn_once_per_cell(page):
    dots = page.page.evaluate(
        "import('/ui/js/plot/draw.js').then(d => {"
        " const xs = new Float64Array(10000).map((_, i) => i % 100);"  # 100 distinct points
        " const ys = new Float64Array(10000).map((_, i) => i % 100);"
        " const area = {left: 0, top: 0, width: 1000, height: 1000};"
        " return d.pointPath(xs, ys, area, {min: 0, max: 99}, {min: 0, max: 99}, 4).dots; })"
    )
    assert dots == 100


def test_points_outside_the_plot_or_missing_are_left_out(page):
    dots = page.page.evaluate(
        "import('/ui/js/plot/draw.js').then(d => d.pointPath("
        "new Float64Array([0.5, 5, NaN, 0.2]), new Float64Array([0.5, 0.5, 0.5, NaN]),"
        " {left: 0, top: 0, width: 100, height: 100}, {min: 0, max: 1}, {min: 0, max: 1}, 2).dots)"
    )
    assert dots == 1


def check_limits(page, draft):
    return page.page.evaluate(
        f"import('/ui/js/plot/panel.js').then(p => p.checkLimits({draft}))"
    )


def test_the_limits_are_checked(page):
    assert check_limits(
        page,
        "{x: {auto: true, min: '', max: '', log: false},"
        " y: {auto: false, min: '1', max: '5', log: false}}",
    ) == {"limits": {"x": None, "y": {"min": 1, "max": 5}}}


def test_the_limits_are_checked_against_the_log_setting_given_with_them(page):
    draft = "{{x: {{auto: true, min: '', max: '', log: false}}, y: {{auto: false, min: '0', max: '5', log: {}}}}}"
    assert "error" in check_limits(page, draft.format("true"))
    assert "limits" in check_limits(page, draft.format("false"))


@pytest.mark.parametrize(
    "low, high, ticks",
    [
        (19.99, 20.011, [19.99, 19.995, 20, 20.005, 20.01]),  # under a decade: even
        (1, 100, [1, 2, 5, 10, 20, 50, 100]),  # a few: 1, 2 and 5 of each
        (1e-6, 1e6, [1e-6, 1e-4, 0.01, 1, 100, 1e4, 1e6]),  # many: every other power
    ],
)
def test_log_ticks(page, low, high, ticks):
    got = page.page.evaluate(
        f"import('/ui/js/plot/draw.js').then(d => d.logTicks({low}, {high}).ticks)"
    )
    assert got == pytest.approx(ticks)
