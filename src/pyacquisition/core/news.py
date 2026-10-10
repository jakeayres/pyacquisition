"""News on startup: what is new since the last version seen on this PC, a newer
version on PyPI, and, from the maker's feed, notices of serious fixes and the
maker's news. The page asks for it at `/news` and shows it as a card.

What's new comes from the changelog shipped in the package, so it needs no
network. The rest is fetched in the background, at most once a day, when a page
first asks, and never in a frozen app. Nothing about the user is sent. Each user
keeps what they have seen, and their choices, in one small file (`news.json`).

The environment can change it:

- `PYACQUISITION_NEWS`: `all` (the default), `updates` (no news from the maker),
  or `off` (nothing fetched, and no card).
- `PYACQUISITION_NEWS_FEED`: a feed's address, or a file, in place of the
  maker's, to preview a message before it is published.
- `PYACQUISITION_NEWS_DIR`: the folder for `news.json`, in place of the user's
  application data folder.

See docs/reference/news.md.
"""

import datetime
import hashlib
import json
import os
import re
import sys
import threading
import time
from importlib.metadata import PackageNotFoundError, version as installed
from pathlib import Path

import requests
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .logging import logger

# Where the newest version is read from.
PYPI_URL = "https://pypi.org/pypi/pyacquisition/json"
# The maker's feed of fixes and news: `news/feed.json` in the public repository,
# so every message it has held can be read there. Every copy of this version
# reads this address for good, so the file must stay at it.
FEED_URL: str | None = (
    "https://raw.githubusercontent.com/jakeayres/pyacquisition/main/news/feed.json"
)
# What the maker's news is labelled with, until the maker's name is known.
MAKER_LABEL = "From the maker"
# The changelog on the docs site, which what's new and updates link to.
CHANGELOG_URL = "https://pyacquisition.readthedocs.io/en/latest/reference/changelog/"
# The ways to update, the one the docs install with (uv) first and recommended.
UPGRADES = (
    {"label": "uv", "command": "uv sync --upgrade-package pyacquisition", "recommended": True},
    {"label": "pip", "command": "pip install --upgrade pyacquisition", "recommended": False},
)

TIMEOUT = 5.0  # seconds, for each request
FETCH_EVERY = 24 * 3600  # seconds a fetch is reused for
FEED_LIMIT = 64 * 1024  # bytes
PYPI_LIMIT = 16 * 1024 * 1024  # bytes: PyPI's JSON lists every release's files
IMAGE_LIMIT = 1024 * 1024  # bytes
MESSAGES_LIMIT = 20  # feed entries looked at
SEEN_KEPT = 500  # ids remembered as seen

MODES = ("all", "updates", "off")
LABELS = {"fix": "Fix", "update": "Update", "whats_new": "What's new", "news": MAKER_LABEL}
ORDER = {"fix": 0, "update": 1, "whats_new": 2, "news": 3}
# The kinds that come back each run, after being closed, until "Don't show
# again" is chosen. The others are shown once.
COMES_BACK = ("fix", "update")

_CHANGELOG = Path(__file__).resolve().parent.parent / "changelog.md"
_ID = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_IMAGE_FILE = re.compile(r"^[0-9a-f]{20}\.(png|jpg)$")
_IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg"}


# ------------------------------------------------------------------ versions
_VERSION = re.compile(
    r"^\s*v?(?P<release>\d+(?:\.\d+)*)"
    r"(?:[.-]?(?P<pre>dev|a|b|rc)(?P<n>\d*))?"
    r"(?:\+[A-Za-z0-9.]*)?\s*$"
)
_PRE = {"dev": 0, "a": 1, "b": 2, "rc": 3, None: 4}  # a release after all of these
FINAL = _PRE[None]


def version_key(text) -> tuple | None:
    """A version as something that sorts: `0.4.0.dev3` before `0.4.0rc1` before
    `0.4.0`. A local part (`+g1a2b3c4`) is ignored. None if it isn't a version."""
    match = _VERSION.match(text) if isinstance(text, str) else None
    if not match:
        return None
    release = [int(part) for part in match["release"].split(".")]
    release += [0] * (3 - len(release))
    return (tuple(release), _PRE[match["pre"]], int(match["n"] or 0))


def release_of(text) -> str | None:
    """The release a version is of, or on its way to: `0.4.0` for `0.4.0.dev3`."""
    key = version_key(text)
    return None if key is None else ".".join(str(part) for part in key[0])


_COMPARISON = re.compile(r"^\s*(<=|>=|==|!=|<|>)\s*(\S+)\s*$")
_COMPARE = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _comparisons(spec: str) -> list:
    """`>=0.3.0,<0.3.3` as [(operator, key)]. Raises ValueError if it isn't one."""
    found = []
    for part in spec.split(","):
        match = _COMPARISON.match(part)
        key = version_key(match[2]) if match else None
        if key is None:
            raise ValueError(f"{spec!r} isn't a list of comparisons such as <0.3.3")
        found.append((match[1], key))
    return found


def in_range(text, spec: str | None) -> bool:
    """Whether a version is in a range such as `>=0.3.0,<0.3.3`. Any version is
    in no range (None), and no version (None) is in any other."""
    if not spec:
        return True
    key = version_key(text)
    if key is None:
        return False
    return all(_COMPARE[op](key, other) for op, other in _comparisons(spec))


def installed_version() -> str | None:
    try:
        return installed("pyacquisition")
    except PackageNotFoundError:
        return None


# ----------------------------------------------------------------- changelog
_HEADING = re.compile(r"^##\s+v?(\S+)(?:\s+\((.*)\))?\s*$")


def read_changelog(text: str) -> list[dict]:
    """Each version's section of the changelog, as written (newest first): its
    `version`, its `date` (or what the heading says instead, such as
    "unreleased") and its `highlights`, the points under `### Highlights`."""
    versions = []
    current = None
    in_highlights = False
    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading and version_key(heading[1]) is not None:
            current = {"version": heading[1], "date": heading[2], "highlights": []}
            versions.append(current)
            in_highlights = False
        elif line.startswith("#"):
            in_highlights = current is not None and line.strip().lower() == "### highlights"
        elif in_highlights:
            if line.startswith(("- ", "* ")):
                current["highlights"].append(line[2:].strip())
            elif line.startswith("  ") and line.strip() and current["highlights"]:
                current["highlights"][-1] += " " + line.strip()
    return versions


# ------------------------------------------------------------------- fetching
def fetch_bytes(url: str, limit: int) -> bytes:
    """What an https address answers, if it is at most `limit` bytes. Raises an
    error otherwise. The tests replace it."""
    with requests.get(url, timeout=TIMEOUT, stream=True) as response:
        response.raise_for_status()
        content = b""
        for chunk in response.iter_content(64 * 1024):
            content += chunk
            if len(content) > limit:
                raise ValueError(f"{url} is over {limit} bytes")
        return content


def _is_https(text) -> bool:
    return isinstance(text, str) and text.startswith("https://") and len(text) <= 2000


def _text(value, longest: int, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > longest:
        raise ValueError(f"expected text of at most {longest} characters")
    return value.strip()


def _date(value) -> datetime.date | None:
    if value is None:
        return None
    return datetime.date.fromisoformat(value)


def clean_message(entry, local: bool = False) -> dict:
    """A feed entry, checked: `id`, `kind` (`fix` or `news`), `title` and
    `text`, and optionally `versions`, `from`, `until`, `link` and `image`.
    Raises ValueError, saying why, if it won't do. An image's address may be a
    file only in a `local` feed (a preview)."""
    if not isinstance(entry, dict):
        raise ValueError("an entry is an object")
    if not isinstance(entry.get("id"), str) or not _ID.match(entry["id"]):
        raise ValueError("its id is letters, digits, '.', '_' and '-'")
    if entry.get("kind") not in ("fix", "news"):
        raise ValueError("its kind is 'fix' or 'news'")
    message = {
        "id": entry["id"],
        "kind": entry["kind"],
        "title": _text(entry.get("title"), 200),
        "text": _text(entry.get("text"), 4000),
    }
    versions = entry.get("versions")
    if versions is not None:
        if not isinstance(versions, str):
            raise ValueError("its versions are text, such as <0.3.3")
        _comparisons(versions)
        message["versions"] = versions
    for when in ("from", "until"):
        if entry.get(when) is not None:
            message[when] = _date(entry[when]).isoformat()
    link = entry.get("link")
    if link is not None:
        if not isinstance(link, dict) or not _is_https(link.get("url")):
            raise ValueError("its link has an https url")
        message["link"] = {"label": _text(link.get("label"), 80), "url": link["url"]}
    image = entry.get("image")
    if image is not None:
        url = image.get("url") if isinstance(image, dict) else None
        if not (_is_https(url) or (local and isinstance(url, str) and url.strip())):
            raise ValueError("its image has an https url")
        message["image"] = {"url": url, "alt": _text(image.get("alt"), 300)}
    return message


def image_type(data: bytes) -> str | None:
    """`png` or `jpg`, from an image's first bytes, or None for anything else."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    return None


class Message(BaseModel):
    id: str


class Choices(BaseModel):
    maker_news: bool


class News:
    """
    The news for this run, and the user's file it keeps what they have seen in.

    The environment is read each time it is asked, so it can change while it runs
    (as the tests change it).
    """

    def __init__(
        self,
        version: str | None = None,
        busy=None,
        frozen: bool | None = None,
        changelog: str | None = None,
    ):
        """
        Args:
            version (str | None): The running version. By default, the installed
                one.
            busy (callable | None): Whether a task is running, during which the
                maker's news waits.
            frozen (bool | None): Whether this is a frozen app, which fetches
                nothing. By default, whether PyInstaller made it.
            changelog (str | None): The changelog's text. By default, the
                shipped `changelog.md`.
        """
        self.version = version if version is not None else installed_version()
        self._busy = busy or (lambda: False)
        self._frozen = getattr(sys, "frozen", False) if frozen is None else frozen
        self._changelog = changelog
        self._lock = threading.Lock()
        self._fetch_thread = None
        self._fetch_started = False
        self._closed = set()  # the fixes and updates closed in this run
        self._warned = set()

    # -------------------------------------------------------------- settings
    def mode(self) -> str:
        """`all`, `updates` or `off`, from PYACQUISITION_NEWS."""
        mode = os.environ.get("PYACQUISITION_NEWS", "all").strip().lower() or "all"
        if mode not in MODES:
            self._warn_once(
                f"PYACQUISITION_NEWS is {mode!r}, which isn't one of all, updates or "
                "off, so all is used."
            )
            return "all"
        return mode

    def folder(self) -> Path:
        """Where `news.json` is kept: PYACQUISITION_NEWS_DIR, or the user's
        application data folder."""
        chosen = os.environ.get("PYACQUISITION_NEWS_DIR")
        if chosen:
            return Path(chosen)
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
        else:
            base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
        return Path(base) / "pyacquisition"

    def feed_source(self) -> str | None:
        """The feed's address or file: PYACQUISITION_NEWS_FEED, or the maker's."""
        return os.environ.get("PYACQUISITION_NEWS_FEED") or FEED_URL

    def _warn_once(self, message: str) -> None:
        if message not in self._warned:
            self._warned.add(message)
            logger.warning(f"[News] {message}")

    # ---------------------------------------------------------- the user's file
    def _path(self) -> Path:
        return self.folder() / "news.json"

    def _load(self) -> dict:
        try:
            data = json.loads(self._path().read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self, data: dict) -> None:
        path = self._path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            spare = path.with_suffix(".tmp")
            spare.write_text(json.dumps(data, indent=1), encoding="utf-8")
            os.replace(spare, path)
        except OSError as error:
            logger.debug(f"[News] Couldn't write {path}: {error}")

    # ---------------------------------------------------------------- messages
    def _changelog_versions(self) -> list[dict]:
        text = self._changelog
        if text is None:
            try:
                text = _CHANGELOG.read_text(encoding="utf-8")
            except OSError:
                return []
        return read_changelog(text)

    def whats_new(self, since: str | None) -> dict | None:
        """What's new in the releases after the one `since` is of, up to the one
        the running version is of, or, with `since` None, in that release alone.
        Releases, not versions, so a development build shows its coming
        release's, and only once. None if there is nothing."""
        running = version_key(self.version)
        if running is None:
            return None
        after = version_key(since)[0] if version_key(since) else None
        sections = [
            {"version": entry["version"], "points": entry["highlights"]}
            for entry in self._changelog_versions()
            if entry["highlights"]
            and (release := version_key(entry["version"])[0]) <= running[0]
            and (release > after if after is not None else release == running[0])
        ]
        if not sections:
            return None
        newest = sections[0]["version"]
        title = (
            f"What's new in {newest}" if len(sections) == 1 else f"What's new since {since}"
        )
        return self._message(
            id=f"whats-new-{release_of(self.version)}",
            kind="whats_new",
            title=title,
            sections=sections,
            link={"label": "The whole changelog", "url": CHANGELOG_URL},
        )

    def _update(self, latest: str | None) -> dict | None:
        if version_key(latest) is None or version_key(self.version) is None:
            return None
        if version_key(latest) <= version_key(self.version):
            return None
        return self._message(
            id=f"update-{latest}",
            kind="update",
            title=f"PyAcquisition {latest} is out",
            text=(
                f"You have {self.version}. Stop the experiment, then run one of these "
                "in your project's folder:"
            ),
            commands=[dict(upgrade) for upgrade in UPGRADES],
            link={"label": "What's changed", "url": CHANGELOG_URL},
        )

    def _from_feed(self, entry: dict, images: dict) -> dict | None:
        today = datetime.date.today().isoformat()
        try:
            if not in_range(self.version, entry.get("versions")):
                return None
        except ValueError:
            return None
        if entry.get("from") and today < entry["from"]:
            return None
        if entry.get("until") and today > entry["until"]:
            return None
        image = None
        if entry.get("image") and entry["id"] in images:
            image = {"src": f"/news/image/{entry['id']}", "alt": entry["image"]["alt"]}
        return self._message(
            id=entry["id"],
            kind=entry["kind"],
            title=entry["title"],
            text=entry["text"],
            link=entry.get("link"),
            image=image,
            important=entry["kind"] == "fix",
        )

    @staticmethod
    def _message(
        id, kind, title, text="", sections=None, commands=None, link=None, image=None,
        important=False,
    ) -> dict:
        return {
            "id": id,
            "kind": kind,
            "label": LABELS[kind],
            "title": title,
            "text": text,
            "sections": sections or [],
            "commands": commands or [],
            "link": link,
            "image": image,
            "important": important,
            "comes_back": kind in COMES_BACK,
        }

    # ------------------------------------------------------------------ state
    def state(self) -> dict:
        """What `GET /news` answers: `show`, the messages to show now, in order;
        `all`, every current one, for What's new; the `mode`; whether the user
        wants the maker's news (`maker_news`); whether a fetch is still going
        (`pending`); and whether the maker's news is waiting for the running task
        (`waiting`)."""
        mode = self.mode()
        if mode == "off":
            current = self.whats_new(None)
            return {
                "show": [],
                "all": [current] if current else [],
                "mode": mode,
                "maker_news": False,
                "pending": False,
                "waiting": False,
            }
        with self._lock:
            data = self._load()
            if "version" not in data and self.version is not None:
                # A new install: everything is new, so nothing is shown as new.
                data["version"] = self.version
                self._save(data)
        self._start_fetch(mode, data)
        messages, unseen, current, maker_news = self._messages(data, mode)
        seen = set(data.get("seen") or []) | self._closed

        def ordered(found):
            return sorted((m for m in found if m), key=lambda m: ORDER[m["kind"]])

        busy = bool(self._busy())
        show = []
        waiting = False
        for message in ordered(messages + [unseen]):
            if message["id"] in seen:
                continue
            if message["kind"] == "news" and busy:
                waiting = True
                continue
            show.append(message)
        return {
            "show": show,
            "all": ordered(messages + [current]),
            "mode": mode,
            "maker_news": maker_news,
            "pending": self.pending,
            "waiting": waiting,
        }

    def _messages(self, data: dict, mode: str):
        """The current messages from the user's file: the update and the
        feed's, what's new since the last version seen (or None), what's new for
        What's new, and whether the maker's news is wanted."""
        fetched = data.get("fetched") or {}
        maker_news = mode == "all" and data.get("maker_news", True) is not False
        messages = []
        update = self._update(fetched.get("latest"))
        if update:
            messages.append(update)
        images = fetched.get("images") or {}
        for entry in fetched.get("messages") or []:
            message = self._from_feed(entry, images)
            if message and (message["kind"] == "fix" or maker_news):
                messages.append(message)
        # What's new since the last version seen, if there is any, to show; and
        # for What's new, that or else what is new in this release.
        unseen = self.whats_new(data.get("version")) if data.get("version") else None
        current = unseen or self.whats_new(None)
        return messages, unseen, current, maker_news

    @property
    def pending(self) -> bool:
        """Whether the fetch this run started is still going."""
        return self._fetch_thread is not None and self._fetch_thread.is_alive()

    def close(self, message_id: str) -> None:
        """A card was closed. A fix or an update is hidden for this run, and
        comes back next run. Anything else isn't shown again (see `seen`)."""
        messages, *_ = self._messages(self._load(), self.mode())
        kinds = {message["id"]: message["kind"] for message in messages}
        if kinds.get(message_id) in COMES_BACK:
            self._closed.add(message_id)
        else:
            self.seen(message_id)

    def seen(self, message_id: str) -> None:
        """Marks a message as seen on this PC, so it isn't shown again: "Don't
        show again". What's new marks the running version as the last one seen."""
        with self._lock:
            data = self._load()
            if message_id.startswith("whats-new-"):
                if self.version is not None:
                    data["version"] = self.version
            else:
                seen = [i for i in data.get("seen") or [] if i != message_id]
                data["seen"] = (seen + [message_id])[-SEEN_KEPT:]
            self._save(data)

    def choose(self, maker_news: bool) -> None:
        """Whether this user wants the maker's news."""
        with self._lock:
            data = self._load()
            data["maker_news"] = bool(maker_news)
            self._save(data)

    def image(self, message_id: str) -> tuple[Path, str] | None:
        """The cached image of a message, and its media type, or None."""
        name = ((self._load().get("fetched") or {}).get("images") or {}).get(message_id)
        if not isinstance(name, str) or not _IMAGE_FILE.match(name):
            return None
        path = self.folder() / "news-images" / name
        if not path.is_file():
            return None
        return path, _IMAGE_TYPES[name.rsplit(".", 1)[1]]

    # --------------------------------------------------------------- fetching
    def _start_fetch(self, mode: str, data: dict) -> None:
        """Starts the background fetch, once a run, if the last one is over a day
        old (or the feed is a preview, which is always fetched again)."""
        if self._frozen or mode == "off" or self._fetch_started:
            return
        self._fetch_started = True
        source = self.feed_source()
        fetched = data.get("fetched") or {}
        preview = bool(os.environ.get("PYACQUISITION_NEWS_FEED"))
        fresh = (
            time.time() - fetched.get("at", 0) < FETCH_EVERY
            and fetched.get("source") == source
        )
        if fresh and not preview:
            return
        self._fetch_thread = threading.Thread(
            target=self.fetch, args=(source,), name="news", daemon=True
        )
        self._fetch_thread.start()

    def fetch(self, source: str | None) -> None:
        """Fetches the newest version and the feed, with its images, and keeps
        them in the user's file. What can't be had is kept from before."""
        latest = self._latest()
        feed = self._feed(source)
        with self._lock:
            data = self._load()
            before = data.get("fetched") or {}
            if latest is None and (feed is None or not source):
                return  # offline: try again next run
            messages, images = feed if feed is not None else (
                before.get("messages") or [],
                before.get("images") or {},
            )
            data["fetched"] = {
                "at": time.time(),
                "source": source,
                "latest": latest or before.get("latest"),
                "messages": messages,
                "images": images,
            }
            self._save(data)
        self._tidy_images(images)

    def _latest(self) -> str | None:
        """The newest release on PyPI, or None if it can't be had."""
        try:
            info = json.loads(fetch_bytes(PYPI_URL, PYPI_LIMIT))["info"]
            latest = info["version"]
        except Exception as error:  # noqa: BLE001 - offline, or PyPI answered oddly
            logger.debug(f"[News] Couldn't read the newest version: {error}")
            return None
        key = version_key(latest)
        return latest if key is not None and key[1] == FINAL else None

    def _feed(self, source: str | None):
        """The feed's checked messages and their cached images, as (messages,
        images), or None if it can't be had. No feed is no messages."""
        if not source:
            return [], {}
        local = not source.startswith(("https://", "http://"))
        try:
            if local:
                raw = Path(source).read_bytes()
                if len(raw) > FEED_LIMIT:
                    raise ValueError(f"{source} is over {FEED_LIMIT} bytes")
            elif not source.startswith("https://"):
                raise ValueError("a feed's address is https")
            else:
                raw = fetch_bytes(source, FEED_LIMIT)
            entries = json.loads(raw)["messages"]
            if not isinstance(entries, list):
                raise ValueError("its messages are a list")
        except Exception as error:  # noqa: BLE001 - offline, or a broken feed
            logger.debug(f"[News] Couldn't read the feed {source}: {error}")
            return None

        messages, images, ids = [], {}, set()
        for entry in entries[:MESSAGES_LIMIT]:
            try:
                message = clean_message(entry, local=local)
            except ValueError as error:
                logger.debug(f"[News] Skipped a feed entry: {error}")
                continue
            if message["id"] in ids:
                continue
            ids.add(message["id"])
            messages.append(message)
            if "image" in message:
                name = self._fetch_image(message["image"]["url"], source if local else None)
                if name:
                    images[message["id"]] = name
        return messages, images

    def _fetch_image(self, url: str, feed_file: str | None) -> str | None:
        """Keeps an image in the user's cache, and gives its file's name, or None
        if it won't do: over 1 MB, or not a PNG or a JPEG."""
        try:
            if url.startswith("https://"):
                data = fetch_bytes(url, IMAGE_LIMIT)
            elif feed_file is not None and not url.startswith(("http://", "https://")):
                path = Path(feed_file).parent / url
                data = path.read_bytes()
                if len(data) > IMAGE_LIMIT:
                    raise ValueError(f"{path} is over {IMAGE_LIMIT} bytes")
            else:
                raise ValueError("an image's address is https")
            kind = image_type(data)
            if kind is None:
                raise ValueError("it isn't a PNG or a JPEG")
            name = f"{hashlib.sha256(url.encode()).hexdigest()[:20]}.{kind}"
            folder = self.folder() / "news-images"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(data)
            return name
        except Exception as error:  # noqa: BLE001 - offline, or an image that won't do
            logger.debug(f"[News] Couldn't keep the image {url}: {error}")
            return None

    def _tidy_images(self, images: dict) -> None:
        """Deletes the cached images that no message has any more."""
        folder = self.folder() / "news-images"
        keep = set(images.values())
        try:
            for path in folder.iterdir():
                if _IMAGE_FILE.match(path.name) and path.name not in keep:
                    path.unlink()
        except OSError:
            pass

    # -------------------------------------------------------------- endpoints
    def register_endpoints(self, app) -> None:
        """Adds `/news` and its endpoints to a FastAPI app."""

        @app.get("/news", tags=["news"])
        async def news():
            """
            What to show: `show`, the messages to show now, most important first;
            `all`, every current one, for What's new; `mode` (all, updates or off,
            from PYACQUISITION_NEWS); `maker_news`, whether the maker's news is
            shown; `pending`, whether a fetch is still going (ask again when it
            isn't); and `waiting`, whether the maker's news waits for a running
            task. A message has `id`, `kind` (whats_new, update, fix or news),
            `label`, `title`, `text`, `sections`, `commands`, `link`, `image`,
            `important` and `comes_back` (a fix or an update, shown each run until
            Don't show again).
            """
            return {"status": 200, "data": self.state()}

        @app.post("/news/close", tags=["news"])
        async def news_close(message: Message):
            """A card was closed. A fix or an update comes back next run (until
            `/news/seen`). Anything else isn't shown again on this PC."""
            self.close(message.id)
            return {"status": 200}

        @app.post("/news/seen", tags=["news"])
        async def news_seen(message: Message):
            """Don't show a message again on this PC, whatever its kind."""
            self.seen(message.id)
            return {"status": 200}

        @app.post("/news/choices", tags=["news"])
        async def news_choices(choices: Choices):
            """Whether this PC's user wants the maker's news (`maker_news`)."""
            self.choose(choices.maker_news)
            return {"status": 200}

        @app.get("/news/image/{message}", tags=["news"])
        async def news_image(message: str):
            """A message's image, kept on this PC when the feed was fetched."""
            found = self.image(message)
            if found is None:
                raise HTTPException(status_code=404, detail="No such image.")
            path, media_type = found
            return FileResponse(path, media_type=media_type)
