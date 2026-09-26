"""The Logs tab (milestone 7)."""

import itertools

import pytest

pytest.importorskip("playwright")

from ui_helpers import Page, Running
from playwright.sync_api import expect

from pyacquisition import Experiment, Measurement
from pyacquisition.core.logging import logger
from pyacquisition.instruments import Clock

_markers = itertools.count()


def marker(name="message"):
    """Text that no other test logs."""
    return f"{name}-{next(_markers)}"


class LogRig(Experiment):
    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)
        self.add_measurement(Measurement("time", clock.time))

        # Logs from inside the experiment's event loop, as its own parts do.
        @self._api_server.app.get("/test/log")
        async def log(message: str, level: str = "info", count: int = 1):
            for n in range(count):
                getattr(logger, level)(message.format(n=n))
            return {"status": 200}


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    running = Running(LogRig, tmp_path_factory.mktemp("logs"))
    yield running
    running.stop()


def log(rig, message, level="info", count=1):
    rig.get("/test/log", message=message, level=level, count=count)


def open_logs(context, rig):
    """The page, loaded, with its Logs tab open and its log loaded."""
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function(
        "window.pyacquisition?.logs?.status === 'live'", timeout=15000
    )
    page.page.get_by_role("tab", name="Logs").click()
    return page


def row(page, text):
    return page.page.locator(".log-row").filter(has_text=text)


def search(page, text):
    page.page.get_by_role("searchbox", name="Search the log").fill(text)


def level_toggle(page, label):
    return page.page.get_by_role("group", name="Levels shown").get_by_role(
        "button", name=label
    )


def list_state(page):
    return page.page.locator(".logs-list").evaluate(
        """list => ({
            top: list.scrollTop,
            fromBottom: list.scrollHeight - list.scrollTop - list.clientHeight,
            firstInView: [...list.querySelectorAll('.log-row')]
                .map(row => [row.dataset.seq, row.getBoundingClientRect().top])
                .filter(([, top]) => top >= list.getBoundingClientRect().top - 1)
                .sort((a, b) => a[1] - b[1])[0]?.[0],
        })"""
    )


# -------------------------------------------------------------- what is shown
def test_logs_from_before_the_page_opened_are_shown(context, rig):
    text = marker("early")
    log(rig, text)

    page = open_logs(context, rig)

    expect(row(page, text)).to_have_count(1)
    # Right back to logging being set up, as the experiment was made.
    assert page.page.evaluate(
        "window.pyacquisition.logs.entries"
        ".some(e => e.message.startsWith('Logging configured'))"
    )
    assert page.errors == []


def test_messages_logged_while_the_tab_is_closed_are_kept(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.logs?.status === 'live'")
    expect(page.page.get_by_role("tab", name="Values")).to_have_attribute(
        "aria-selected", "true"
    )
    text = marker("while-closed")
    log(rig, text)
    page.page.wait_for_function(
        f"window.pyacquisition.logs.entries.some(e => e.message === {text!r})"
    )

    page.page.get_by_role("tab", name="Logs").click()

    expect(row(page, text)).to_have_count(1)


def test_new_messages_appear_live(context, rig):
    page = open_logs(context, rig)
    text = marker("live")

    log(rig, text, level="warning")

    expect(row(page, text)).to_have_count(1)


def test_each_row_has_its_time_level_and_source(context, rig):
    page = open_logs(context, rig)
    text = marker("parts")

    log(rig, f"[Tester] {text}", level="error")

    line = row(page, text)
    expect(line.locator(".log-level")).to_have_text("Error")
    expect(line.locator(".log-source")).to_have_text("Tester")
    expect(line.locator(".log-message")).to_have_text(text)
    expect(line.locator(".log-time")).to_have_text(
        __import__("re").compile(r"^\d\d:\d\d:\d\d\.\d{3}$")
    )


def test_each_level_has_its_own_colour(context, rig):
    page = open_logs(context, rig)
    texts = {level: marker(level) for level in ("debug", "info", "warning", "error")}
    for level, text in texts.items():
        log(rig, text, level=level)
    for text in texts.values():
        expect(row(page, text)).to_have_count(1)

    colours = {
        level: row(page, text)
        .locator(".log-level")
        .evaluate("badge => getComputedStyle(badge).color")
        for level, text in texts.items()
    }
    assert len(set(colours.values())) == 4, colours


# -------------------------------------------------------------- filtering
def test_a_level_can_be_hidden_and_shown_again(context, rig):
    page = open_logs(context, rig)
    debug, warning = marker("hidden-debug"), marker("kept-warning")
    log(rig, debug, level="debug")
    log(rig, warning, level="warning")
    expect(row(page, debug)).to_have_count(1)

    level_toggle(page, "Debug").click()

    expect(level_toggle(page, "Debug")).to_have_attribute("aria-pressed", "false")
    expect(row(page, debug)).to_have_count(0)
    expect(row(page, warning)).to_have_count(1)
    expect(page.page.locator(".logs-count")).to_contain_text(" of ")

    level_toggle(page, "Debug").click()

    expect(row(page, debug)).to_have_count(1)


def test_each_level_shows_how_many_messages_it_has(context, rig):
    page = open_logs(context, rig)
    count = page.page.evaluate(
        "window.pyacquisition.logs.entries.filter(e => e.level === 'warning').length"
    )

    expect(level_toggle(page, "Warning").locator(".level-count")).to_have_text(
        str(count)
    )


def test_search_shows_only_matching_messages_and_marks_the_match(context, rig):
    page = open_logs(context, rig)
    tag = marker("needle")
    log(rig, f"found {tag} here")
    log(rig, marker("hay"))

    search(page, tag.upper())  # whatever the case

    expect(page.page.locator(".log-row")).to_have_count(1)
    expect(page.page.locator(".log-row mark")).to_have_text(tag)
    expect(page.page.locator(".logs-count")).to_contain_text("1 of ")


def test_escape_clears_the_search(context, rig):
    page = open_logs(context, rig)
    search(page, "nothing will match this")
    expect(page.page.get_by_text("No messages match.")).to_be_visible()

    page.page.get_by_role("searchbox", name="Search the log").press("Escape")

    expect(page.page.get_by_text("No messages match.")).to_have_count(0)
    expect(page.page.locator(".log-row").first).to_be_visible()


def test_the_filters_can_be_cleared_when_nothing_matches(context, rig):
    page = open_logs(context, rig)
    level_toggle(page, "Info").click()
    search(page, "nothing will match this")

    page.page.get_by_role("button", name="Clear the filters").click()

    expect(level_toggle(page, "Info")).to_have_attribute("aria-pressed", "true")
    expect(page.page.get_by_role("searchbox", name="Search the log")).to_have_value("")


def test_the_filters_last_for_the_session(context, rig):
    page = open_logs(context, rig)
    level_toggle(page, "Debug").click()
    search(page, "kept")

    page.page.reload()
    page.page.wait_for_function("window.pyacquisition?.logs?.status === 'live'")

    expect(level_toggle(page, "Debug")).to_have_attribute("aria-pressed", "false")
    expect(page.page.get_by_role("searchbox", name="Search the log")).to_have_value(
        "kept"
    )


# -------------------------------------------------------------- a busy log
def test_a_busy_log_draws_only_the_rows_in_view_and_filters_quickly(context, rig):
    page = open_logs(context, rig)
    tag = marker("busy")
    log(rig, tag + " {n}", count=3000)
    page.page.wait_for_function(
        f"window.pyacquisition.logs.entries.some(e => e.message === '{tag} 2999')"
    )
    expect(row(page, f"{tag} 2999")).to_have_count(1)

    assert page.page.locator(".log-row").count() < 100

    search(page, f"{tag} 1234")
    expect(page.page.locator(".log-row")).to_have_count(1)
    search(page, tag)
    expect(page.page.locator(".logs-count")).to_contain_text("3,000 of ")


def test_the_log_is_trimmed_to_what_the_server_keeps(context, rig):
    page = open_logs(context, rig)
    tag = marker("flood")
    log(rig, tag + " {n}", count=6000)
    page.page.wait_for_function(
        f"window.pyacquisition.logs.entries.at(-1).message === '{tag} 5999'"
    )

    kept = page.page.evaluate("window.pyacquisition.logs.entries.length")
    assert 4900 <= kept <= 5000


# -------------------------------------------------------------- following
def test_it_follows_new_messages_until_scrolled_up(context, rig):
    page = open_logs(context, rig)
    log(rig, marker("fill") + " {n}", count=200)
    last = marker("last")
    log(rig, last)
    expect(row(page, last)).to_be_visible()
    assert list_state(page)["fromBottom"] < 2
    expect(page.page.get_by_role("button", name="Jump to the latest message")).to_have_count(0)

    page.page.locator(".logs-list").hover()
    page.page.mouse.wheel(0, -600)
    latest = page.page.get_by_role("button", name="Jump to the latest message")
    expect(latest).to_be_visible()
    page.page.wait_for_timeout(300)  # the smooth scroll settles
    held = list_state(page)

    after = marker("after")
    log(rig, after + " {n}", count=50)
    page.page.wait_for_function(
        f"window.pyacquisition.logs.entries.at(-1).message === '{after} 49'"
    )
    page.page.wait_for_timeout(100)

    assert list_state(page)["firstInView"] == held["firstInView"]
    expect(latest).to_contain_text("newer")

    latest.click()

    expect(latest).to_have_count(0)
    expect(row(page, f"{after} 49")).to_be_visible()


def test_scrolling_up_a_list_too_short_to_scroll_keeps_following(context, rig):
    page = open_logs(context, rig)
    tag = marker("short")
    log(rig, tag)
    search(page, tag)
    expect(page.page.locator(".log-row")).to_have_count(1)

    page.page.locator(".logs-list").hover()
    page.page.mouse.wheel(0, -300)
    page.page.wait_for_timeout(200)

    expect(page.page.get_by_role("button", name="Jump to the latest message")).to_have_count(0)


def test_scrolling_back_to_the_bottom_follows_again(context, rig):
    page = open_logs(context, rig)
    log(rig, marker("fill") + " {n}", count=200)
    page.page.locator(".logs-list").hover()
    page.page.mouse.wheel(0, -600)
    latest = page.page.get_by_role("button", name="Jump to the latest message")
    expect(latest).to_be_visible()
    page.page.wait_for_timeout(300)  # the smooth scroll settles

    page.page.locator(".logs-list").evaluate("list => list.scrollTop = list.scrollHeight")

    expect(latest).to_have_count(0)
    text = marker("followed")
    log(rig, text)
    expect(row(page, text)).to_be_visible()


def test_a_held_view_stays_on_the_same_row_when_rows_above_are_filtered(context, rig):
    page = open_logs(context, rig)
    tag = marker("mixed")
    # Debug and info messages alternating, so hiding debug removes rows above.
    for n in range(100):
        log(rig, f"{tag} {n}", level="debug" if n % 2 else "info")
    page.page.wait_for_function(
        f"window.pyacquisition.logs.entries.at(-1).message === '{tag} 99'"
    )
    # Scrolled up so an info message (which survives the filter) is at the top.
    page.page.locator(".logs-list").evaluate(
        f"""list => {{
            const entries = window.pyacquisition.logs.entries;
            const index = entries.findIndex(e => e.message === '{tag} 40');
            list.scrollTop = index * 22;
        }}"""
    )
    expect(page.page.get_by_role("button", name="Jump to the latest message")).to_be_visible()
    held = list_state(page)["firstInView"]
    assert page.page.locator(f".log-row[data-seq='{held}']").inner_text().endswith(
        f"{tag} 40"
    )

    level_toggle(page, "Debug").click()

    expect(row(page, f"{tag} 41")).to_have_count(0)
    assert list_state(page)["firstInView"] == held


def test_a_held_view_stays_on_the_same_row_when_old_rows_are_trimmed(context, rig):
    page = open_logs(context, rig)
    tag = marker("base")
    log(rig, tag + " {n}", count=300)
    page.page.wait_for_function(
        f"window.pyacquisition.logs.entries.at(-1).message === '{tag} 299'"
    )
    page.page.locator(".logs-list").evaluate(
        f"""list => {{
            const entries = window.pyacquisition.logs.entries;
            const index = entries.findIndex(e => e.message === '{tag} 250');
            list.scrollTop = index * 22;
        }}"""
    )
    expect(page.page.get_by_role("button", name="Jump to the latest message")).to_be_visible()
    held = list_state(page)["firstInView"]
    # A limit of what the page has now, so every message after this trims some.
    page.page.evaluate(
        "window.pyacquisition.logs.maxEntries = window.pyacquisition.logs.entries.length"
    )

    after = marker("trimming")
    log(rig, after + " {n}", count=100)
    page.page.wait_for_function(
        f"window.pyacquisition.logs.entries.at(-1).message === '{after} 99'"
    )
    page.page.wait_for_timeout(100)

    assert list_state(page)["firstInView"] == held


# -------------------------------------------------------------- one message
def test_clicking_a_row_shows_the_whole_message(context, rig):
    page = open_logs(context, rig)
    text = marker("long") + " " + "word " * 120
    log(rig, text)

    row(page, text[:20]).click()

    detail = page.page.get_by_role("region", name="Log message")
    expect(detail).to_contain_text(text.strip())

    detail.get_by_role("button", name="Close the message").click()

    expect(detail).to_have_count(0)
