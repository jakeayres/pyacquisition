"""The layout comes back on the next run: the plots, the dock and the theme
(milestone 15)."""

import json
import re

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from test_values import Rig
from ui_helpers import Page, Running

pytestmark = pytest.mark.real_layout


def open_page(browser_context, rig):
    page = Page(browser_context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    return page


def new_window(browser):
    """A new window, as the app opens on each run: nothing in its session."""
    from ui_helpers import VIEWPORT

    return browser.new_context(viewport=VIEWPORT, reduced_motion="reduce")


def saved_layout(rig):
    return rig.get("/experiment/layout").json()["data"]


def wait_saved(rig, condition, timeout=5.0):
    import time

    end = time.monotonic() + timeout
    while time.monotonic() < end:
        layout = saved_layout(rig)
        if condition(layout):
            return layout
        time.sleep(0.1)
    raise AssertionError(f"the layout never got there: {json.dumps(saved_layout(rig))}")


def test_the_layout_comes_back_after_a_restart(browser, tmp_path):
    first = Running(Rig, tmp_path)
    context = new_window(browser)
    try:
        page = open_page(context, first).page
        # Two plots, the second of "wave" against time on a log x axis...
        page.get_by_role("button", name="Add plot").click()
        expect(page.locator(".plot-panel")).to_have_count(2)
        # ...the Logs tab open, the dock taller, and the dark theme.
        page.get_by_role("tab", name="Logs").click()
        page.locator(".dock-resize").focus()
        page.keyboard.press("ArrowUp")
        page.keyboard.press("ArrowUp")
        page.get_by_role("button", name=re.compile("Switch to the (dark|light) theme")).click()
        theme = page.evaluate("document.documentElement.dataset.theme")
        height = page.locator(".dock").evaluate("d => d.getBoundingClientRect().height")
        wait_saved(first, lambda layout: layout.get("dock", {}).get("active") == "logs"
                   and len(layout.get("plots", {}).get("panels", [])) == 2
                   and layout.get("theme") == theme)
    finally:
        context.close()
        first.stop()

    # The next run, in a new window.
    second = Running(Rig, tmp_path, port=first.port)
    context = new_window(browser)
    try:
        page = open_page(context, second).page
        expect(page.locator(".plot-panel")).to_have_count(2)
        expect(page.get_by_role("tab", name="Logs")).to_have_attribute("aria-selected", "true")
        assert page.evaluate("document.documentElement.dataset.theme") == theme
        assert page.locator(".dock").evaluate(
            "d => d.getBoundingClientRect().height"
        ) == pytest.approx(height, abs=1)
    finally:
        context.close()
        second.stop()


def test_a_column_that_is_gone_is_dropped_quietly(browser, tmp_path):
    rig = Running(Rig, tmp_path)
    context = new_window(browser)
    try:
        rig_layout = {
            "plots": {
                "panels": [
                    {"id": 1, "x": "time", "series": [{"name": "retired"}, {"name": "wave"}]},
                    {"id": 2, "x": "gone", "series": [{"name": "also gone"}]},
                ],
                "link": False,
                "showPrevious": True,
            }
        }
        import requests

        requests.put(f"{rig.address}/experiment/layout", json=rig_layout, timeout=5)
        page = open_page(context, rig)

        panels = page.page.locator(".plot-panel")
        expect(panels).to_have_count(2)
        # The first keeps what still exists; the second falls back to defaults.
        expect(panels.first.locator(".series-chip")).to_have_count(1)
        expect(panels.first.locator(".series-chip")).to_contain_text("wave")
        expect(panels.nth(1).locator(".series-chip")).to_have_count(1)
        assert page.errors == []
    finally:
        context.close()
        rig.stop()


def test_this_sessions_layout_wins_over_the_saved_one_on_a_reload(browser, tmp_path):
    rig = Running(Rig, tmp_path)
    context = new_window(browser)
    try:
        import requests

        requests.put(
            f"{rig.address}/experiment/layout",
            json={"dock": {"active": "queue", "collapsed": False, "height": 300}},
            timeout=5,
        )
        page = open_page(context, rig).page
        expect(page.get_by_role("tab", name="Queue")).to_have_attribute("aria-selected", "true")

        page.get_by_role("tab", name="Instruments").click()
        page.reload()
        page.wait_for_function("window.pyacquisition?.store?.status === 'live'")

        expect(page.get_by_role("tab", name="Instruments")).to_have_attribute("aria-selected", "true")
    finally:
        context.close()
        rig.stop()


def test_the_palettes_recent_runs_come_back_after_a_restart(browser, tmp_path):
    first = Running(Rig, tmp_path)
    context = new_window(browser)
    try:
        page = open_page(context, first).page
        page.keyboard.press("Control+k")
        search = page.get_by_role("searchbox", name="Search tasks, instruments and actions")
        search.press_sequentially("wait 0 5")
        expect(page.locator(".task-form-title")).to_have_text("WaitFor")
        search.press("Enter")
        expect(page.get_by_role("dialog", name="Command palette")).to_have_count(0)
        wait_saved(first, lambda layout: [r["label"] for r in layout.get("recents", [])] == ["WaitFor"])
    finally:
        context.close()
        first.stop()

    second = Running(Rig, tmp_path, port=first.port)
    context = new_window(browser)
    try:
        page = open_page(context, second).page
        page.keyboard.press("Control+k")
        recent = page.locator(".palette-recent").first
        expect(recent).to_contain_text("WaitFor")
        expect(recent).to_contain_text("hours=0, minutes=5")
    finally:
        context.close()
        second.stop()


def test_a_trace_panel_comes_back_and_an_older_layout_loads_as_plots(browser, tmp_path):
    from test_trace_panel import TraceRig

    first = Running(TraceRig, tmp_path)
    context = new_window(browser)
    try:
        page = open_page(context, first).page
        page.get_by_role("button", name="Add plot").click()
        page.get_by_role("menuitem", name="Trace: spectrum").click()
        panel = page.locator(".trace-panel")
        panel.get_by_label("Earlier traces shown behind").select_option("5")
        wait_saved(first, lambda layout: any(
            p.get("kind") == "trace" and p.get("overlay") == 5
            for p in layout.get("plots", {}).get("panels", [])))
    finally:
        context.close()
        first.stop()

    second = Running(TraceRig, tmp_path, port=first.port)
    context = new_window(browser)
    try:
        page = open_page(context, second)
        panel = page.page.locator(".trace-panel[data-trace='spectrum']")
        expect(panel).to_be_visible()
        expect(panel.get_by_label("Earlier traces shown behind")).to_have_value("5")
        expect(page.page.locator(".plot-panel")).to_have_count(2)

        # A layout from before panels had kinds: every panel is a plot.
        import requests

        older = {"plots": {"panels": [{"id": 1, "x": "time", "series": [{"name": "time"}]},
                                      {"id": 2, "x": "time", "series": [{"name": "spectrum_index"}]}],
                           "link": False, "showPrevious": True}}
        requests.put(f"{second.address}/experiment/layout", json=older, timeout=5)
    finally:
        context.close()
    context = new_window(browser)
    try:
        page = open_page(context, second)
        expect(page.page.locator(".plot-panel")).to_have_count(2)
        expect(page.page.locator(".trace-panel")).to_have_count(0)
        assert page.errors == []
    finally:
        context.close()
        second.stop()
