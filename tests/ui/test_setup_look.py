"""How the setup page looks and reads: the section and the file as wide as each
other, the file's TOML coloured, defaults that can't be taken for values, and
the driver list tall enough to see several at once."""

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, SetupRunning

RIG = """\
# A rig to look at.

[instruments]
clock = {instrument = "Clock"}
random = {instrument = "RandomNumberGenerator"}

[measurements]
t = {instrument = "clock", method = "timestamp_ms", unit = "ms"}
n = {instrument = "random", method = "integer"}

[rack]
period = 0.5
"""


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / "rig.toml"
    path.write_bytes(RIG.encode("utf-8"))
    running = SetupRunning(path)
    yield running
    running.stop()


def open_setup(context, running):
    page = Page(context.new_page())
    page.page.goto(f"{running.address}/")
    page.page.get_by_role("heading", name="Instruments").wait_for()
    expect(page.page.get_by_label("TOML")).not_to_be_empty()
    return page


def section(page, name):
    page.page.get_by_role("navigation", name="Sections").get_by_role("button", name=name).click()
    page.page.get_by_role("heading", name=name).wait_for()


def test_the_section_and_the_file_are_as_wide_as_each_other(context, setup):
    page = open_setup(context, setup)

    middle = page.page.locator(".setup-main").bounding_box()
    file = page.page.locator(".setup-preview").bounding_box()

    assert abs(middle["width"] - file["width"]) <= 2


def test_the_file_is_coloured_and_its_text_is_as_it_is(context, setup):
    page = open_setup(context, setup)
    toml = page.page.get_by_label("TOML")

    expect(toml).to_have_text(RIG)
    expect(toml.locator(".toml-comment")).to_have_text(["# A rig to look at."])
    expect(toml.locator(".toml-header")).to_have_text(["[instruments]", "[measurements]", "[rack]"])
    expect(toml.locator(".toml-key").first).to_have_text("clock")
    expect(toml.locator(".toml-string").first).to_have_text('"Clock"')
    expect(toml.locator(".toml-number")).to_have_text(["0.5"])
    assert page.errors == []


def test_a_default_in_an_argument_box_is_shown_as_one_and_is_not_in_the_file(context, setup):
    page = open_setup(context, setup)
    section(page, "Measurements")

    high = page.page.locator("#measurement-n-arg-high")

    expect(high).to_have_value("")
    expect(high).to_have_attribute("placeholder", "default: 100")
    assert high.evaluate("e => getComputedStyle(e, '::placeholder').fontStyle") == "italic"
    expect(page.page.get_by_label("TOML")).to_contain_text(
        'n = {instrument = "random", method = "integer"}'
    )


def test_the_driver_list_shows_several_and_filters_as_you_type(context, setup):
    page = open_setup(context, setup)
    page.page.get_by_role("button", name="Add instrument").click()
    drivers = page.page.get_by_role("listbox", name="Choices")

    options = drivers.get_by_role("option")
    from pyacquisition.instruments import instrument_map

    expect(options).to_have_count(len(instrument_map))  # every driver
    box = drivers.bounding_box()
    row = options.first.bounding_box()
    assert box["height"] >= 5 * row["height"]  # at least five in view at once

    page.page.get_by_label("Driver").fill("lake")
    expect(options).to_have_text(["Lakeshore_340hardware", "Lakeshore_350hardware"])

    options.last.click()
    expect(page.page.get_by_label("Driver")).to_have_value("Lakeshore_350")
    page.page.get_by_role("button", name="Add", exact=True).click()
    expect(page.page.get_by_role("article", name="Instrument lakeshore_350", exact=True)).to_be_visible()


def test_the_driver_list_answers_the_arrow_keys_and_enter(context, setup):
    page = open_setup(context, setup)
    page.page.get_by_role("button", name="Add instrument").click()
    box = page.page.get_by_label("Driver")

    box.fill("SR_")
    box.press("ArrowDown")
    box.press("Enter")

    expect(box).to_have_value("SR_860")
