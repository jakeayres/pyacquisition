"""Keyboard shortcuts, and the Ctrl+K palette that queues a task or calls an
instrument (milestone 18). None of the single keys fire while typing."""

import re

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from test_queue import QueueRig
from ui_helpers import Page, Running


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    running = Running(QueueRig, tmp_path_factory.mktemp("shortcuts"), measurement_period=0.05)
    # Held, so queued tasks wait where they can be looked at.
    running.get("/task_manager/pause")
    running.get("/managers/control/pause")
    yield running
    running.stop()


@pytest.fixture
def page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function(
        "window.pyacquisition?.plot && window.pyacquisition.store.current.rows > 20",
        timeout=15000,
    )
    yield page
    rig.get("/task_manager/clear_tasks")
    rig.get("/managers/control/clear_tasks")
    assert page.errors == [], f"the page logged errors: {page.errors}"


COLLAPSED = re.compile(r"\bcollapsed\b")


def selected_tab(page):
    return page.page.locator(".dock-tab[aria-selected='true']")


def theme(page):
    return page.page.evaluate("document.documentElement.dataset.theme")


def x_range(page):
    return page.page.evaluate("(u => [u.scales.x.min, u.scales.x.max])(window.pyacquisition.plot)")


def rows(page):
    return page.page.evaluate("window.pyacquisition.store.current.rows")


def held(page):
    return page.page.locator(".autoscale-off")


def queue_of(rig, manager="main"):
    return rig.get("/managers/state").json()["data"][manager]["queue"]


def palette(page):
    return page.page.get_by_role("dialog", name="Command palette")


def open_palette(page):
    page.page.keyboard.press("Control+k")
    dialog = palette(page)
    expect(dialog.get_by_role("option").first).to_be_visible()
    return dialog


def field(dialog, name):
    return dialog.locator(f".form-field[data-field='{name}']")


# -------------------------------------------------------------- single keys
def test_the_number_keys_open_the_dock_tabs(page):
    for key, name in (("2", "Queue"), ("4", "Logs"), ("3", "Instruments"), ("1", "Values")):
        page.page.keyboard.press(key)
        expect(selected_tab(page)).to_have_text(name)


def test_a_number_key_shows_a_hidden_dock(page):
    page.page.get_by_role("button", name="Hide the dock").click()

    page.page.keyboard.press("2")

    expect(page.page.locator(".dock")).not_to_have_class(COLLAPSED)
    expect(selected_tab(page)).to_have_text("Queue")


def test_backtick_hides_and_shows_the_dock(page):
    dock = page.page.locator(".dock")

    page.page.keyboard.press("`")
    expect(dock).to_have_class(COLLAPSED)
    page.page.keyboard.press("`")
    expect(dock).not_to_have_class(COLLAPSED)


def test_t_switches_the_theme(page):
    before = theme(page)

    page.page.keyboard.press("t")
    expect(page.page.locator("html")).not_to_have_attribute("data-theme", before)
    page.page.keyboard.press("Shift+T")
    expect(page.page.locator("html")).to_have_attribute("data-theme", before)


def test_space_holds_the_plot_and_lets_it_follow_again(page):
    page.page.keyboard.press(" ")
    expect(held(page)).to_contain_text("Autoscale off: x, y")
    view = x_range(page)
    now = rows(page)
    page.page.wait_for_function(f"window.pyacquisition.store.current.rows > {now + 10}")
    assert x_range(page) == view

    page.page.keyboard.press(" ")
    expect(held(page)).to_have_count(0)
    page.page.wait_for_function(
        f"window.pyacquisition.plot.scales.x.max > {view[1]}", timeout=5000
    )


def test_space_holds_every_plot(page):
    page.page.get_by_role("button", name="+ Add plot").click()
    expect(page.page.locator(".plot-panel")).to_have_count(2)
    page.page.locator("body").click(position={"x": 5, "y": 5})  # away from the button

    page.page.keyboard.press(" ")

    expect(held(page)).to_have_count(2)


def test_question_mark_lists_the_shortcuts(page):
    page.page.keyboard.press("?")

    help = page.page.get_by_role("dialog", name="Keyboard shortcuts")
    expect(help).to_be_visible()
    expect(help.locator(".shortcut")).to_have_count(6)
    expect(help).to_contain_text("Hide or show the dock")
    expect(help.locator(".shortcut").filter(has_text="Ctrl")).to_contain_text(
        "Search tasks, instruments and actions, to queue, call or run one"
    )
    page.page.keyboard.press("Escape")
    expect(help).to_have_count(0)

    page.page.keyboard.press("?")
    expect(help).to_be_visible()
    page.page.keyboard.press("?")
    expect(help).to_have_count(0)


def test_the_top_bar_button_lists_the_shortcuts_too(page):
    page.page.get_by_role("button", name="Keyboard shortcuts").click()

    expect(page.page.get_by_role("dialog", name="Keyboard shortcuts")).to_be_visible()


# -------------------------------------------------------------- not while typing
def test_no_shortcut_fires_while_typing_in_a_field(page):
    page.page.get_by_role("tab", name="Logs").click()
    search = page.page.get_by_role("searchbox", name="Search the log")
    before = theme(page)
    search.click()

    search.press_sequentially("12`t? 3")

    expect(search).to_have_value("12`t? 3")
    expect(selected_tab(page)).to_have_text("Logs")
    expect(page.page.locator(".dock")).not_to_have_class(COLLAPSED)
    assert theme(page) == before
    expect(page.page.get_by_role("dialog")).to_have_count(0)
    expect(held(page)).to_have_count(0)


def test_no_shortcut_fires_while_typing_in_a_form(page):
    dialog = open_palette(page)
    dialog.get_by_role("searchbox").fill("wait for")
    field(dialog, "seconds").locator("input").fill("")

    field(dialog, "seconds").locator("input").press_sequentially("1 2`")

    expect(field(dialog, "seconds").locator("input")).to_have_value("1 2`")
    expect(selected_tab(page)).to_have_text("Values")


def test_space_on_a_button_presses_it_rather_than_holding_the_plot(page):
    page.page.get_by_role("button", name="Hide the dock").focus()

    page.page.keyboard.press(" ")

    expect(page.page.get_by_role("button", name="Show the dock")).to_be_visible()
    expect(held(page)).to_have_count(0)


def test_the_single_keys_wait_while_a_dialog_is_open(page):
    page.page.keyboard.press("?")
    expect(page.page.get_by_role("dialog", name="Keyboard shortcuts")).to_be_visible()

    page.page.keyboard.press("2")
    page.page.keyboard.press("`")

    expect(selected_tab(page)).to_have_text("Values")
    expect(page.page.locator(".dock")).not_to_have_class(COLLAPSED)


# -------------------------------------------------------------- the palette
def test_ctrl_k_opens_the_palette_ready_to_search_even_from_a_field(page):
    page.page.get_by_role("tab", name="Logs").click()
    page.page.get_by_role("searchbox", name="Search the log").click()

    dialog = open_palette(page)

    expect(dialog.get_by_role("searchbox", name="Search tasks, instruments and actions")).to_be_focused()
    names = dialog.locator(".task-option-name").all_inner_texts()
    for name in ("WaitFor", "Explode", "clock.time", "clock.start_timer"):
        assert name in names


def test_escape_closes_the_palette_and_the_focus_goes_back(page):
    page.page.get_by_role("tab", name="Logs").click()
    search = page.page.get_by_role("searchbox", name="Search the log")
    search.click()
    open_palette(page)

    page.page.keyboard.press("Escape")

    expect(palette(page)).to_have_count(0)
    expect(search).to_be_focused()


def test_ctrl_k_again_closes_it(page):
    open_palette(page)

    page.page.keyboard.press("Control+k")

    expect(palette(page)).to_have_count(0)


def test_each_task_manager_offers_its_tasks(page):
    dialog = open_palette(page)

    dialog.get_by_role("searchbox").fill("explode")

    expect(dialog.locator(".palette-tag")).to_have_text(["Task · Main", "Task · Control"])


def test_a_task_is_searched_for_and_queued_from_the_keyboard(page, rig):
    dialog = open_palette(page)
    search = dialog.get_by_role("searchbox")
    search.fill("wait")
    expect(dialog.locator(".task-form-title")).to_have_text("WaitFor")
    search.press("ArrowDown")
    search.press("ArrowUp")
    search.press("Enter")
    hours = field(dialog, "hours").locator("input")
    expect(hours).to_be_focused()

    field(dialog, "seconds").locator("input").fill("30")
    field(dialog, "seconds").locator("input").press("Enter")

    expect(palette(page)).to_have_count(0)
    (task,) = queue_of(rig)
    assert task["name"] == "WaitFor"
    assert task["parameters"] == {"hours": 0, "minutes": 0, "seconds": 30}


def test_a_task_goes_to_the_manager_picked(page, rig):
    dialog = open_palette(page)
    dialog.get_by_role("searchbox").fill("explode control")
    expect(dialog.locator(".palette-tag")).to_have_text(["Task · Control"])

    dialog.get_by_role("button", name="Add to queue").click()

    expect(palette(page)).to_have_count(0)
    assert [t["name"] for t in queue_of(rig, "control")] == ["Explode"]
    assert queue_of(rig) == []


def test_an_instrument_is_called_and_its_answer_shown(page):
    dialog = open_palette(page)
    dialog.get_by_role("searchbox").fill("clock time")
    expect(dialog.locator(".task-form-title")).to_have_text("clock.time")
    expect(dialog.locator(".palette-tag").first).to_have_text("Query")

    dialog.get_by_role("button", name="Read").click()

    answer = dialog.locator(".palette-answer .result-value")
    expect(answer).to_have_text(re.compile(r"^\d+(\.\d+)?$"))
    expect(dialog).to_be_visible()  # still open, to read
    value = answer.inner_text()

    # And it is among the instrument's results.
    page.page.keyboard.press("Escape")
    page.page.get_by_role("tab", name="Instruments").click()
    expect(page.page.locator(".result").first).to_contain_text("time")
    expect(page.page.locator(".result .result-value").first).to_have_text(value)


def test_a_failed_call_says_why_in_the_form(page):
    dialog = open_palette(page)
    dialog.get_by_role("searchbox").fill("read_timer")

    field(dialog, "name").locator("input").fill("never started")
    dialog.get_by_role("button", name="Read").click()

    expect(dialog.locator(".form-error")).to_be_visible()
    expect(dialog.locator(".palette-answer")).to_have_count(0)
    page.errors = [e for e in page.errors if "500" not in e]  # the failed call


def test_nothing_matching_says_so(page):
    dialog = open_palette(page)

    dialog.get_by_role("searchbox").fill("zzzz")

    expect(dialog).to_contain_text("Nothing matches.")
    expect(dialog.locator(".endpoint-form")).to_have_count(0)
