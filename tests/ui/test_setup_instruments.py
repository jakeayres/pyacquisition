"""The setup page's instruments: adding, renaming and removing them, a hardware
instrument's adapter, address and common options, other args kept, and Test
asking for *IDN? (milestone 5 of specs/setup-page.md). Finding instruments
waits for discovery (roadmap 11)."""

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, SetupRunning

RIG = """\
[instruments]
clock = {instrument = "Clock"}

[instruments.lockin]
instrument = "SR_830"
adapter = "mock"
resource = "GPIB0::7::INSTR"
args = {responses = {"*IDN?" = "Stanford_Research_Systems,SR830,1,1"}}

[instruments.wrong]
instrument = "SR_830"
adapter = "mock"
resource = "GPIB0::12::INSTR"
args = {timeout = 2000, responses = {"*IDN?" = "LSCI,MODEL350"}}

[measurements]
x = {instrument = "lockin", method = "get_x"}
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
    page.page.get_by_role("heading", name="Instruments").wait_for()
    expect(page.page.get_by_label("TOML")).not_to_be_empty()
    return page


def card(page, name):
    return page.page.get_by_role("article", name=f"Instrument {name}", exact=True)


def toml(page):
    return page.page.get_by_label("TOML")


# ------------------------------------------------------------ what is shown
def test_each_instrument_has_a_card(context, setup):
    page = open_setup(context, setup)

    for name in ("clock", "lockin", "wrong"):
        expect(card(page, name)).to_be_visible()
    expect(card(page, "clock")).to_contain_text("Clock · software")
    expect(card(page, "clock").get_by_role("button", name="Test")).to_have_count(0)
    expect(card(page, "lockin")).to_contain_text("SR_830 · hardware")
    expect(page.page.locator("#instrument-lockin-adapter")).to_have_value("mock")
    expect(page.page.locator("#instrument-lockin-resource")).to_have_value("GPIB0::7::INSTR")
    assert page.errors == []


def test_the_common_options_have_fields_and_other_args_are_kept(context, setup):
    page = open_setup(context, setup)

    expect(page.page.locator("#instrument-wrong-timeout")).to_have_value("2000")
    others = card(page, "wrong").get_by_role("list", name="Other args")
    expect(others).to_contain_text('responses = {"*IDN?":"LSCI,MODEL350"}')


# ------------------------------------------------------------ Test
def test_an_instrument_that_is_its_driver_matches(context, setup):
    page = open_setup(context, setup)

    card(page, "lockin").get_by_role("button", name="Test").click()

    expect(card(page, "lockin").locator(".setup-test")).to_have_text(
        "It answered Stanford_Research_Systems,SR830,1,1, which is a SR_830."
    )


def test_an_instrument_that_is_not_its_driver_does_not_match(context, setup):
    page = open_setup(context, setup)

    card(page, "wrong").get_by_role("button", name="Test").click()

    result = card(page, "wrong").locator(".setup-test")
    expect(result).to_contain_text("It answered LSCI,MODEL350, which isn't a SR_830")
    expect(result).to_contain_text("a SR_830's answer has STANFORD, SR830.")


def test_an_address_that_cant_be_opened_says_why(context, setup):
    page = open_setup(context, setup)
    page.page.locator("#instrument-lockin-adapter").select_option("prologix")
    page.page.locator("#instrument-lockin-resource").fill("NOT_A_PORT::7")

    card(page, "lockin").get_by_role("button", name="Test").click()

    expect(card(page, "lockin").locator(".setup-test-bad")).to_contain_text("Could not open")


# ------------------------------------------------------------ changing them
def test_the_address_and_options_go_in_the_file(context, setup):
    page = open_setup(context, setup)

    page.page.locator("#instrument-lockin-resource").fill("GPIB0::8::INSTR")
    page.page.locator("#instrument-lockin-timeout").fill("3000")
    page.page.locator("#instrument-lockin-read_termination").fill("\\n")

    expect(toml(page)).to_contain_text('resource = "GPIB0::8::INSTR"')
    expect(toml(page)).to_contain_text(
        'args = {responses = {"*IDN?" = "Stanford_Research_Systems,SR830,1,1"}, '
        'timeout = 3000, read_termination = "\\n"}'
    )


def test_a_timeout_that_isnt_a_number_is_a_problem(context, setup):
    page = open_setup(context, setup)

    page.page.locator("#instrument-lockin-timeout").fill("soon")

    expect(card(page, "lockin").locator('[data-field="timeout"] .form-error')).to_contain_text(
        "timeout must be a whole number of milliseconds"
    )


def test_an_instrument_is_added_with_its_address_to_fill_in(context, setup):
    page = open_setup(context, setup)

    page.page.get_by_role("button", name="Add instrument").click()
    page.page.get_by_label("Driver").fill("Lakeshore_350")
    page.page.get_by_role("button", name="Add", exact=True).click()

    expect(card(page, "lakeshore_350")).to_be_visible()
    expect(page.page.locator("#instrument-lakeshore_350-adapter")).to_have_value("pyvisa")
    expect(
        card(page, "lakeshore_350").locator('[data-field="resource"] .form-error')
    ).to_contain_text("needs `resource`".replace("`", ""))
    expect(toml(page)).to_contain_text('[instruments.lakeshore_350]\ninstrument = "Lakeshore_350"')


def test_a_software_instrument_is_added_as_it_is(context, setup):
    page = open_setup(context, setup)

    page.page.get_by_role("button", name="Add instrument").click()
    page.page.get_by_label("Driver").fill("SignalGenerator")
    page.page.get_by_label("Name").last.fill("signal")
    page.page.get_by_role("button", name="Add", exact=True).click()

    expect(card(page, "signal")).to_contain_text("SignalGenerator · software")
    expect(toml(page)).to_contain_text('[instruments.signal]\ninstrument = "SignalGenerator"')
    expect(page.page.get_by_text("No problems.")).to_be_visible()


def test_a_driver_that_isnt_known_is_not_added(context, setup):
    page = open_setup(context, setup)

    page.page.get_by_role("button", name="Add instrument").click()
    page.page.get_by_label("Driver").fill("Mongolia")
    page.page.get_by_role("button", name="Add", exact=True).click()

    expect(page.page.get_by_role("alert")).to_have_text("Pick a driver from the list.")


def test_renaming_an_instrument_renames_it_in_its_measurements(context, setup):
    page = open_setup(context, setup)

    name = card(page, "lockin").get_by_label("Name")
    name.fill("amplifier")
    name.press("Enter")

    expect(card(page, "amplifier")).to_be_visible()
    expect(toml(page)).to_contain_text("[instruments.amplifier]")
    expect(toml(page)).to_contain_text('x = {instrument = "amplifier", method = "get_x"}')
    expect(page.page.get_by_text("No problems.")).to_be_visible()


def test_a_name_that_is_taken_is_refused(context, setup):
    page = open_setup(context, setup)

    name = card(page, "lockin").get_by_label("Name")
    name.fill("clock")
    name.press("Enter")

    expect(card(page, "lockin").get_by_role("alert")).to_have_text(
        "There is already an instrument called clock."
    )
    expect(toml(page)).to_contain_text("[instruments.lockin]")


def test_removing_an_instrument_a_measurement_uses_is_a_problem(context, setup):
    page = open_setup(context, setup)

    card(page, "lockin").get_by_role("button", name="Remove").click()

    expect(card(page, "lockin")).to_have_count(0)
    expect(toml(page)).not_to_contain_text("[instruments.lockin]")
    expect(page.page.get_by_role("list", name="Problems")).to_contain_text(
        "there is no instrument 'lockin'"
    )
