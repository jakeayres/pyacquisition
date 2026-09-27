"""The setup page (`pyacquisition new`): the options, the file it makes beside
them, checked as it changes, Save, and asking before closing with unsaved
changes (milestone 4 of specs/setup-page.md)."""

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, SetupRunning

from pyacquisition.core import settings

RIG = """\
# The cryostat rig.

[rack]
period = 0.5  # fast enough for the lock-in

[instruments]
clock = {instrument = "Clock"}  # for the time column

[measurements]
t = {instrument = "clock", method = "timestamp_ms"}
"""


@pytest.fixture
def rig_file(tmp_path):
    path = tmp_path / "rig.toml"
    path.write_bytes(RIG.encode("utf-8"))
    return path


@pytest.fixture
def setup(rig_file):
    running = SetupRunning(rig_file)
    yield running
    running.stop()


def open_setup(context, running):
    page = Page(context.new_page())
    page.page.goto(f"{running.address}/")
    page.page.get_by_role("navigation", name="Sections").get_by_role("button", name="Options").click()
    page.page.get_by_role("heading", name="Options").wait_for()
    expect(page.page.get_by_label("TOML")).not_to_be_empty()  # checked once
    return page


def field(page, section, key):
    return page.page.locator(f"#option-{section}-{key}")


def toml(page):
    return page.page.get_by_label("TOML")


def save_button(page):
    return page.page.get_by_role("button", name="Save", exact=True)


# ------------------------------------------------------------ the fields
def test_there_is_a_field_for_each_option_by_its_section(context, setup):
    page = open_setup(context, setup)

    expect(page.page.locator(".setup-group .form-field")).to_have_count(len(settings.SETTINGS))
    legends = page.page.locator(".setup-group legend")
    expect(legends.first).to_have_text("[experiment]")
    expect(page.page.get_by_text("[api_server]", exact=True)).to_be_visible()
    assert page.errors == []


def test_a_set_option_shows_its_value_and_an_unset_one_its_default(context, setup):
    page = open_setup(context, setup)

    expect(field(page, "rack", "period")).to_have_value("0.5")
    expect(field(page, "api_server", "port")).to_have_value("")
    expect(field(page, "api_server", "port")).to_have_attribute("placeholder", "default: 8000")
    expect(field(page, "logging", "console_level").locator("option").first).to_have_text(
        "Default (DEBUG)"
    )


def test_an_options_help_is_shown(context, setup):
    page = open_setup(context, setup)

    expect(page.page.get_by_text("The time between measurements, in seconds.")).to_be_visible()


# ------------------------------------------------------------ the preview
def test_the_file_is_shown_as_it_is(context, setup):
    page = open_setup(context, setup)

    expect(toml(page)).to_have_text(RIG)
    expect(page.page.get_by_text("No problems.")).to_be_visible()


def test_the_preview_follows_a_change_and_keeps_the_comments(context, setup):
    page = open_setup(context, setup)

    field(page, "rack", "period").fill("0.75")

    expect(toml(page)).to_have_text(RIG.replace("period = 0.5", "period = 0.75"))
    expect(page.page.get_by_role("status").filter(has_text="Unsaved changes")).to_be_visible()


def test_a_new_option_is_added_to_the_file(context, setup):
    page = open_setup(context, setup)

    field(page, "logging", "console_level").select_option("INFO")

    expect(toml(page)).to_contain_text('[logging]\nconsole_level = "INFO"')


def test_clearing_an_option_takes_it_out_of_the_file(context, setup):
    page = open_setup(context, setup)

    field(page, "rack", "period").fill("")

    expect(toml(page)).not_to_contain_text("[rack]")
    expect(toml(page)).to_contain_text("# The cryostat rig.")


# ------------------------------------------------------------ problems
def test_an_invalid_value_is_shown_by_its_field_and_stops_save(context, setup):
    page = open_setup(context, setup)

    field(page, "rack", "period").fill("fast")

    problem = "`period` must be a positive number, got 'fast'"
    expect(page.page.locator('[data-field="measurement_period"] .form-error')).to_have_text(
        problem.replace("`", "")
    )
    expect(field(page, "rack", "period")).to_have_attribute("aria-invalid", "true")
    expect(page.page.get_by_role("list", name="Problems")).to_contain_text("[rack] period")
    expect(save_button(page)).to_be_disabled()


def test_fixing_the_value_lets_it_be_saved(context, setup):
    page = open_setup(context, setup)
    field(page, "rack", "period").fill("-1")
    expect(save_button(page)).to_be_disabled()

    field(page, "rack", "period").fill("1")

    expect(page.page.get_by_text("No problems.")).to_be_visible()
    expect(save_button(page)).to_be_enabled()


# ------------------------------------------------------------ saving
def test_save_writes_the_file_keeping_its_comments(context, setup, rig_file):
    page = open_setup(context, setup)
    expect(save_button(page)).to_be_disabled()  # nothing to save yet
    field(page, "rack", "period").fill("0.75")
    field(page, "api_server", "fallback_ports").fill("8001, 8002")

    save_button(page).click()

    expect(page.page.get_by_role("status").filter(has_text="Saved")).to_be_visible()
    expect(save_button(page)).to_be_disabled()
    assert rig_file.read_text(encoding="utf-8") == (
        RIG.replace("period = 0.5", "period = 0.75")
        + "\n[api_server]\nfallback_ports = [8001, 8002]\n"
    )


def test_a_file_that_does_not_exist_is_made_on_the_first_save(context, tmp_path):
    path = tmp_path / "fresh.toml"
    running = SetupRunning(path)
    try:
        page = open_setup(context, running)
        expect(page.page.get_by_role("status").filter(has_text="Not saved yet")).to_be_visible()
        expect(toml(page)).to_contain_text("made with `pyacquisition new`")

        field(page, "rack", "period").fill("0.5")
        save_button(page).click()

        expect(page.page.get_by_role("status").filter(has_text="Saved")).to_be_visible()
        text = path.read_text(encoding="utf-8")
        assert text.startswith("# An experiment's config")
        assert "[rack]\nperiod = 0.5\n" in text
    finally:
        running.stop()


# ------------------------------------------------------------ closing
def test_closing_with_unsaved_changes_asks_first(context, setup):
    page = open_setup(context, setup)
    field(page, "rack", "period").fill("0.75")
    expect(page.page.get_by_role("status").filter(has_text="Unsaved changes")).to_be_visible()

    page.page.evaluate("window.pyacquisition.requestClose()")

    dialog = page.page.get_by_role("alertdialog", name="Close without saving?")
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name="Cancel").click()
    expect(dialog).to_be_hidden()
    assert setup.thread.is_alive()  # still there, with the changes


def test_closing_without_changes_closes_at_once(context, setup):
    page = open_setup(context, setup)

    page.page.evaluate("window.pyacquisition.requestClose()")

    expect(page.page.get_by_role("heading", name="The setup page has closed")).to_be_visible()
    setup.thread.join(timeout=10)
    assert not setup.thread.is_alive()


def test_closing_without_saving_when_told_to(context, setup, rig_file):
    page = open_setup(context, setup)
    field(page, "rack", "period").fill("0.75")
    expect(page.page.get_by_role("status").filter(has_text="Unsaved changes")).to_be_visible()

    page.page.evaluate("window.pyacquisition.requestClose()")
    page.page.get_by_role("button", name="Close without saving").click()

    expect(page.page.get_by_role("heading", name="The setup page has closed")).to_be_visible()
    assert rig_file.read_text(encoding="utf-8") == RIG
