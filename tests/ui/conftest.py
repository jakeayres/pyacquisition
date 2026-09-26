"""The new GUI's page, loaded in a real browser against a running experiment.

The browser is the installed Microsoft Edge, driven by Playwright, so no browser
needs downloading. Without Edge, these tests are skipped. What the tests share
is in ui_helpers.py.
"""

import pytest

from ui_helpers import VIEWPORT, Page, Running, SmokeExperiment


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    """The address of a running experiment, with no GUI of its own."""
    running = Running(SmokeExperiment, tmp_path_factory.mktemp("ui"))
    yield running.address
    running.stop()


# Module scope, not session: while Playwright runs, its event loop is the running
# loop on the main thread, and any asyncio test after it would fail with "cannot
# be called from a running event loop". It has to stop before other tests run.
@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import Error, sync_playwright

    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.launch(channel="msedge")
    except Error:
        playwright.stop()
        pytest.skip("Microsoft Edge is not installed")
    yield browser
    browser.close()
    playwright.stop()


@pytest.fixture
def context(browser):
    """A fresh browser context, so no session state carries between tests.

    Reduced motion turns the page's transitions off (see app.css), so sizes can be
    measured straight after they change.
    """
    context = browser.new_context(viewport=VIEWPORT, reduced_motion="reduce")
    yield context
    context.close()


@pytest.fixture
def page(context, server):
    """The page, loaded and connected."""
    page = Page(context.new_page())
    page.page.goto(f"{server}/")
    page.page.get_by_role("status").filter(has_text="Connected").wait_for()
    yield page
    assert page.errors == [], f"the page logged errors: {page.errors}"
