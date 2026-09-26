"""Dragging queued tasks to new places, and duplicating them (milestone 11)."""

import re

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from test_queue import QueueRig, queue
from ui_helpers import Page, Running


@pytest.fixture
def rig(tmp_path):
    running = Running(QueueRig, tmp_path)
    running.get("/task_manager/pause")  # so queued tasks wait
    for seconds in (1, 2, 3, 4, 5):
        queue(running, seconds=seconds)
    yield running
    running.stop()


def served(rig):
    """The seconds of each queued WaitFor, in the server's order."""
    state = rig.get("/managers/state").json()["data"]["main"]
    return [t["parameters"]["seconds"] for t in state["queue"]]


def shown(page):
    return [
        int(text)
        for text in page.page.locator(
            ".manager[data-manager='main'] .queued-task .task-parameter:has(dt:text-is('seconds')) dd"
        ).all_inner_texts()
    ]


def open_queue(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    page.page.get_by_role("tab", name="Queue").click()
    # A tall dock, so every row is in view.
    handle = page.page.locator(".dock-resize")
    handle.focus()
    page.page.keyboard.press("End")
    expect(page.page.locator(".manager[data-manager='main'] .queued-task")).to_have_count(5)
    return page


def rows(page):
    return page.page.locator(".manager[data-manager='main'] .queued-task")


def drag(page, row, to_y, release=True):
    """Drags a row by its handle to a height on the page."""
    box = rows(page).nth(row).locator(".drag-handle").bounding_box()
    page.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.page.mouse.down()
    page.page.mouse.move(box["x"] + box["width"] / 2, to_y, steps=8)
    if release:
        page.page.mouse.up()


def top_of(page, row):
    return rows(page).nth(row).bounding_box()["y"]


def bottom_of(page, row):
    box = rows(page).nth(row).bounding_box()
    return box["y"] + box["height"]


# -------------------------------------------------------------- dragging
def test_the_last_task_can_be_dragged_to_the_front(context, rig):
    page = open_queue(context, rig)

    drag(page, 4, top_of(page, 0) + 2)

    expect(rows(page).first).to_contain_text("5")
    assert served(rig) == [5, 1, 2, 3, 4]
    assert shown(page) == served(rig)
    assert page.errors == []


def test_the_first_task_can_be_dragged_to_the_end(context, rig):
    page = open_queue(context, rig)

    drag(page, 0, bottom_of(page, 4) - 2)

    expect(rows(page).last).to_contain_text("1")
    assert served(rig) == [2, 3, 4, 5, 1]


def test_a_task_can_be_dragged_into_the_middle(context, rig):
    page = open_queue(context, rig)

    # Just below the middle of the fourth row: between the fourth and fifth.
    box = rows(page).nth(3).bounding_box()
    drag(page, 0, box["y"] + box["height"] * 0.75)

    expect(rows(page).nth(3)).to_contain_text("1")
    assert served(rig) == [2, 3, 4, 1, 5]


def test_a_line_shows_where_it_will_go_and_escape_puts_it_back(context, rig):
    page = open_queue(context, rig)

    drag(page, 4, top_of(page, 1) + 2, release=False)

    expect(rows(page).nth(1)).to_have_class(re.compile("drop-before"))
    expect(rows(page).nth(4)).to_have_class(re.compile("dragged"))
    page.page.keyboard.press("Escape")
    page.page.mouse.up()

    expect(rows(page).locator(".drop-before, .dragged")).to_have_count(0)
    expect(page.page.locator(".queued-task.drop-before")).to_have_count(0)
    assert served(rig) == [1, 2, 3, 4, 5]


def test_dropping_where_it_started_changes_nothing(context, rig):
    page = open_queue(context, rig)

    drag(page, 2, top_of(page, 2) + 4)

    page.page.wait_for_timeout(300)
    assert served(rig) == [1, 2, 3, 4, 5]


# -------------------------------------------------------------- the keyboard
def test_the_handle_moves_its_task_with_the_arrow_keys(context, rig):
    page = open_queue(context, rig)
    handle = rows(page).nth(1).locator(".drag-handle")
    handle.focus()

    page.page.keyboard.press("ArrowDown")
    expect(rows(page).nth(2)).to_contain_text("2")
    # The focus goes with the task.
    expect(rows(page).nth(2).locator(".drag-handle")).to_be_focused()

    page.page.keyboard.press("Home")
    expect(rows(page).first).to_contain_text("2")
    page.page.keyboard.press("End")
    expect(rows(page).last).to_contain_text("2")

    page.page.wait_for_timeout(300)
    assert served(rig) == [1, 3, 4, 5, 2]


# -------------------------------------------------------------- duplicating
def test_a_duplicate_goes_straight_after_the_original(context, rig):
    page = open_queue(context, rig)

    rows(page).nth(1).get_by_role("button", name="Duplicate WaitFor").click()

    expect(rows(page)).to_have_count(6)
    assert served(rig) == [1, 2, 2, 3, 4, 5]
    ids = [row.get_attribute("data-task-id") for row in rows(page).all()]
    assert ids[1] != ids[2]  # two tasks, not one shown twice


def test_the_running_task_can_be_queued_again_to_run_next(context, rig):
    page = open_queue(context, rig)
    # A long one at the front, to be running while this looks at it.
    queue(rig, seconds=300)
    last = rig.get("/managers/state").json()["data"]["main"]["queue"][-1]["id"]
    rig.get("/task_manager/place_queued_task", task_id=last, index=0)
    rig.get("/task_manager/resume")
    running = page.page.get_by_label("Running task")
    expect(running).to_contain_text("300")

    running.get_by_role("button", name="Queue WaitFor again").click()

    expect(rows(page).first).to_contain_text("300")
    assert served(rig) == [300, 1, 2, 3, 4, 5]
