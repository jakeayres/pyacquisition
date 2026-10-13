"""News on startup (core/news.py): what's new from the changelog, a newer version
from PyPI, the maker's feed of fixes and news with its images, the user's file,
the switches, and the endpoints.

Nothing here reaches the network: `fetch_bytes` is replaced by a fake web, and
the user's file is kept in a temporary folder.
"""

import datetime
import json
import struct
import time
import zlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pyacquisition import Experiment
from pyacquisition.core import news as news_module
from pyacquisition.core.news import (
    News,
    clean_message,
    image_type,
    in_range,
    read_changelog,
    release_of,
    version_key,
)

CHANGELOG = """# Changelog

Some words.

## 0.5.0 (unreleased)

### Highlights

- Five, with a [link](https://example.org/five)
  carried on to a second line.
- And `code`.

### Breaking changes

- Not a highlight.

## 0.4.0 (2026-11-02)

### Highlights

- Four.

## 0.3.4 (2026-10-09)

### Highlights

- Three point four.
"""


def png(width=2, height=1):
    """A real, tiny PNG."""
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    rows = b"".join(b"\x00" + b"\x40\x80\xc0" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


class FakeWeb:
    """The web, as `fetch_bytes` sees it: the pages it has, and offline for the rest."""

    def __init__(self):
        self.pages = {}
        self.asked = []

    def __call__(self, url, limit):
        self.asked.append(url)
        if url not in self.pages:
            raise ConnectionError("offline")
        if len(self.pages[url]) > limit:
            raise ValueError("too big")
        return self.pages[url]

    def pypi(self, version):
        self.pages[news_module.PYPI_URL] = json.dumps({"info": {"version": version}}).encode()


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Where the user's file is kept, with news turned on."""
    monkeypatch.setenv("PYACQUISITION_NEWS", "all")
    monkeypatch.setenv("PYACQUISITION_NEWS_DIR", str(tmp_path / "news"))
    monkeypatch.delenv("PYACQUISITION_NEWS_FEED", raising=False)
    monkeypatch.setattr(news_module, "FEED_URL", None)  # each test gives its own feed
    return tmp_path / "news"


@pytest.fixture
def web(monkeypatch):
    fake = FakeWeb()
    monkeypatch.setattr(news_module, "fetch_bytes", fake)
    return fake


def make(version="0.4.0", **options):
    return News(version=version, changelog=CHANGELOG, frozen=False, **options)


def settled(news):
    """The state once the fetch it starts has ended."""
    news.state()
    if news._fetch_thread is not None:
        news._fetch_thread.join(5)
    return news.state()


def user(home, **data):
    home.mkdir(parents=True, exist_ok=True)
    (home / "news.json").write_text(json.dumps(data), encoding="utf-8")


def stored(home):
    return json.loads((home / "news.json").read_text(encoding="utf-8"))


def kinds(messages):
    return [m["kind"] for m in messages]


def feed(tmp_path, monkeypatch, *messages):
    """A preview feed in a file, with these messages."""
    path = tmp_path / "feed" / "feed.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"messages": list(messages)}), encoding="utf-8")
    monkeypatch.setenv("PYACQUISITION_NEWS_FEED", str(path))
    return path


FIX = {"id": "fix-1", "kind": "fix", "versions": "<0.4.1", "title": "A fix", "text": "Update."}
NEWS = {"id": "tutorial", "kind": "news", "title": "A new tutorial", "text": "A [sweep](https://example.org/tutorial)."}


# ---------------------------------------------------------------- versions
def test_versions_sort_dev_and_previews_before_their_release():
    order = ["0.3.4", "0.4.0.dev3", "0.4.0.dev12+g1a2b3c", "0.4.0a1", "0.4.0rc1", "0.4.0", "0.4.1", "1.0"]
    assert sorted(order, key=version_key) == order
    assert version_key("1.0") == version_key("1.0.0")
    assert version_key("not a version") is None
    assert version_key(None) is None


def test_the_release_a_version_is_on_its_way_to():
    assert release_of("0.4.0.dev38+g23864d9") == "0.4.0"
    assert release_of("0.3.4") == "0.3.4"
    assert release_of("nonsense") is None


@pytest.mark.parametrize(
    "version, spec, expected",
    [
        ("0.3.2", "<0.3.3", True),
        ("0.3.3", "<0.3.3", False),
        ("0.3.4", ">=0.3.0,<0.3.5", True),
        ("0.2.9", ">=0.3.0,<0.3.5", False),
        ("0.4.0", "==0.4.0", True),
        ("0.4.0", "!=0.4.0", False),
        ("0.4.0.dev3", "<0.4.0", True),
        ("0.4.0", None, True),
        (None, "<1.0", False),
    ],
)
def test_a_version_in_a_range(version, spec, expected):
    assert in_range(version, spec) is expected


def test_a_range_that_is_not_one_is_refused():
    with pytest.raises(ValueError, match="comparisons"):
        in_range("0.4.0", "about 0.4")


# --------------------------------------------------------------- changelog
def test_the_changelog_gives_each_versions_highlights():
    versions = read_changelog(CHANGELOG)
    assert [(v["version"], v["date"]) for v in versions] == [
        ("0.5.0", "unreleased"),
        ("0.4.0", "2026-11-02"),
        ("0.3.4", "2026-10-09"),
    ]
    assert versions[0]["highlights"] == [
        "Five, with a [link](https://example.org/five) carried on to a second line.",
        "And `code`.",
    ]


def test_the_shipped_changelog_reads():
    versions = read_changelog(news_module._CHANGELOG.read_text(encoding="utf-8"))
    assert versions and all(v["highlights"] for v in versions)
    assert all(version_key(v["version"]) for v in versions)


def test_whats_new_since_an_older_version_lists_each_release_newest_first():
    message = make("0.5.0").whats_new("0.3.4")
    assert message["kind"] == "whats_new"
    assert message["title"] == "What's new since 0.3.4"
    assert [s["version"] for s in message["sections"]] == ["0.5.0", "0.4.0"]
    assert message["link"]["url"] == news_module.CHANGELOG_URL
    assert message["id"] == "whats-new-0.5.0"


def test_whats_new_in_one_release():
    assert make("0.4.0").whats_new("0.3.4")["title"] == "What's new in 0.4.0"
    assert make("0.4.0").whats_new(None)["title"] == "What's new in 0.4.0"


def test_a_development_build_shows_its_coming_release_once():
    assert make("0.5.0.dev7").whats_new("0.4.0")["sections"][0]["version"] == "0.5.0"
    assert make("0.5.0.dev9").whats_new("0.5.0.dev7") is None
    assert make("0.5.0").whats_new("0.5.0.dev9") is None


def test_nothing_is_new_without_a_section_or_a_version(monkeypatch):
    assert make("0.4.0").whats_new("0.4.0") is None
    assert make("0.9.0").whats_new(None) is None  # not in the changelog
    # No version given means the installed one, so that is made unknown too.
    monkeypatch.setattr(news_module, "installed_version", lambda: None)
    assert News(version=None, changelog=CHANGELOG).whats_new(None) is None


# --------------------------------------------------------- the user's file
def test_a_new_install_records_its_version_and_shows_nothing_new(home, web):
    state = settled(make("0.4.0"))
    assert state["show"] == []
    assert stored(home)["version"] == "0.4.0"
    assert kinds(state["all"]) == ["whats_new"]  # What's new lists this release's


def test_after_an_upgrade_whats_new_shows_until_it_is_closed(home, web):
    user(home, version="0.3.4")
    news = make("0.5.0")
    state = settled(news)
    assert kinds(state["show"]) == ["whats_new"]
    assert [s["version"] for s in state["show"][0]["sections"]] == ["0.5.0", "0.4.0"]

    news.seen("whats-new-0.5.0")
    assert stored(home)["version"] == "0.5.0"
    assert news.state()["show"] == []


def test_a_broken_or_unwritable_file_does_not_stop_it(home, web, tmp_path, monkeypatch):
    home.mkdir(parents=True)
    (home / "news.json").write_text("{not json", encoding="utf-8")
    assert settled(make())["show"] == []

    blocked = tmp_path / "a file, not a folder"
    blocked.write_text("", encoding="utf-8")
    monkeypatch.setenv("PYACQUISITION_NEWS_DIR", str(blocked))
    news = make()
    assert settled(news)["show"] == []
    news.seen("anything")
    news.choose(False)


def test_seen_is_kept_and_not_for_ever(home, web, monkeypatch):
    monkeypatch.setattr(news_module, "SEEN_KEPT", 3)
    news = make()
    for i in range(5):
        news.seen(f"m{i}")
    news.seen("m2")
    assert stored(home)["seen"] == ["m3", "m4", "m2"]


def test_the_folder_is_the_users_application_data(monkeypatch, tmp_path):
    monkeypatch.delenv("PYACQUISITION_NEWS_DIR", raising=False)
    monkeypatch.setattr(news_module.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    assert make().folder() == tmp_path / "Local" / "pyacquisition"
    monkeypatch.setattr(news_module.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    assert make().folder() == tmp_path / "share" / "pyacquisition"


# ------------------------------------------------------------------ updates
def test_a_newer_version_on_pypi_is_an_update(home, web):
    web.pypi("0.4.1")
    user(home, version="0.4.0")
    news = make("0.4.0")
    first = news.state()
    assert first["pending"] is True
    news._fetch_thread.join(5)
    state = news.state()
    assert state["pending"] is False
    (update,) = state["show"]
    assert update["kind"] == "update"
    assert update["id"] == "update-0.4.1"
    assert update["title"] == "PyAcquisition 0.4.1 is out"
    assert update["text"] == (
        "You have 0.4.0. Stop the experiment, then run one of these in your project's folder:"
    )
    assert update["commands"] == [
        {"label": "uv", "command": "uv sync --upgrade-package pyacquisition", "recommended": True},
        {"label": "pip", "command": "pip install --upgrade pyacquisition", "recommended": False},
    ]

    news.seen("update-0.4.1")
    assert news.state()["show"] == []


@pytest.mark.parametrize("latest", ["0.4.0", "0.3.9", "0.5.0rc1", "0.5.0.dev2"])
def test_no_update_for_the_same_an_older_or_a_preview_version(home, web, latest):
    web.pypi(latest)
    user(home, version="0.4.0")
    assert settled(make("0.4.0"))["show"] == []


def test_a_development_build_ahead_of_pypi_gets_no_update(home, web):
    web.pypi("0.3.4")
    user(home, version="0.4.0.dev38")
    assert kinds(settled(make("0.4.0.dev38"))["show"]) == []


def test_a_fetch_is_kept_for_a_day(home, web):
    web.pypi("0.4.1")
    user(home, version="0.4.0")
    settled(make("0.4.0"))
    assert web.asked == [news_module.PYPI_URL]

    again = make("0.4.0")  # the next run, the same day
    assert kinds(settled(again)["show"]) == ["update"]
    assert web.asked == [news_module.PYPI_URL]

    data = stored(home)
    data["fetched"]["at"] = time.time() - news_module.FETCH_EVERY - 1
    user(home, **data)
    settled(make("0.4.0"))
    assert len(web.asked) == 2


def test_offline_nothing_is_kept_and_it_tries_again_next_run(home, web):
    user(home, version="0.4.0")
    news = make("0.4.0")
    assert settled(news)["show"] == []
    assert "fetched" not in stored(home)
    settled(make("0.4.0"))
    assert len(web.asked) == 2


def test_one_run_fetches_once(home, web):
    web.pypi("0.4.1")
    news = make("0.4.0")
    settled(news)
    news.state()
    news.state()
    assert len(web.asked) == 1


# ------------------------------------------------- closing, and for good
def test_a_closed_fix_or_update_comes_back_next_run_until_dont_show_again(home, web, tmp_path, monkeypatch):
    feed(tmp_path, monkeypatch, FIX)
    web.pypi("0.4.1")
    user(home, version="0.4.0")
    news = make("0.4.0")
    state = settled(news)
    assert [(m["kind"], m["comes_back"]) for m in state["show"]] == [("fix", True), ("update", True)]

    news.close("fix-1")
    news.close("update-0.4.1")
    assert news.state()["show"] == []  # for the rest of this run
    assert "seen" not in stored(home)
    assert kinds(news.state()["all"]) == ["fix", "update", "whats_new"]  # What's new still lists them

    again = make("0.4.0")  # the next run
    assert kinds(again.state()["show"]) == ["fix", "update"]
    again.seen("fix-1")  # Don't show again
    again.seen("update-0.4.1")
    assert make("0.4.0").state()["show"] == []


def test_dont_show_again_for_an_update_is_for_that_version(home, web):
    web.pypi("0.4.1")
    user(home, version="0.4.0", seen=["update-0.4.1"], fetched={"at": 0, "source": None})
    assert settled(make("0.4.0"))["show"] == []
    web.pypi("0.4.2")
    data = stored(home)
    data["fetched"]["at"] = 0
    user(home, **data)
    assert [m["id"] for m in settled(make("0.4.0"))["show"]] == ["update-0.4.2"]


def test_closing_whats_new_or_the_makers_news_is_for_good(home, web, tmp_path, monkeypatch):
    feed(tmp_path, monkeypatch, NEWS)
    user(home, version="0.3.4")
    news = make("0.4.0")
    state = settled(news)
    assert [(m["kind"], m["comes_back"]) for m in state["show"]] == [("whats_new", False), ("news", False)]
    news.close("whats-new-0.4.0")
    news.close("tutorial")
    assert stored(home)["version"] == "0.4.0"
    assert stored(home)["seen"] == ["tutorial"]
    assert settled(make("0.4.0"))["show"] == []


# ------------------------------------------------------------------ switches
def test_off_fetches_nothing_writes_nothing_and_shows_nothing(home, web, monkeypatch):
    monkeypatch.setenv("PYACQUISITION_NEWS", "off")
    web.pypi("9.9.9")
    state = settled(make("0.4.0"))
    assert state["show"] == []
    assert kinds(state["all"]) == ["whats_new"]  # What's new still lists the changelog
    assert state["mode"] == "off"
    assert web.asked == []
    assert not home.exists()


def test_updates_leaves_out_the_makers_news_and_keeps_fixes(home, web, tmp_path, monkeypatch):
    monkeypatch.setenv("PYACQUISITION_NEWS", "updates")
    feed(tmp_path, monkeypatch, FIX, NEWS)
    user(home, version="0.4.0")
    state = settled(make("0.4.0"))
    assert kinds(state["show"]) == ["fix"]
    assert state["maker_news"] is False


def test_an_unknown_mode_is_all_with_a_warning(home, web, monkeypatch):
    monkeypatch.setenv("PYACQUISITION_NEWS", "sometimes")
    warnings = []
    monkeypatch.setattr(news_module.logger, "warning", warnings.append)
    news = make()
    assert news.mode() == "all"
    assert news.mode() == "all"
    assert len(warnings) == 1 and "sometimes" in warnings[0]


def test_a_frozen_app_fetches_nothing(home, web):
    web.pypi("9.9.9")
    news = News(version="0.4.0", changelog=CHANGELOG, frozen=True)
    assert settled(news)["show"] == []
    assert web.asked == []


# --------------------------------------------------------------------- feed
def test_a_fix_for_this_version_comes_first_and_is_important(home, web, tmp_path, monkeypatch):
    feed(tmp_path, monkeypatch, NEWS, FIX)
    web.pypi("0.4.1")
    user(home, version="0.3.4")
    state = settled(make("0.4.0"))
    assert kinds(state["show"]) == ["fix", "update", "whats_new", "news"]
    fix = state["show"][0]
    assert fix["important"] is True and fix["label"] == "Fix"
    assert state["show"][3]["label"] == news_module.MAKER_LABEL


def test_a_fix_for_other_versions_is_not_shown(home, web, tmp_path, monkeypatch):
    feed(tmp_path, monkeypatch, FIX)
    user(home, version="0.4.1")
    assert settled(make("0.4.1"))["show"] == []


def test_dates_say_when_a_message_shows(home, web, tmp_path, monkeypatch):
    today = datetime.date.today()
    feed(
        tmp_path,
        monkeypatch,
        {**NEWS, "id": "past", "until": str(today - datetime.timedelta(days=1))},
        {**NEWS, "id": "future", "from": str(today + datetime.timedelta(days=1))},
        {**NEWS, "id": "now", "from": str(today), "until": str(today)},
    )
    user(home, version="0.4.0")
    assert [m["id"] for m in settled(make())["show"]] == ["now"]


def test_the_makers_news_waits_while_a_task_runs(home, web, tmp_path, monkeypatch):
    feed(tmp_path, monkeypatch, FIX, NEWS)
    user(home, version="0.4.0")
    running = {"busy": True}
    news = make(busy=lambda: running["busy"])
    state = settled(news)
    assert kinds(state["show"]) == ["fix"]
    assert state["waiting"] is True
    assert kinds(state["all"]) == ["fix", "whats_new", "news"]
    running["busy"] = False
    state = news.state()
    assert kinds(state["show"]) == ["fix", "news"]
    assert state["waiting"] is False


def test_turning_off_the_makers_news_keeps_fixes(home, web, tmp_path, monkeypatch):
    feed(tmp_path, monkeypatch, FIX, NEWS)
    user(home, version="0.4.0")
    news = make()
    settled(news)
    news.choose(False)
    state = news.state()
    assert kinds(state["show"]) == ["fix"]
    assert "news" not in kinds(state["all"])
    assert state["maker_news"] is False
    news.choose(True)
    assert "news" in kinds(news.state()["show"])


def test_a_preview_feed_is_read_every_run(home, web, tmp_path, monkeypatch):
    path = feed(tmp_path, monkeypatch, NEWS)
    user(home, version="0.4.0")
    settled(make())
    path.write_text(json.dumps({"messages": [{**NEWS, "title": "Changed"}]}), encoding="utf-8")
    assert settled(make())["show"][0]["title"] == "Changed"


def test_the_makers_feed_at_its_address(home, web, monkeypatch):
    monkeypatch.setattr(news_module, "FEED_URL", "https://news.test/feed.json")
    web.pages["https://news.test/feed.json"] = json.dumps({"messages": [NEWS]}).encode()
    user(home, version="0.4.0")
    assert kinds(settled(make())["show"]) == ["news"]


def test_the_feed_is_the_file_in_the_public_repository():
    # Every copy of a version reads the address it shipped with, for good.
    assert news_module.FEED_URL == (
        "https://raw.githubusercontent.com/jakeayres/pyacquisition/main/news/feed.json"
    )
    feed = json.loads((news_module._CHANGELOG.parents[2] / "news" / "feed.json").read_text(encoding="utf-8"))
    for entry in feed["messages"]:
        clean_message(entry)  # every message in it keeps to the rules


def test_without_an_address_there_is_no_feed(home, web):
    user(home, version="0.4.0")
    settled(make())
    assert web.asked == [news_module.PYPI_URL]


def test_a_feed_that_cant_be_had_keeps_the_messages_from_before(home, web, monkeypatch):
    monkeypatch.setattr(news_module, "FEED_URL", "https://news.test/feed.json")
    web.pages["https://news.test/feed.json"] = json.dumps({"messages": [NEWS]}).encode()
    web.pypi("0.4.0")
    user(home, version="0.4.0")
    settled(make())
    del web.pages["https://news.test/feed.json"]
    data = stored(home)
    data["fetched"]["at"] = 0
    user(home, **data)
    assert kinds(settled(make())["show"]) == ["news"]


@pytest.mark.parametrize(
    "content",
    [b"{not json", json.dumps({"messages": "none"}).encode(), b" " * (65 * 1024)],
    ids=["not-json", "messages-not-a-list", "over-64-kb"],
)
def test_a_broken_feed_is_skipped(home, web, tmp_path, monkeypatch, content):
    path = feed(tmp_path, monkeypatch)
    path.write_bytes(content)
    user(home, version="0.4.0")
    assert settled(make())["show"] == []


def test_entries_that_wont_do_are_skipped_and_the_rest_kept(home, web, tmp_path, monkeypatch):
    feed(
        tmp_path,
        monkeypatch,
        {**NEWS, "id": "has spaces"},
        {**NEWS, "id": "advert", "kind": "advert"},
        {**NEWS, "id": "plain-link", "link": {"label": "Go", "url": "http://example.org"}},
        {**NEWS, "id": "no-alt", "image": {"url": "https://example.org/i.png"}},
        {**NEWS, "id": "bad-range", "versions": "soon"},
        "not an object",
        NEWS,
        {**NEWS, "title": "The same id again"},
    )
    user(home, version="0.4.0")
    state = settled(make())
    assert [(m["id"], m["title"]) for m in state["show"]] == [("tutorial", "A new tutorial")]


def test_a_message_is_checked_and_kept_as_data():
    message = clean_message(
        {**NEWS, "versions": ">=0.4", "until": "2027-01-31", "extra": "ignored",
         "link": {"label": "More", "url": "https://example.org"}}
    )
    assert message == {
        "id": "tutorial",
        "kind": "news",
        "title": "A new tutorial",
        "text": "A [sweep](https://example.org/tutorial).",
        "versions": ">=0.4",
        "until": "2027-01-31",
        "link": {"label": "More", "url": "https://example.org"},
    }
    with pytest.raises(ValueError, match="text"):
        clean_message({**NEWS, "title": "x" * 201})


# ------------------------------------------------------------------- images
def test_an_image_is_kept_on_this_pc_and_served(home, web, tmp_path, monkeypatch):
    web.pages["https://example.org/tutorial.png"] = png()
    feed(tmp_path, monkeypatch, {**NEWS, "image": {"url": "https://example.org/tutorial.png", "alt": "A new tutorial"}})
    user(home, version="0.4.0")
    news = make()
    (message,) = settled(news)["show"]
    assert message["image"] == {"src": "/news/image/tutorial", "alt": "A new tutorial"}
    path, media_type = news.image("tutorial")
    assert path.read_bytes() == png() and media_type == "image/png"
    assert path.parent == home / "news-images"


def test_a_preview_feeds_image_can_be_a_file_beside_it(home, web, tmp_path, monkeypatch):
    path = feed(tmp_path, monkeypatch, {**NEWS, "image": {"url": "tutorial.jpg", "alt": "A new tutorial"}})
    (path.parent / "tutorial.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\0" * 50)
    user(home, version="0.4.0")
    news = make()
    settled(news)
    assert news.image("tutorial")[1] == "image/jpeg"


@pytest.mark.parametrize(
    "url, content",
    [
        ("https://example.org/i.svg", b"<svg onload='alert(1)'></svg>"),
        ("https://example.org/big.png", png() + b"\0" * (1024 * 1024)),
        ("https://example.org/missing.png", None),
    ],
    ids=["svg", "over-1-mb", "missing"],
)
def test_an_image_that_wont_do_is_left_out_and_the_message_kept(home, web, tmp_path, monkeypatch, url, content):
    if content is not None:
        web.pages[url] = content
    feed(tmp_path, monkeypatch, {**NEWS, "image": {"url": url, "alt": "An image"}})
    user(home, version="0.4.0")
    news = make()
    (message,) = settled(news)["show"]
    assert message["image"] is None
    assert news.image("tutorial") is None


def test_a_remote_feeds_image_must_be_https(home, web, monkeypatch):
    monkeypatch.setattr(news_module, "FEED_URL", "https://news.test/feed.json")
    web.pages["https://news.test/feed.json"] = json.dumps(
        {"messages": [{**NEWS, "image": {"url": "tutorial.png", "alt": "A file"}}]}
    ).encode()
    user(home, version="0.4.0")
    assert settled(make())["show"] == []  # the entry is refused


def test_old_images_are_deleted_and_a_tampered_name_isnt_served(home, web, tmp_path, monkeypatch):
    web.pages["https://example.org/a.png"] = png()
    web.pages["https://example.org/b.png"] = png(3, 2)
    path = feed(tmp_path, monkeypatch, {**NEWS, "image": {"url": "https://example.org/a.png", "alt": "A"}})
    user(home, version="0.4.0")
    settled(make())
    path.write_text(json.dumps({"messages": [{**NEWS, "image": {"url": "https://example.org/b.png", "alt": "B"}}]}), encoding="utf-8")
    settled(make())
    assert len(list((home / "news-images").iterdir())) == 1

    data = stored(home)
    data["fetched"]["images"]["tutorial"] = "../news.json"
    user(home, **data)
    assert make().image("tutorial") is None


def test_image_types_by_their_first_bytes():
    assert image_type(png()) == "png"
    assert image_type(b"\xff\xd8\xff\xdb") == "jpg"
    assert image_type(b"GIF89a") is None
    assert image_type(b"<svg") is None


# ------------------------------------------------------------- fetch_bytes
class FakeResponse:
    def __init__(self, chunks, status=200):
        self.chunks = chunks
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status != 200:
            raise RuntimeError(f"HTTP {self.status}")

    def iter_content(self, size):
        yield from self.chunks


def test_fetch_bytes_stops_at_its_limit(monkeypatch):
    asked = {}

    def get(url, **options):
        asked.update(options)
        return FakeResponse([b"ab", b"cd"])

    monkeypatch.setattr(news_module.requests, "get", get)
    assert news_module.fetch_bytes("https://x.test", 4) == b"abcd"
    assert asked == {"timeout": news_module.TIMEOUT, "stream": True}
    with pytest.raises(ValueError, match="over 3 bytes"):
        news_module.fetch_bytes("https://x.test", 3)
    monkeypatch.setattr(news_module.requests, "get", lambda url, **o: FakeResponse([], 404))
    with pytest.raises(RuntimeError, match="404"):
        news_module.fetch_bytes("https://x.test", 3)


# ---------------------------------------------------------------- endpoints
def test_the_endpoints(home, web, tmp_path, monkeypatch):
    web.pages["https://example.org/tutorial.png"] = png()
    feed(tmp_path, monkeypatch, {**NEWS, "image": {"url": "https://example.org/tutorial.png", "alt": "A new tutorial"}})
    user(home, version="0.4.0")
    news = make()
    app = FastAPI()
    news.register_endpoints(app)
    client = TestClient(app)

    client.get("/news")
    news._fetch_thread.join(5)
    data = client.get("/news").json()["data"]
    assert kinds(data["show"]) == ["news"]
    image = client.get("/news/image/tutorial")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert client.get("/news/image/nothing").status_code == 404

    assert client.post("/news/close", json={"id": "tutorial"}).json() == {"status": 200}
    assert client.get("/news").json()["data"]["show"] == []
    assert stored(home)["seen"] == ["tutorial"]  # the maker's news, closed for good
    assert client.post("/news/seen", json={"id": "fix-9"}).json() == {"status": 200}
    assert stored(home)["seen"] == ["tutorial", "fix-9"]
    assert client.post("/news/choices", json={"maker_news": False}).json() == {"status": 200}
    assert stored(home)["maker_news"] is False
    assert client.post("/news/choices", json={}).status_code == 422


def test_the_experiment_serves_the_news_and_its_tasks_hold_the_makers_news(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    experiment._register_endpoints(experiment._api_server)
    paths = experiment._api_server.app.openapi()["paths"]
    assert {"/news", "/news/close", "/news/seen", "/news/choices", "/news/image/{message}"} <= set(paths)
    assert experiment._news._busy() is False
    experiment._task_manager._current_task = object()
    assert experiment._news._busy() is True


def test_the_setup_page_serves_the_news_too(tmp_path):
    from pyacquisition.core.setup import SetupServer

    server = SetupServer(tmp_path / "new.toml")
    assert "/news" in server.app.openapi()["paths"]


def test_the_window_opens_only_https_links(monkeypatch):
    from pyacquisition.gui.window import _Api

    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    api = _Api(owner=None)
    assert api.open_link("https://example.org") is True
    assert api.open_link("http://example.org") is False
    assert api.open_link("file:///C:/Windows") is False
    assert opened == ["https://example.org"]
