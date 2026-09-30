"""Usage › Build a config in the interface (docs/usage/setup_page.md): the page's
steps, done in the real setup page, write exactly the files the page shows
(examples/usage/setup_page/cryostat_N.toml), and it says what the page says."""

import time
from pathlib import Path

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, SetupRunning

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples" / "usage" / "setup_page"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.fixture
def setup(tmp_path):
    running = SetupRunning(tmp_path / "cryostat.toml")
    yield running, tmp_path / "cryostat.toml"
    running.stop()


def section(page, name):
    page.get_by_role("navigation", name="Sections").get_by_role("button", name=name).click()
    page.get_by_role("heading", name=name).wait_for()


def add_instrument(page, driver, name):
    page.get_by_role("button", name="Add instrument").click()
    page.get_by_label("Driver").fill(driver)
    page.get_by_label("Name").last.fill(name)
    page.get_by_role("button", name="Add", exact=True).click()


def add_measurement(page, instrument, method, name, unit):
    page.get_by_role("button", name="Add measurement").click()
    form = page.get_by_role("form", name="Add measurement")
    form.get_by_label("Instrument").select_option(instrument)
    form.get_by_label("Query").select_option(method)
    form.get_by_label("Name").fill(name)
    form.get_by_role("button", name="Add", exact=True).click()
    if unit:
        page.locator(f"#measurement-{name}-unit").fill(unit)


def save(page, path, version):
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_text("Unsaved changes")).to_have_count(0)
    wanted = text(HERE / f"cryostat_{version}.toml")
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not (path.exists() and text(path) == wanted):
        time.sleep(0.05)  # the file may still be being written
    assert text(path) == wanted, f"after step {version}"


def test_each_step_writes_the_file_the_page_shows(context, setup):
    running, path = setup
    page = Page(context.new_page()).page
    page.goto(f"{running.address}/")
    page.get_by_role("heading", name="Instruments").wait_for()
    assert not path.exists()  # made when it is first saved

    add_instrument(page, "Clock", "clock")
    add_instrument(page, "SR_830", "lockin")
    page.locator("#instrument-lockin-adapter").select_option("mock")
    page.locator("#instrument-lockin-resource").fill("GPIB0::8::INSTR")
    add_instrument(page, "Lakeshore_350", "cryostat")
    page.locator("#instrument-cryostat-adapter").select_option("mock")
    page.locator("#instrument-cryostat-resource").fill("GPIB0::12::INSTR")
    lockin = page.get_by_role("article", name="Instrument lockin", exact=True)
    lockin.get_by_role("button", name="Test").click()
    expect(lockin).to_contain_text("It answered MOCK,GPIB0::8::INSTR,0,0, which isn't a SR_830")
    save(page, path, 1)

    section(page, "Measurements")
    add_measurement(page, "clock", "time", "time", "s")
    add_measurement(page, "lockin", "get_x", "x", "V")
    add_measurement(page, "cryostat", "get_temperature", "T", None)
    page.locator("#measurement-T-arg-input_channel").select_option(label="Input A")
    page.locator("#measurement-T-unit").fill("K")  # after the channel, as the page says
    save(page, path, 2)

    section(page, "Calculations")
    page.get_by_role("button", name="Add calculation").click()
    form = page.get_by_role("form", name="Add calculation")
    form.get_by_label("Calculation").select_option("RollingMean")
    form.get_by_label("Name").fill("x_mean10")
    form.get_by_role("button", name="Add", exact=True).click()
    page.locator("#calculation-x_mean10-column").select_option("x")
    page.locator("#calculation-x_mean10-window").fill("10")
    page.locator("#calculation-x_mean10-unit").fill("V")
    save(page, path, 3)

    section(page, "Options")
    page.locator("#option-rack-period").fill("0.5")
    page.locator("#option-logging-console_level").select_option("INFO")
    save(page, path, 4)

    page.locator("#option-rack-period").fill("fast")
    problems = page.get_by_role("list", name="Problems")
    expect(problems).to_contain_text("period must be a positive number, got 'fast'")
    expect(page.get_by_role("button", name="Save", exact=True)).to_be_disabled()
    page.locator("#option-rack-period").fill("0.5")
    expect(page.get_by_role("button", name="Save", exact=True)).to_be_disabled()  # nothing new to save
    expect(problems).to_have_count(0)
    assert text(path) == text(HERE / "cryostat_4.toml")
