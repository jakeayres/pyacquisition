"""Saving a queue as a sequence and loading it again, from the Queue tab
(milestone 13)."""

import json

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from test_queue import QueueRig, queue
from ui_helpers import Page, Running


def start(root, paused=True):
    running = Running(QueueRig, root)
    if paused:
        running.get("/task_manager/pause")  # so queued tasks wait
    return running


@pytest.fixture
def rig(tmp_path):
    running = start(tmp_path)
    yield running
    running.stop()


def open_queue(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    page.page.get_by_role("tab", name="Queue").click()
    return page


def main(page):
    return page.page.get_by_role("region", name="Main", exact=True)


def queued(rig, manager="main"):
    state = rig.get("/managers/state").json()["data"][manager]
    return [(t["name"], t["parameters"]) for t in state["queue"]]


def saved(rig):
    return {s["name"]: s["tasks"] for s in rig.get("/sequences").json()["data"]}


def save_as(page, name):
    main(page).get_by_role("button", name="Save Main as a sequence").click()
    dialog = page.page.get_by_role("dialog", name="Save the Main queue as a sequence")
    dialog.get_by_role("textbox", name="Name").fill(name)
    dialog.get_by_role("button", name="Save").click()
    return dialog


# -------------------------------------------------------------- saving
def test_the_queue_is_saved_as_a_sequence(context, rig, tmp_path):
    queue(rig, seconds=10)
    queue(rig, task="explode", message="later")
    page = open_queue(context, rig)
    expect(main(page).locator(".queued-task")).to_have_count(2)

    dialog = save_as(page, "cooldown")

    expect(dialog).to_have_count(0)
    assert saved(rig) == {"cooldown": ["WaitFor", "Explode"]}
    assert (tmp_path / "sequences" / "cooldown.json").is_file()
    assert page.errors == []


def test_a_name_that_is_taken_can_be_replaced(context, rig):
    queue(rig, seconds=10)
    rig.get("/sequences/save", name="mine")
    queue(rig, seconds=20)
    page = open_queue(context, rig)

    dialog = save_as(page, "mine")

    expect(dialog.get_by_role("alert")).to_contain_text("There is already a sequence called mine.")
    assert saved(rig) == {"mine": ["WaitFor"]}  # not yet
    dialog.get_by_role("button", name="Replace it").click()

    expect(dialog).to_have_count(0)
    assert saved(rig) == {"mine": ["WaitFor", "WaitFor"]}


def test_the_running_task_can_be_left_out(context, tmp_path):
    rig = start(tmp_path, paused=False)
    try:
        queue(rig, seconds=300)  # runs
        page = open_queue(context, rig)
        expect(main(page).get_by_label("Running task")).to_be_visible()
        rig.get("/task_manager/pause")
        queue(rig, seconds=5)
        expect(main(page).locator(".queued-task")).to_have_count(1)

        main(page).get_by_role("button", name="Save Main as a sequence").click()
        dialog = page.page.get_by_role("dialog", name="Save the Main queue as a sequence")
        box = dialog.get_by_role("checkbox", name="Start with the running task (WaitFor)")
        expect(box).to_be_checked()
        box.uncheck()
        dialog.get_by_role("textbox", name="Name").fill("just the rest")
        dialog.get_by_role("button", name="Save").click()

        expect(dialog).to_have_count(0)
        assert saved(rig) == {"just the rest": ["WaitFor"]}
    finally:
        rig.stop()


def test_a_bad_name_is_explained(context, rig):
    queue(rig, seconds=10)
    page = open_queue(context, rig)

    dialog = save_as(page, "a/b")

    expect(dialog.get_by_role("alert")).to_contain_text("can't contain /")
    assert saved(rig) == {}


# -------------------------------------------------------------- loading
def test_a_sequence_saved_in_one_run_loads_in_the_next(context, tmp_path):
    first = start(tmp_path)
    queue(first, minutes=2)
    queue(first, task="explode", message="the magnet quenched")
    queue(first, manager="main", task="newfile", file_name="cooldown", increment_block=True)
    before = queued(first)
    first.get("/sequences/save", name="overnight")
    first.stop()

    second = start(tmp_path)
    try:
        page = open_queue(context, second)
        main(page).get_by_role("button", name="Load a sequence onto Main").click()
        dialog = page.page.get_by_role("dialog", name="Load a sequence onto Main")
        item = dialog.locator(".sequence[data-sequence='overnight']")
        expect(item).to_contain_text("3 tasks")
        expect(item.locator(".sequence-tasks li")).to_have_text(["WaitFor", "Explode", "NewFile"])

        item.get_by_role("button", name="Load overnight").click()

        expect(dialog).to_have_count(0)
        expect(main(page).locator(".queued-task")).to_have_count(3)
        assert queued(second) == before
    finally:
        second.stop()


def test_a_sequence_loads_onto_another_task_manager(context, rig):
    queue(rig, seconds=10)
    rig.get("/sequences/save", name="short")
    rig.get("/managers/control/pause")
    page = open_queue(context, rig)
    control = page.page.get_by_role("region", name="Control", exact=True)

    control.get_by_role("button", name="Load a sequence onto Control").click()
    page.page.get_by_role("dialog").get_by_role("button", name="Load short").click()

    expect(control.locator(".queued-task")).to_have_count(1)
    assert queued(rig, "control") == [("WaitFor", {"hours": 0, "minutes": 0, "seconds": 10})]


def test_a_sequence_that_cannot_be_loaded_says_why_and_queues_nothing(context, rig, tmp_path):
    folder = tmp_path / "sequences"
    folder.mkdir()
    (folder / "old.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {"task": "waitfor", "name": "WaitFor", "parameters": {"seconds": 1}},
                    {"task": "retired", "name": "Retired", "parameters": {}},
                ]
            }
        )
    )
    page = open_queue(context, rig)

    main(page).get_by_role("button", name="Load a sequence onto Main").click()
    dialog = page.page.get_by_role("dialog")
    dialog.get_by_role("button", name="Load old").click()

    expect(dialog.get_by_role("alert")).to_contain_text("2. Retired: can't be queued here")
    assert queued(rig) == []


def test_a_sequence_can_be_deleted_after_asking(context, rig):
    queue(rig, seconds=10)
    rig.get("/sequences/save", name="spare")
    page = open_queue(context, rig)
    main(page).get_by_role("button", name="Load a sequence onto Main").click()
    dialog = page.page.get_by_role("dialog")

    dialog.get_by_role("button", name="Delete spare").click()
    expect(dialog).to_contain_text("Delete it?")
    dialog.get_by_role("button", name="Delete", exact=True).click()

    expect(dialog).to_contain_text("No sequences yet.")
    assert saved(rig) == {}


def test_with_no_sequences_the_list_says_so(context, rig):
    page = open_queue(context, rig)

    main(page).get_by_role("button", name="Load a sequence onto Main").click()

    expect(page.page.get_by_role("dialog")).to_contain_text("No sequences yet.")
    page.page.keyboard.press("Escape")
    expect(page.page.get_by_role("dialog")).to_have_count(0)
