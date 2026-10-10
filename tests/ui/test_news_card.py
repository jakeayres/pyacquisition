"""The news card (news.js), on the experiment's page and the setup page: what's
new after an upgrade, an update, a fix and the maker's news, one at a time and
most important first; What's new; the maker's news waiting for a running task
and turned off; images; and links, which the window opens in the browser.

Each test has its own rig and its own user's file, which holds a fetch made
just now, so nothing is fetched and the messages are known.
"""

import json
import struct
import time
import zlib

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, Running, SetupRunning, SmokeExperiment

from pyacquisition.core import news as news_module
from pyacquisition.core.news import clean_message, read_changelog

# The newest release in the shipped changelog, and a build on its way to it, so
# that its highlights are what's new after an upgrade from an older version.
RELEASES = read_changelog(news_module._CHANGELOG.read_text(encoding="utf-8"))
NEWEST = RELEASES[0]["version"]
PREVIOUS = RELEASES[1]["version"]  # upgrading from it, only the newest is new
RUNNING = f"{NEWEST}.dev1"

FIX = clean_message(
    {"id": "fix-1", "kind": "fix", "title": "A serious fix", "text": "Please update. [Why](https://example.org/why)"}
)
NEWS = clean_message(
    {
        "id": "tutorial",
        "kind": "news",
        "title": "A new tutorial",
        "text": "A sweep inside a sweep, with a live map.",
        "link": {"label": "Read more", "url": "https://example.org/tutorial"},
    }
)


def png():
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    rows = b"".join(b"\x00" + b"\x40\x80\xc0" * 8 for _ in range(4))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 4, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


@pytest.fixture
def home(tmp_path, monkeypatch):
    """The user's folder, with news on, a running version, and no network."""
    folder = tmp_path / "news-home"
    monkeypatch.setenv("PYACQUISITION_NEWS", "all")
    monkeypatch.setenv("PYACQUISITION_NEWS_DIR", str(folder))
    monkeypatch.delenv("PYACQUISITION_NEWS_FEED", raising=False)
    monkeypatch.setattr(news_module, "FEED_URL", None)  # the user's file holds the messages
    monkeypatch.setattr(news_module, "installed_version", lambda: RUNNING)

    def offline(url, limit):
        raise ConnectionError("no network in the tests")

    monkeypatch.setattr(news_module, "fetch_bytes", offline)
    return folder


def user_file(home, version=PREVIOUS, messages=(), latest=None, images=None):
    """The user's file: the last version seen, and a fetch made just now."""
    home.mkdir(parents=True, exist_ok=True)
    data = {
        "version": version,
        "fetched": {
            "at": time.time(),
            "source": None,
            "latest": latest,
            "messages": list(messages),
            "images": images or {},
        },
    }
    (home / "news.json").write_text(json.dumps(data), encoding="utf-8")


def stored(home):
    return json.loads((home / "news.json").read_text(encoding="utf-8"))


def eventually(check, timeout=5.0):
    """Waits for the page's request to reach the user's file."""
    end = time.monotonic() + timeout
    while not check():
        assert time.monotonic() < end, "the user's file never got there"
        time.sleep(0.05)


@pytest.fixture
def rig(home, tmp_path):
    running = Running(SmokeExperiment, tmp_path / "rig")
    yield running
    running.stop()


def open_page(context, address, path="/"):
    page = Page(context.new_page())
    page.page.goto(f"{address}{path}")
    return page


def card(page):
    return page.page.get_by_role("region", name="News")


def open_whats_new(page):
    """Opens What's new from the palette."""
    page.page.keyboard.press("Control+k")
    palette = page.page.get_by_role("dialog", name="Command palette")
    expect(palette.get_by_role("option").first).to_be_visible()
    search = palette.get_by_role("searchbox")
    search.press_sequentially("whats new")
    expect(palette.get_by_role("option").first).to_contain_text("What's new")
    search.press("Enter")
    return page.page.get_by_role("dialog", name="What's new")


def kind(card_):
    """The card's kind, as it is written (the page shows it in capitals)."""
    return " ".join(card_.locator(".news-kind").text_content().split())


# ------------------------------------------------------------- what's new
def test_whats_new_after_an_upgrade_until_it_is_closed(context, home, rig):
    user_file(home, version=PREVIOUS)
    page = open_page(context, rig.address)

    expect(card(page)).to_contain_text(f"What's new in {NEWEST}")
    expect(card(page).locator(".news-kind")).to_have_text("What's new")
    card(page).get_by_role("button", name="Close").click()
    expect(card(page)).to_have_count(0)
    eventually(lambda: stored(home)["version"] == RUNNING)

    page.page.reload()
    page.page.get_by_role("status").filter(has_text="Connected").wait_for()
    page.page.wait_for_timeout(500)
    expect(card(page)).to_have_count(0)
    assert page.errors == []


def test_a_new_install_shows_no_card(context, home, rig):
    page = open_page(context, rig.address)
    page.page.get_by_role("status").filter(has_text="Connected").wait_for()
    page.page.wait_for_timeout(500)
    expect(card(page)).to_have_count(0)
    assert stored(home)["version"] == RUNNING


# --------------------------------------------- the most important first
def test_one_card_at_a_time_most_important_first(context, home, rig):
    user_file(home, version=PREVIOUS, messages=[NEWS, FIX], latest="99.0.0")
    page = open_page(context, rig.address)

    expect(card(page).locator(".news-kind")).to_have_text("Fix · Important")
    expect(card(page).locator(".news-title")).to_have_text("A serious fix")
    expect(card(page).get_by_role("button", name="3 more")).to_be_visible()

    order = []
    for _ in range(4):
        order.append(kind(card(page)))
        card(page).get_by_role("button", name="Close").click()
    assert order == ["Fix · Important", "Update", "What's new", news_module.MAKER_LABEL]
    expect(card(page)).to_have_count(0)
    # The fix and the update come back next run; the maker's news doesn't.
    eventually(lambda: stored(home).get("seen") == ["tutorial"])
    assert page.errors == []


def test_a_fix_or_update_comes_back_next_run_until_dont_show_again(context, home, tmp_path):
    user_file(home, version=RUNNING, messages=[FIX], latest="99.0.0")
    first = Running(SmokeExperiment, tmp_path / "first")
    try:
        page = open_page(context, first.address)
        expect(card(page).locator(".news-title")).to_have_text("A serious fix")
        card(page).get_by_role("button", name="Close").click()  # for this run
        expect(card(page).locator(".news-title")).to_have_text("PyAcquisition 99.0.0 is out")
        card(page).get_by_role("button", name="Don't show again").click()
        expect(card(page)).to_have_count(0)
        eventually(lambda: stored(home).get("seen") == ["update-99.0.0"])
        assert page.errors == []
    finally:
        first.stop()

    second = Running(SmokeExperiment, tmp_path / "second")  # the next run
    try:
        page = open_page(context, second.address)
        expect(card(page).locator(".news-title")).to_have_text("A serious fix")
        expect(card(page).get_by_role("button", name="Don't show again")).to_be_visible()
        expect(card(page).locator(".news-more")).to_have_count(0)  # the update isn't back
    finally:
        second.stop()


def test_more_opens_whats_new_with_everything(context, home, rig):
    user_file(home, version=PREVIOUS, messages=[NEWS, FIX], latest="99.0.0")
    page = open_page(context, rig.address)

    card(page).get_by_role("button", name="3 more").click()
    dialog = page.page.get_by_role("dialog", name="What's new")
    expect(dialog.locator(".news-item .news-title")).to_have_text(
        ["A serious fix", "PyAcquisition 99.0.0 is out", f"What's new in {NEWEST}", "A new tutorial"]
    )
    expect(dialog.locator(".news-command code")).to_have_text(
        ["uv sync --upgrade-package pyacquisition", "pip install --upgrade pyacquisition"]
    )
    page.page.keyboard.press("Escape")
    expect(dialog).to_have_count(0)


def test_whats_new_from_the_palette(context, home, rig):
    user_file(home, version=RUNNING)  # nothing to show, and What's new still lists the release
    page = open_page(context, rig.address)
    page.page.get_by_role("status").filter(has_text="Connected").wait_for()

    dialog = open_whats_new(page)
    expect(dialog.locator(".news-title")).to_have_text([f"What's new in {NEWEST}"])
    expect(dialog.get_by_label("Show news from the maker")).to_be_checked()


# ------------------------------------------------------ the maker's news
def test_the_makers_news_waits_for_a_running_task(context, home, rig):
    user_file(home, version=RUNNING, messages=[NEWS])
    rig.get("/tasks/waitfor", seconds=60)
    context.add_init_script("window.pyacquisitionNewsTimeScale = 0.02")
    page = open_page(context, rig.address)
    page.page.get_by_role("status").filter(has_text="Connected").wait_for()
    page.page.wait_for_timeout(1000)
    expect(card(page)).to_have_count(0)

    rig.get("/task_manager/abort")
    expect(card(page).locator(".news-title")).to_have_text("A new tutorial", timeout=10000)


def test_the_makers_news_can_be_turned_off_and_fixes_stay(context, home, rig):
    user_file(home, version=RUNNING, messages=[NEWS, FIX])
    page = open_page(context, rig.address)
    card(page).get_by_role("button", name="Close").click()  # the fix

    card(page).get_by_role("button", name="Don't show news from the maker").click()
    expect(card(page)).to_have_count(0)
    eventually(lambda: stored(home).get("maker_news") is False)

    dialog = open_whats_new(page)
    expect(dialog.get_by_label("Show news from the maker")).not_to_be_checked()
    expect(dialog.locator(".news-title")).to_have_text(["A serious fix", f"What's new in {NEWEST}"])


def test_off_shows_nothing_and_says_so(context, home, rig, monkeypatch):
    monkeypatch.setenv("PYACQUISITION_NEWS", "off")
    user_file(home, version=PREVIOUS, messages=[FIX], latest="99.0.0")
    page = open_page(context, rig.address)
    page.page.get_by_role("status").filter(has_text="Connected").wait_for()
    page.page.wait_for_timeout(500)
    expect(card(page)).to_have_count(0)

    dialog = open_whats_new(page)
    expect(dialog).to_contain_text("PYACQUISITION_NEWS is off")
    expect(dialog.get_by_label("Show news from the maker")).to_have_count(0)


# ------------------------------------------------------ images and links
def test_an_image_is_served_by_the_experiment(context, home, rig):
    folder = home / "news-images"
    folder.mkdir(parents=True)
    (folder / "0123456789abcdef0123.png").write_bytes(png())
    message = clean_message({**NEWS, "image": {"url": "https://example.org/x.png", "alt": "A new tutorial"}})
    user_file(home, version=RUNNING, messages=[message], images={"tutorial": "0123456789abcdef0123.png"})
    requests = []
    page = open_page(context, rig.address)
    page.page.on("request", lambda request: requests.append(request.url))

    image = card(page).get_by_role("img", name="A new tutorial")
    expect(image).to_have_attribute("src", "/news/image/tutorial")
    page.page.wait_for_function("document.querySelector('.news-image')?.naturalWidth === 8")
    assert all(url.startswith(rig.address) for url in requests)


def test_a_link_opens_through_the_window_and_the_page_stays(context, home, rig):
    user_file(home, version=RUNNING, messages=[NEWS])
    context.add_init_script(
        "window.pywebview = {api: {open_link: (url) => { window.opened = url; return true; }}}"
    )
    page = open_page(context, rig.address)

    card(page).get_by_role("link", name="Read more").click()
    assert page.page.evaluate("window.opened") == "https://example.org/tutorial"
    assert page.page.url.startswith(rig.address)


def test_in_a_browser_a_link_opens_a_new_tab(context, home, rig):
    user_file(home, version=RUNNING, messages=[NEWS])
    page = open_page(context, rig.address)
    link = card(page).get_by_role("link", name="Read more")
    expect(link).to_have_attribute("target", "_blank")
    expect(link).to_have_attribute("rel", "noopener noreferrer")


def test_the_update_offers_uv_first_and_pip_and_each_can_be_copied(context, home, rig):
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    user_file(home, version=RUNNING, latest="99.0.0")
    page = open_page(context, rig.address)

    expect(card(page).locator(".news-title")).to_have_text("PyAcquisition 99.0.0 is out")
    commands = card(page).locator(".news-command")
    expect(commands.locator(".news-command-label")).to_have_text(["uv", "pip"])
    expect(commands.first).to_have_attribute("data-recommended", "true")
    expect(commands.first.locator(".news-badge")).to_have_text("Recommended")
    expect(commands.nth(1).locator(".news-badge")).to_have_count(0)

    card(page).get_by_role("button", name="Copy the uv command").click()
    expect(commands.first.get_by_role("status")).to_have_text("Copied")
    assert page.page.evaluate("navigator.clipboard.readText()") == "uv sync --upgrade-package pyacquisition"
    card(page).get_by_role("button", name="Copy the pip command").click()
    page.page.wait_for_function("navigator.clipboard.readText().then((t) => t.startsWith('pip'))")


# -------------------------------------------------------- the setup page
def test_the_setup_page_shows_the_card_too(context, home, tmp_path):
    user_file(home, version=RUNNING, messages=[FIX])
    setup = SetupRunning(tmp_path / "new.toml")
    try:
        page = open_page(context, setup.address, "/ui/setup/")
        expect(card(page).locator(".news-title")).to_have_text("A serious fix")
        box = card(page).bounding_box()
        size = page.page.viewport_size
        assert box["x"] + box["width"] > size["width"] - 40  # in the window's corner
        assert box["y"] + box["height"] > size["height"] - 40
        assert page.errors == []
    finally:
        setup.stop()
