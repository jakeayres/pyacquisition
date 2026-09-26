"""The app shell: top bar, plot area, dock and theme (milestone 1)."""

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect


def dock_height(page) -> float:
    return page.locator(".dock").bounding_box()["height"]


def css_pixels(page, name) -> float:
    return page.evaluate(
        "name => parseFloat(getComputedStyle(document.documentElement)"
        ".getPropertyValue(name))",
        name,
    )


def drag_dock_edge(page, to_y):
    handle = page.locator(".dock-resize").bounding_box()
    x, y = handle["x"] + 200, handle["y"] + handle["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, to_y, steps=5)
    page.mouse.up()


def reload(page):
    page.reload()
    page.get_by_role("status").filter(has_text="Connected").wait_for()


# -------------------------------------------------------------- loading
def test_the_page_loads_and_connects_without_errors(page):
    # The fixture waits for "Connected", and fails the test on any console error.
    expect(page.page).to_have_title("SmokeExperiment · PyAcquisition")


def test_the_top_bar_names_the_experiment(page):
    expect(page.page.locator(".brand-name")).to_have_text("SmokeExperiment")


def test_the_layout_fills_the_window(page):
    topbar = page.page.locator(".topbar").bounding_box()
    plots = page.page.locator(".plot-area").bounding_box()
    dock = page.page.locator(".dock").bounding_box()

    assert topbar["y"] == 0
    assert plots["y"] == pytest.approx(topbar["y"] + topbar["height"], abs=1)
    assert dock["y"] == pytest.approx(plots["y"] + plots["height"], abs=1)
    assert dock["y"] + dock["height"] == pytest.approx(800, abs=1)


# -------------------------------------------------------------- the dock
def test_the_dock_has_four_tabs_with_values_open(page):
    expect(page.page.get_by_role("tab")).to_have_text(
        ["Values", "Queue", "Instruments", "Logs"]
    )
    expect(page.page.get_by_role("tab", name="Values")).to_have_attribute(
        "aria-selected", "true"
    )


def test_a_tab_shows_its_panel(page):
    page.page.get_by_role("tab", name="Logs").click()

    panel = page.page.get_by_role("tabpanel", name="Logs")
    expect(panel.get_by_role("list", name="Log messages")).to_be_visible()


def test_arrow_keys_move_between_tabs(page):
    page.page.get_by_role("tab", name="Values").focus()
    page.page.keyboard.press("ArrowRight")

    queue = page.page.get_by_role("tab", name="Queue")
    expect(queue).to_have_attribute("aria-selected", "true")
    expect(queue).to_be_focused()


def test_the_collapse_button_hides_and_shows_the_dock(page):
    open_height = dock_height(page.page)

    page.page.get_by_role("button", name="Hide the dock").click()

    expect(page.page.get_by_role("tabpanel")).to_be_hidden()
    tab_strip = css_pixels(page.page, "--dock-tabs-height") + 1  # and its border
    assert dock_height(page.page) == pytest.approx(tab_strip, abs=1)

    page.page.get_by_role("button", name="Show the dock").click()

    expect(page.page.get_by_role("tabpanel")).to_be_visible()
    assert dock_height(page.page) == pytest.approx(open_height, abs=1)


def test_clicking_the_open_tab_collapses_the_dock(page):
    page.page.get_by_role("tab", name="Values").click()

    expect(page.page.get_by_role("tabpanel")).to_be_hidden()

    page.page.get_by_role("tab", name="Queue").click()

    expect(
        page.page.get_by_role("tabpanel").get_by_role("region", name="Task queue")
    ).to_be_visible()


def test_dragging_the_top_edge_resizes_the_dock(page):
    before = dock_height(page.page)
    handle = page.page.locator(".dock-resize").bounding_box()

    drag_dock_edge(page.page, handle["y"] + handle["height"] / 2 - 100)

    assert dock_height(page.page) == pytest.approx(before + 100, abs=2)


def test_the_dock_never_leaves_the_plots_less_than_their_minimum(page):
    drag_dock_edge(page.page, 0)

    plots = page.page.locator(".plot-area").bounding_box()
    assert plots["height"] == pytest.approx(
        css_pixels(page.page, "--plot-min-height"), abs=1
    )


def test_dragging_the_dock_most_of_the_way_down_collapses_it(page):
    drag_dock_edge(page.page, 799)

    expect(page.page.get_by_role("tabpanel")).to_be_hidden()


def test_the_arrow_keys_resize_the_dock(page):
    before = dock_height(page.page)
    page.page.locator(".dock-resize").focus()
    page.page.keyboard.press("ArrowUp")
    page.page.keyboard.press("ArrowUp")

    assert dock_height(page.page) == pytest.approx(before + 32, abs=1)


def test_a_shorter_window_shrinks_the_dock_to_fit(page):
    page.page.locator(".dock-resize").focus()
    page.page.keyboard.press("End")  # as tall as it can be

    page.page.set_viewport_size({"width": 1280, "height": 600})

    plots = page.page.locator(".plot-area")
    minimum = css_pixels(page.page, "--plot-min-height")
    page.page.wait_for_function(
        "min => document.querySelector('.plot-area').offsetHeight >= min - 1",
        arg=minimum,
    )
    assert plots.bounding_box()["height"] == pytest.approx(minimum, abs=1)


def test_the_dock_is_remembered_for_the_session(page):
    page.page.get_by_role("tab", name="Instruments").click()
    page.page.locator(".dock-resize").focus()
    page.page.keyboard.press("Shift+ArrowUp")
    height = dock_height(page.page)

    reload(page.page)

    expect(page.page.get_by_role("tab", name="Instruments")).to_have_attribute(
        "aria-selected", "true"
    )
    assert dock_height(page.page) == pytest.approx(height, abs=1)


def test_a_collapsed_dock_is_remembered_for_the_session(page):
    page.page.get_by_role("button", name="Hide the dock").click()

    reload(page.page)

    expect(page.page.get_by_role("tabpanel")).to_be_hidden()


# -------------------------------------------------------------- the theme
def theme(page) -> str:
    return page.evaluate("document.documentElement.dataset.theme")


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_theme_follows_the_os(context, server, scheme):
    page = context.new_page()
    page.emulate_media(color_scheme=scheme)
    page.goto(f"{server}/")

    assert theme(page) == scheme


def test_the_theme_follows_the_os_when_it_changes(page):
    page.page.emulate_media(color_scheme="light")
    page.page.wait_for_function("document.documentElement.dataset.theme === 'light'")

    page.page.emulate_media(color_scheme="dark")
    page.page.wait_for_function("document.documentElement.dataset.theme === 'dark'")


def test_the_toggle_switches_the_theme_and_is_remembered(page):
    page.page.emulate_media(color_scheme="light")
    page.page.get_by_role("button", name="Switch to the dark theme").click()

    expect(page.page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.page.locator("body")).to_have_css(
        "background-color",
        "rgb(14, 16, 20)",  # --bg in the dark theme
    )

    reload(page.page)
    assert theme(page.page) == "dark"


def test_a_chosen_theme_stays_when_the_os_changes(page):
    page.page.emulate_media(color_scheme="light")
    page.page.get_by_role("button", name="Switch to the dark theme").click()

    page.page.emulate_media(color_scheme="dark")
    page.page.emulate_media(color_scheme="light")

    expect(page.page.locator("html")).to_have_attribute("data-theme", "dark")
