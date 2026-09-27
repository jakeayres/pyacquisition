"""The setup page's calculations: Sum and RollingMean, their inputs chosen from
the columns above them, their order, and a unit (milestone 7 of
specs/setup-page.md)."""

from pathlib import Path

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, SetupRunning

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

RIG = """\
[instruments]
lockin = {instrument = "SR_830", adapter = "mock", resource = "GPIB0::7::INSTR"}

[measurements]
x = {instrument = "lockin", method = "get_x", unit = "V"}
y = {instrument = "lockin", method = "get_y", unit = "V"}
"""


def serve(tmp_path, text=RIG):
    path = tmp_path / "rig.toml"
    path.write_bytes(text.encode("utf-8"))
    return SetupRunning(path)


@pytest.fixture
def setup(tmp_path):
    running = serve(tmp_path)
    yield running
    running.stop()


def open_calculations(context, running):
    page = Page(context.new_page())
    page.page.goto(f"{running.address}/")
    page.page.get_by_role("navigation", name="Sections").get_by_role(
        "button", name="Calculations"
    ).click()
    page.page.get_by_role("heading", name="Calculations").wait_for()
    expect(page.page.get_by_label("TOML")).not_to_be_empty()
    return page


def card(page, name):
    return page.page.get_by_role("article", name=f"Calculation {name}", exact=True)


def toml(page):
    return page.page.get_by_label("TOML")


def add(page, kind, name):
    page.page.get_by_role("button", name="Add calculation").click()
    form = page.page.get_by_role("form", name="Add calculation")
    form.get_by_label("Calculation").select_option(kind)
    form.get_by_label("Name").fill(name)
    form.get_by_role("button", name="Add", exact=True).click()


def test_a_rolling_mean_is_written_as_the_format_says(context, setup):
    page = open_calculations(context, setup)

    add(page, "RollingMean", "x_smooth")
    page.page.locator("#calculation-x_smooth-column").select_option("x")
    page.page.locator("#calculation-x_smooth-window").fill("10")

    expect(toml(page)).to_contain_text(
        '[calculations.x_smooth]\ncalculation = "RollingMean"\ncolumn = "x"\nwindow = 10'
    )
    expect(page.page.get_by_text("No problems.")).to_be_visible()
    expect(card(page, "x_smooth")).to_contain_text("column 3")
    assert page.errors == []


def test_a_sum_takes_the_columns_ticked_with_a_unit(context, setup):
    page = open_calculations(context, setup)

    add(page, "Sum", "total")
    inputs = card(page, "total").locator('[data-field="inputs"]')
    inputs.get_by_label("y").check()
    inputs.get_by_label("x").check()
    page.page.locator("#calculation-total-unit").fill("V")

    expect(toml(page)).to_contain_text(
        '[calculations.total]\ncalculation = "Sum"\ninputs = ["x", "y"]\nunit = "V"'
    )


def test_a_new_calculation_shows_what_it_still_needs(context, setup):
    page = open_calculations(context, setup)

    add(page, "RollingMean", "m")

    expect(card(page, "m").locator('[data-field="column"] .form-error')).to_contain_text(
        "a RollingMean needs column"
    )
    expect(page.page.get_by_role("button", name="Save", exact=True)).to_be_disabled()


def test_the_inputs_offered_are_the_columns_above_it(context, setup):
    page = open_calculations(context, setup)
    add(page, "Sum", "total")
    add(page, "RollingMean", "total_smooth")

    column = page.page.locator("#calculation-total_smooth-column")
    expect(column.locator("option")).to_have_text(["Choose…", "x", "y", "total"])
    expect(card(page, "total").locator('[data-field="inputs"] input')).to_have_count(2)


def test_moving_a_calculation_above_its_input_is_a_problem(context, setup):
    page = open_calculations(context, setup)
    add(page, "Sum", "total")
    card(page, "total").locator('[data-field="inputs"]').get_by_label("x").check()
    add(page, "RollingMean", "total_smooth")
    page.page.locator("#calculation-total_smooth-column").select_option("total")
    page.page.locator("#calculation-total_smooth-window").fill("3")
    expect(page.page.get_by_text("No problems.")).to_be_visible()

    page.page.get_by_role("button", name="Move total_smooth up", exact=True).click()

    expect(card(page, "total_smooth").locator('[data-field="column"] .form-error')).to_contain_text(
        "names 'total', which is not a measurement or a calculation above this one"
    )
    expect(toml(page)).to_contain_text("[calculations.total_smooth]")
    assert toml(page).inner_text().index("total_smooth") < toml(page).inner_text().index(
        "[calculations.total]"
    )


def test_a_window_of_zero_is_a_problem(context, setup):
    page = open_calculations(context, setup)
    add(page, "RollingMean", "m")
    page.page.locator("#calculation-m-column").select_option("x")

    page.page.locator("#calculation-m-window").fill("0")

    expect(card(page, "m").locator('[data-field="window"] .form-error')).to_contain_text(
        "must be a whole number of at least 1"
    )


def test_changing_the_kind_starts_its_keys_afresh(context, setup):
    page = open_calculations(context, setup)
    add(page, "RollingMean", "m")
    page.page.locator("#calculation-m-column").select_option("x")

    page.page.locator("#calculation-m-calculation").select_option("Sum")

    expect(toml(page)).not_to_contain_text('column = "x"')
    expect(card(page, "m").locator('[data-field="inputs"]')).to_be_visible()


def test_a_name_that_is_a_column_already_is_refused(context, setup):
    page = open_calculations(context, setup)
    page.page.get_by_role("button", name="Add calculation").click()
    form = page.page.get_by_role("form", name="Add calculation")
    form.get_by_label("Calculation").select_option("Sum")
    form.get_by_label("Name").fill("x")
    form.get_by_role("button", name="Add", exact=True).click()

    expect(form.get_by_role("alert")).to_have_text("There is already a column called x.")


def test_the_calculations_example_is_shown_and_kept_as_it_is(context, tmp_path):
    text = (EXAMPLES / "calculations.toml").read_text(encoding="utf-8")
    running = serve(tmp_path, text)
    try:
        page = open_calculations(context, running)

        expect(toml(page)).to_have_text(text)
        expect(page.page.locator("#calculation-v_smooth-column")).to_have_value("v_total")
        expect(
            card(page, "v_total").locator('[data-field="inputs"] input:checked')
        ).to_have_count(2)
        expect(page.page.get_by_role("button", name="Save", exact=True)).to_be_disabled()
        assert page.errors == []
    finally:
        running.stop()
