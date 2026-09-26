"""The experiment's controls in the top bar: the data file, the measurements
and stopping (milestone 8)."""

import itertools
import re
import time

import pytest

pytest.importorskip("playwright")

from ui_helpers import Page, Running, SmokeExperiment
from playwright.sync_api import expect

_titles = itertools.count()


def unique(title):
    return f"{title} {next(_titles)}"


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    running = Running(SmokeExperiment, tmp_path_factory.mktemp("controls"))
    yield running
    running.stop()


def open_page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function(
        "window.pyacquisition?.store?.status === 'live'", timeout=15000
    )
    return page


def file_button(page):
    return page.page.get_by_role("button", name="Data file")


def rack_button(page):
    return page.page.get_by_role("button", name="Measurements", exact=True)


def scribe(rig):
    return rig.get("/scribe/state").json()["data"]


def wait_for(condition, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return
        time.sleep(0.05)
    raise AssertionError("the condition never held")


# -------------------------------------------------------------- the data file
def test_the_top_bar_shows_the_data_file(context, rig):
    page = open_page(context, rig)

    expect(file_button(page)).to_have_text(scribe(rig)["file"])


def test_a_file_started_elsewhere_shows_at_once(context, rig):
    page = open_page(context, rig)
    title = unique("elsewhere")

    rig.get("/scribe/next_file", title=title)

    expect(file_button(page)).to_contain_text(title)


def test_a_new_file_is_started_from_the_top_bar(context, rig):
    page = open_page(context, rig)
    title = unique("sweep up")
    expected = scribe(rig)["next_step"].format(title=title)

    file_button(page).click()
    page.page.get_by_role("textbox", name="Title").fill(title)
    menu = page.page.get_by_role("dialog", name="Data file")
    expect(menu).to_contain_text(f"Next file: {expected}")
    menu.get_by_role("button", name="Start new file").click()

    expect(menu).to_have_count(0)
    expect(file_button(page)).to_have_text(expected)
    directory = scribe(rig)["directory"]
    from pathlib import Path

    wait_for(lambda: (Path(directory) / expected).exists())


def test_a_new_block_can_be_started(context, rig):
    page = open_page(context, rig)
    title = unique("cooldown")
    expected = scribe(rig)["next_block"].format(title=title)

    file_button(page).click()
    page.page.get_by_role("textbox", name="Title").fill(title)
    page.page.get_by_role("checkbox", name="Start a new block").check()
    page.page.get_by_role("textbox", name="Title").press("Enter")

    expect(file_button(page)).to_have_text(expected)
    assert re.match(r"^\d\d\.00 ", expected)


def test_a_title_that_cannot_be_a_file_name_is_explained(context, rig):
    page = open_page(context, rig)
    before = scribe(rig)["file"]

    file_button(page).click()
    page.page.get_by_role("textbox", name="Title").fill("a/b")
    page.page.get_by_role("button", name="Start new file").click()

    expect(page.page.get_by_role("alert")).to_have_text("A title can't contain /")
    assert scribe(rig)["file"] == before


def test_the_title_is_focused_when_the_menu_opens(context, rig):
    page = open_page(context, rig)

    file_button(page).click()

    expect(page.page.get_by_role("textbox", name="Title")).to_be_focused()


def test_the_menu_shows_the_folder_and_can_copy_it(context, rig):
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    page = open_page(context, rig)
    directory = scribe(rig)["directory"]

    file_button(page).click()
    menu = page.page.get_by_role("dialog", name="Data file")
    expect(menu).to_contain_text(directory)
    menu.get_by_role("button", name="Copy the folder's path").click()

    expect(menu.get_by_role("status")).to_have_text("Copied")
    assert page.page.evaluate("navigator.clipboard.readText()") == directory
    # Opening the folder needs the app's own window, not a browser.
    expect(menu.get_by_role("button", name="Open the folder")).to_have_count(0)


def test_escape_or_a_click_elsewhere_closes_the_menu(context, rig):
    page = open_page(context, rig)
    menu = page.page.get_by_role("dialog", name="Data file")

    file_button(page).click()
    page.page.keyboard.press("Escape")
    expect(menu).to_have_count(0)

    file_button(page).click()
    page.page.mouse.click(640, 500)
    expect(menu).to_have_count(0)


# -------------------------------------------------------------- measurements
def test_the_measurements_can_be_paused_and_resumed(context, rig):
    page = open_page(context, rig)
    expect(rack_button(page)).to_have_text("Every 0.25 s")

    page.page.get_by_role("button", name="Pause measurements").click()

    expect(rack_button(page)).to_have_text("Paused")
    assert rig.get("/rack/state").json()["paused"] is True
    page.page.wait_for_timeout(300)  # the last row in flight arrives
    seq = page.page.evaluate("window.pyacquisition.store.seq")
    page.page.wait_for_timeout(800)
    assert page.page.evaluate("window.pyacquisition.store.seq") == seq

    page.page.get_by_role("button", name="Resume measurements").click()

    expect(rack_button(page)).to_have_text("Every 0.25 s")
    page.page.wait_for_function(f"window.pyacquisition.store.seq > {seq}")


def test_a_pause_made_elsewhere_shows(context, rig):
    page = open_page(context, rig)
    expect(rack_button(page)).to_have_text("Every 0.25 s")

    rig.get("/rack/pause/")
    try:
        expect(rack_button(page)).to_have_text("Paused")
    finally:
        rig.get("/rack/resume/")
    expect(rack_button(page)).to_have_text("Every 0.25 s")


def test_the_period_can_be_changed(context, rig):
    page = open_page(context, rig)

    rack_button(page).click()
    box = page.page.get_by_role("textbox", name="Seconds between measurements")
    expect(box).to_have_value("0.25")
    expect(box).to_be_focused()
    box.fill("0.5")
    page.page.get_by_role("button", name="Apply").click()
    try:
        expect(rack_button(page)).to_have_text("Every 0.5 s")
        assert rig.get("/rack/state").json()["period"] == 0.5
    finally:
        rig.get("/rack/period/set/", period=0.25)


@pytest.mark.parametrize("text", ["0", "-1", "fast", ""])
def test_a_period_that_is_not_a_positive_number_is_explained(context, rig, text):
    page = open_page(context, rig)

    rack_button(page).click()
    page.page.get_by_role("textbox", name="Seconds between measurements").fill(text)
    page.page.get_by_role("button", name="Apply").click()

    expect(page.page.get_by_role("alert")).to_have_text(
        "Give a number of seconds above zero."
    )
    assert rig.get("/rack/state").json()["period"] == 0.25


# -------------------------------------------------------------- stopping
def test_stopping_asks_first(context, rig):
    page = open_page(context, rig)

    page.page.get_by_role("button", name="Stop the experiment").click()

    dialog = page.page.get_by_role("alertdialog")
    expect(dialog).to_contain_text("Stop the experiment?")
    expect(dialog).to_contain_text("This stops the experiment and all of its tasks.")
    dialog.get_by_role("button", name="Keep running").click()
    expect(dialog).to_have_count(0)
    assert rig.get("/ping").json() == "pong"


def test_stopping_stops_the_experiment(context, tmp_path):
    running = Running(SmokeExperiment, tmp_path)
    try:
        page = open_page(context, running)

        page.page.get_by_role("button", name="Stop the experiment").click()
        page.page.get_by_role("button", name="Stop experiment").click()

        expect(page.page.get_by_role("alertdialog")).to_contain_text(
            "The experiment has stopped"
        )
        running.thread.join(timeout=15)
        assert not running.thread.is_alive()
    finally:
        running.stop()
