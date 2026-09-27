"""The setup page's measurements: each one's instrument, query, arguments (a form
built from the query's route) and unit, their order, which is the data file's,
and renaming and removing them (milestone 6 of specs/setup-page.md)."""

from pathlib import Path

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, SetupRunning

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

RIG = """\
# A rig to measure.

[instruments]
clock = {instrument = "Clock"}

[instruments.lakeshore]
instrument = "Lakeshore_350"
adapter = "mock"
resource = "GPIB0::12::INSTR"

[instruments.magnet]
instrument = "Mercury_IPS"
adapter = "mock"
resource = "GPIB0::25::INSTR"

[measurements]
t = {instrument = "clock", method = "timestamp_ms", unit = "ms"}
T = {instrument = "lakeshore", method = "get_temperature", args = {input_channel = "INPUT_B"}, unit = "K"}

[calculations.T_smooth]
calculation = "RollingMean"
column = "T"
window = 5
"""


def serve(tmp_path, text=RIG):
    path = tmp_path / "rig.toml"
    path.write_bytes(text.encode("utf-8"))
    return SetupRunning(path), path


@pytest.fixture
def setup(tmp_path):
    running, _ = serve(tmp_path)
    yield running
    running.stop()


def open_measurements(context, running):
    page = Page(context.new_page())
    page.page.goto(f"{running.address}/")
    page.page.get_by_role("navigation", name="Sections").get_by_role(
        "button", name="Measurements"
    ).click()
    page.page.get_by_role("heading", name="Measurements").wait_for()
    expect(page.page.get_by_label("TOML")).not_to_be_empty()
    return page


def card(page, name):
    return page.page.get_by_role("article", name=f"Measurement {name}", exact=True)


def toml(page):
    return page.page.get_by_label("TOML")


def add(page, instrument, method, name=None):
    page.page.get_by_role("button", name="Add measurement").click()
    form = page.page.get_by_role("form", name="Add measurement")
    form.get_by_label("Instrument").select_option(instrument)
    form.get_by_label("Query").select_option(method)
    if name:
        form.get_by_label("Name").fill(name)
    form.get_by_role("button", name="Add", exact=True).click()


# ------------------------------------------------------------ what is shown
def test_each_measurement_has_its_instrument_query_arguments_and_unit(context, setup):
    page = open_measurements(context, setup)

    expect(page.page.locator("#measurement-T-instrument")).to_have_value("lakeshore")
    expect(page.page.locator("#measurement-T-method")).to_have_value("get_temperature")
    channel = page.page.locator("#measurement-T-arg-input_channel")
    expect(channel).to_have_value("INPUT_B")
    expect(channel.locator("option:checked")).to_have_text("Input B")
    expect(page.page.locator("#measurement-T-unit")).to_have_value("K")
    expect(card(page, "t")).to_contain_text("column 1")
    expect(card(page, "T")).to_contain_text("column 2")
    assert page.errors == []


def test_the_querys_docstring_is_shown(context, setup):
    page = open_measurements(context, setup)

    expect(card(page, "T")).to_contain_text("temperature")


# ------------------------------------------------------------ adding
def test_a_query_with_an_enum_offers_its_members_and_writes_the_name(context, setup):
    page = open_measurements(context, setup)

    add(page, "lakeshore", "get_temperature", name="T2")
    channel = page.page.locator("#measurement-T2-arg-input_channel")
    expect(channel.locator("option")).to_have_text(
        ["Choose…", "Input A", "Input B", "Input C", "Input D"]
    )
    channel.select_option(label="Input A")

    expect(toml(page)).to_contain_text(
        'T2 = {instrument = "lakeshore", method = "get_temperature", '
        'args = {input_channel = "INPUT_A"}}'
    )


def test_a_needed_argument_left_out_is_a_problem(context, setup):
    page = open_measurements(context, setup)

    add(page, "lakeshore", "get_temperature", name="T2")

    expect(card(page, "T2").locator('[data-field="input_channel"] .form-error')).to_contain_text(
        "needs input_channel"
    )


def test_only_a_drivers_queries_are_offered_not_its_commands(context, setup):
    page = open_measurements(context, setup)
    page.page.get_by_role("button", name="Add measurement").click()
    form = page.page.get_by_role("form", name="Add measurement")

    form.get_by_label("Instrument").select_option("magnet")

    options = form.get_by_label("Query").locator("option")
    expect(options.filter(has_text="get_output_field")).to_have_count(1)
    expect(options.filter(has_text="to_zero")).to_have_count(0)
    expect(options.filter(has_text="switch_heater_on")).to_have_count(0)


def test_a_new_measurement_is_named_after_its_query(context, setup):
    page = open_measurements(context, setup)

    add(page, "magnet", "get_output_field")

    expect(card(page, "output_field")).to_be_visible()
    expect(toml(page)).to_contain_text(
        'output_field = {instrument = "magnet", method = "get_output_field"}'
    )


def test_software_instruments_offer_every_query(context, setup):
    page = open_measurements(context, setup)

    add(page, "clock", "time", name="seconds")

    expect(toml(page)).to_contain_text('seconds = {instrument = "clock", method = "time"}')
    expect(page.page.get_by_text("No problems.")).to_be_visible()


# ------------------------------------------------------------ changing
def test_a_unit_goes_in_the_file(context, setup):
    page = open_measurements(context, setup)

    page.page.locator("#measurement-t-unit").fill("s")

    expect(toml(page)).to_contain_text(
        't = {instrument = "clock", method = "timestamp_ms", unit = "s"}'
    )


def test_changing_the_query_clears_its_arguments(context, setup):
    page = open_measurements(context, setup)

    page.page.locator("#measurement-T-method").select_option("identify")

    expect(toml(page)).not_to_contain_text("INPUT_B")


def test_moving_a_measurement_changes_the_column_order(context, setup):
    page = open_measurements(context, setup)

    page.page.get_by_role("button", name="Move T up", exact=True).click()

    expect(card(page, "T")).to_contain_text("column 1")
    text = toml(page)
    expect(text).to_contain_text("[measurements]\nT = {")
    expect(page.page.get_by_role("button", name="Move T up", exact=True)).to_be_disabled()


def test_renaming_a_measurement_renames_it_in_the_calculations(context, setup):
    page = open_measurements(context, setup)

    name = card(page, "T").get_by_label("Name")
    name.fill("temperature")
    name.press("Enter")

    expect(toml(page)).to_contain_text('temperature = {instrument = "lakeshore"')
    expect(toml(page)).to_contain_text('column = "temperature"')
    expect(page.page.get_by_text("No problems.")).to_be_visible()


def test_a_column_name_that_is_taken_is_refused(context, setup):
    page = open_measurements(context, setup)

    name = card(page, "T").get_by_label("Name")
    name.fill("T_smooth")
    name.press("Enter")

    expect(card(page, "T").get_by_role("alert")).to_have_text(
        "There is already a column called T_smooth."
    )


def test_removing_an_instrument_a_measurement_uses_is_a_problem_by_it(context, setup):
    page = open_measurements(context, setup)
    page.page.get_by_role("navigation", name="Sections").get_by_role(
        "button", name="Instruments"
    ).click()
    page.page.get_by_role("article", name="Instrument lakeshore").get_by_role(
        "button", name="Remove"
    ).click()
    page.page.get_by_role("navigation", name="Sections").get_by_role(
        "button", name="Measurements"
    ).click()

    expect(card(page, "T").locator('[data-field="instrument"] .form-error')).to_contain_text(
        "there is no instrument 'lakeshore'"
    )


def test_removing_a_measurement(context, setup):
    page = open_measurements(context, setup)

    card(page, "t").get_by_role("button", name="Remove").click()

    expect(card(page, "t")).to_have_count(0)
    expect(toml(page)).not_to_contain_text("timestamp_ms")


# ------------------------------------------------------------ a real config
def test_the_front_page_example_is_shown_and_kept_as_it_is(context, tmp_path):
    text = (EXAMPLES / "front_page.toml").read_text(encoding="utf-8")
    running, path = serve(tmp_path, text)
    try:
        page = open_measurements(context, running)

        expect(toml(page)).to_have_text(text)
        expect(page.page.locator("#measurement-T-arg-input_channel")).to_have_value("INPUT_A")
        expect(page.page.get_by_role("button", name="Save", exact=True)).to_be_disabled()
        assert page.errors == []
    finally:
        running.stop()
