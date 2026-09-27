"""The Ctrl+K palette with arguments typed on its search line (the command
palette's milestone 1): `wait 0 5` and Enter queues a five-minute wait, and
what is wrong shows before anything is sent."""

import re

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from test_queue import QueueRig
from ui_helpers import Page, Running


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    running = Running(QueueRig, tmp_path_factory.mktemp("palette"), measurement_period=0.05)
    # Held, so queued tasks wait where they can be looked at.
    running.get("/task_manager/pause")
    running.get("/managers/control/pause")
    yield running
    running.stop()


@pytest.fixture
def page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.current?.rows > 5", timeout=15000)
    yield page
    rig.get("/task_manager/clear_tasks")
    rig.get("/managers/control/clear_tasks")
    assert page.errors == [], f"the page logged errors: {page.errors}"


def palette(page):
    return page.page.get_by_role("dialog", name="Queue a task or call an instrument")


def open_palette(page):
    page.page.keyboard.press("Control+k")
    dialog = palette(page)
    expect(dialog.get_by_role("option").first).to_be_visible()
    return dialog


def type_line(page, text):
    """Opens the palette and types `text` on its search line: the dialog, and
    the search box."""
    dialog = open_palette(page)
    search = dialog.get_by_role("searchbox")
    search.press_sequentially(text)
    return dialog, search


def field(dialog, name):
    return dialog.locator(f".form-field[data-field='{name}']")


def queued(rig, manager="main"):
    return [
        (task["name"], task["parameters"])
        for task in rig.get("/managers/state").json()["data"][manager]["queue"]
    ]


def test_typed_arguments_fill_the_form_and_enter_queues_it(page, rig):
    dialog, search = type_line(page, "wait 0 5")

    expect(dialog.locator(".task-form-title")).to_have_text("WaitFor")
    expect(field(dialog, "hours").locator("input")).to_have_value("0")
    expect(field(dialog, "minutes").locator("input")).to_have_value("5")
    expect(dialog.locator(".palette-args")).to_contain_text("hours=0")
    expect(dialog.locator(".palette-args")).to_contain_text("✓ Enter to queue")

    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("WaitFor", {"hours": 0, "minutes": 5, "seconds": 0})]


def test_a_named_argument_and_a_positional_one(page, rig):
    _, search = type_line(page, "wait seconds=30 0")

    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("WaitFor", {"hours": 0, "minutes": 0, "seconds": 30})]


def test_words_after_the_search_are_text(page, rig):
    _, search = type_line(page, "new file cold")

    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("NewFile", {"file_name": "cold", "increment_block": False})]


def test_tab_locks_in_the_item_so_every_word_after_it_is_an_argument(page, rig):
    dialog, search = type_line(page, "newf")

    search.press("Tab")
    expect(search).to_have_value("NewFile ")
    expect(search).to_be_focused()
    search.press_sequentially("cold run")
    expect(field(dialog, "file_name").locator("input")).to_have_value("cold run")
    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("NewFile", {"file_name": "cold run", "increment_block": False})]


def test_quotes_hold_spaces(page, rig):
    _, search = type_line(page, 'new file "cold run"')

    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("NewFile", {"file_name": "cold run", "increment_block": False})]


@pytest.mark.parametrize(
    "text, where, problem",
    [
        ("wait abc", "hours", "Nothing left here takes abc"),
        ("wait 1 2 3 4", "seconds", "4 has nowhere to go"),
    ],
)
def test_a_problem_shows_before_enter_and_enter_goes_to_it(page, rig, text, where, problem):
    dialog, search = type_line(page, text)

    expect(dialog.locator(".palette-arg-problem")).to_contain_text(problem)
    expect(field(dialog, where).locator(".form-error")).to_contain_text(problem)
    expect(dialog.locator(".palette-arg-ready")).to_have_count(0)

    search.press("Enter")

    expect(field(dialog, where).locator("input")).to_be_focused()
    expect(dialog).to_be_visible()
    assert queued(rig) == []


def test_the_problem_goes_once_the_field_is_changed(page, rig):
    dialog, search = type_line(page, "wait abc")
    search.press("Enter")
    hours = field(dialog, "hours")

    hours.locator("input").fill("1")

    expect(hours.locator(".form-error")).to_have_count(0)
    hours.locator("input").press("Enter")
    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("WaitFor", {"hours": 1, "minutes": 0, "seconds": 0})]


def test_an_instrument_called_inline_answers_and_the_palette_stays_open(page):
    dialog, search = type_line(page, "clock start_timer lap")
    expect(dialog.locator(".task-form-title")).to_have_text("clock.start_timer")
    search.press("Enter")
    expect(dialog.locator(".palette-answer")).to_be_visible()

    search.fill("")
    search.press_sequentially("clock read_timer lap")
    expect(dialog.locator(".palette-args")).to_contain_text("✓ Enter to read")
    search.press("Enter")

    answer = dialog.locator(".palette-answer .result-value")
    expect(answer).to_have_text(re.compile(r"^\d+(\.\d+)?(e-?\d+)?$"))
    expect(dialog).to_be_visible()


def test_an_item_with_inputs_and_nothing_typed_after_it_goes_to_its_form(page, rig):
    dialog, search = type_line(page, "new file")
    expect(dialog.locator(".palette-args")).to_have_count(0)

    search.press("Enter")

    expect(field(dialog, "file_name").locator("input")).to_be_focused()
    assert queued(rig) == []


def test_an_item_without_inputs_runs_on_enter(page):
    dialog, search = type_line(page, "clock time")
    expect(dialog.locator(".task-form-title")).to_have_text("clock.time")

    search.press("Enter")

    expect(dialog.locator(".palette-answer .result-value")).to_have_text(re.compile(r"^\d"))


def test_an_item_whose_inputs_all_have_defaults_still_goes_to_its_form(page, rig):
    dialog, search = type_line(page, "explode control")

    search.press("Enter")

    expect(field(dialog, "message").locator("input")).to_be_focused()
    assert queued(rig, "control") == []


def test_the_arrow_keys_pick_another_match_for_the_arguments(page, rig):
    dialog, search = type_line(page, "wait 0 5")
    expect(dialog.locator(".task-form-title")).to_have_text("WaitFor")

    search.press("ArrowDown")

    expect(dialog.locator(".task-form-title")).to_have_text("WaitUntil")


# -------------------------------------------------------------- queueing a call
def test_shift_enter_queues_an_instrument_call(page, rig):
    dialog, search = type_line(page, "clock start_timer lap")
    expect(dialog.locator(".palette-arg-ready")).to_have_text("✓ Enter to send · Shift+Enter to queue")

    search.press("Shift+Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("clock.start_timer", {"name": "lap"})]


def test_add_to_queue_on_the_form_queues_it(page, rig):
    dialog, _ = type_line(page, "clock read_timer lap")

    dialog.get_by_role("button", name="Add to queue").click()

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("clock.read_timer", {"name": "lap"})]


def test_a_call_can_be_queued_on_another_task_manager(page, rig):
    dialog, _ = type_line(page, "clock time")
    expect(dialog.get_by_label("Queue on")).to_have_value("main")

    dialog.get_by_label("Queue on").select_option("control")
    dialog.get_by_role("button", name="Add to queue").click()

    expect(palette(page)).to_have_count(0)
    assert queued(rig, "control") == [("clock.time", None)]
    assert queued(rig) == []


def test_a_task_has_no_second_button(page):
    dialog, _ = type_line(page, "wait")

    expect(dialog.locator(".task-form-title")).to_have_text("WaitFor")
    expect(dialog.get_by_role("button", name="Add to queue")).to_have_count(1)  # its own
    expect(dialog.get_by_label("Queue on")).to_have_count(0)


def test_a_queued_query_runs_and_its_value_is_the_last_result(page, rig):
    for line in ("clock start_timer lap", "clock read_timer lap"):
        _, search = type_line(page, line)
        search.press("Shift+Enter")
        expect(palette(page)).to_have_count(0)
    assert [name for name, _ in queued(rig)] == ["clock.start_timer", "clock.read_timer"]

    rig.get("/task_manager/resume")
    try:
        page.page.get_by_role("tab", name="Queue").click()
        expect(page.page.locator(".queue-last").first).to_contain_text(
            re.compile(r"clock\.read_timer completed → \d")
        )
    finally:
        rig.get("/task_manager/pause")


def test_a_queue_holding_a_call_is_saved_and_loaded_again(page, rig):
    _, search = type_line(page, "clock start_timer lap")
    search.press("Shift+Enter")
    assert rig.get("/sequences/save", name="with a call", manager="main").status_code == 200
    rig.get("/task_manager/clear_tasks")
    assert queued(rig) == []

    assert rig.get("/sequences/load", name="with a call", manager="main").status_code == 200

    assert queued(rig) == [("clock.start_timer", {"name": "lap"})]
    rig.get("/sequences/delete", name="with a call")
