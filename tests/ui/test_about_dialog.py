"""About PyAcquisition (milestone 2 of specs/archive/relicense-mpl.md): the
dialog that the palette's action and the top bar's name open, with what /about
says."""

import pytest

pytest.importorskip("playwright")

import requests
from playwright.sync_api import expect


def about(page):
    return page.page.get_by_role("dialog", name="About PyAcquisition")


def brand(page):
    return page.page.get_by_role("button", name="About PyAcquisition")


def test_the_palettes_action_opens_it(page):
    page.page.keyboard.press("Control+k")
    palette = page.page.get_by_role("dialog", name="Command palette")
    expect(palette.get_by_role("option").first).to_be_visible()
    search = palette.get_by_role("searchbox")
    search.press_sequentially("about")
    expect(palette.get_by_role("option").first).to_contain_text("About PyAcquisition")
    search.press("Enter")

    expect(about(page)).to_be_visible()


def test_the_top_bars_name_opens_it(page):
    expect(brand(page).locator(".brand-name")).to_have_text("SmokeExperiment")

    brand(page).click()

    expect(about(page)).to_be_visible()


def test_it_shows_what_about_says(page, server):
    data = requests.get(f"{server}/about", timeout=5).json()["data"]

    brand(page).click()

    dialog = about(page)
    expect(dialog).to_contain_text(f"Version {data['version']}" if data["version"] else "Version unknown")
    expect(dialog.get_by_role("link", name="Mozilla Public License 2.0")).to_have_attribute(
        "href", "https://pyacquisition.readthedocs.io/en/latest/overview/license/"
    )
    expect(dialog).to_contain_text("Copyright (C) 2023-2026 Jake Ayres")
    expect(dialog.get_by_role("link", name="github.com/jakeayres/pyacquisition")).to_have_attribute(
        "href", "https://github.com/jakeayres/pyacquisition"
    )
    expect(dialog).to_contain_text("Its interface uses Preact (MIT), uPlot (MIT) and htm (Apache-2.0).")


def test_escape_and_close_close_it(page):
    brand(page).click()
    expect(about(page)).to_be_visible()
    page.page.keyboard.press("Escape")
    expect(about(page)).to_have_count(0)

    brand(page).click()
    about(page).get_by_role("button", name="Close").click()
    expect(about(page)).to_have_count(0)
