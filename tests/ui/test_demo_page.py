"""The front page's live demo (docs/demo/): the interface's own page, running in a
browser from a recording, with no experiment to connect to. Served as the docs
serve it: docs/demo/, with the interface's files copied in as app/.

The last test checks the recording against a live run of the experiment it was
made from, so a change to the API that the recording no longer matches fails
here. Record it again with `uv run --no-sync python scripts/record_demo.py`."""

import json
import re
import shutil
import sys

import pytest

pytest.importorskip("playwright")

import requests  # noqa: E402
from playwright.sync_api import expect  # noqa: E402
from ui_helpers import REPO, VIEWPORT, Page, Running, StaticSite, copy_interface  # noqa: E402

DEMO = REPO / "docs" / "demo"
GUI_JS = REPO / "src" / "pyacquisition" / "gui" / "static" / "js"
SESSION = json.loads((DEMO / "session.json").read_text(encoding="utf-8"))
MESSAGE = "This is a demo in the documentation"
NUMBER = re.compile(r"^-?\d+(\.\d+)?(e[-+]?\d+)?$")


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("demo")
    shutil.copytree(DEMO, root / "demo", ignore=shutil.ignore_patterns("app"))
    copy_interface(root / "demo" / "app")
    served = StaticSite(root)
    yield served
    served.stop()


@pytest.fixture
def opened(browser, site, request):
    """The demo, open and live: (page, every URL it asked for). Reduced motion is
    off unless the test is marked `still`, as the rows only move without it."""
    still = request.node.get_closest_marker("still") is not None
    context = browser.new_context(
        viewport=VIEWPORT, reduced_motion="reduce" if still else "no-preference"
    )
    asked, failed = [], []
    context.on("request", lambda r: asked.append(r.url))
    context.on("requestfailed", lambda r: failed.append(f"{r.url} {r.failure}"))
    page = Page(context.new_page())
    page.page.goto(f"{site.address}/demo/")
    try:
        page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    except Exception as error:
        unanswered = page.page.evaluate("window.pyacquisitionDemo?.unanswered ?? null")
        raise AssertionError(
            f"the demo never went live: errors {page.errors}, unanswered {unanswered}, "
            f"failed requests {failed}"
        ) from error
    yield page, asked
    context.close()


def seq(page):
    return page.page.evaluate("pyacquisitionDemo.seq")


def demo(page, script):
    return page.page.evaluate(f"pyacquisitionDemo.{script}")


# ------------------------------------------------------------ what it shows
def test_the_demo_runs_the_interface_from_the_recording(opened):
    page, _ = opened

    expect(page.page.locator(".brand-name")).to_have_text("MyExperiment")
    for name in SESSION["columns"]:
        expect(page.page.locator(f'.value-tile[data-column="{name}"]')).to_be_visible()
    expect(page.page.locator('.value-tile[data-column="T"] .value-unit')).to_have_text("K")
    expect(page.page.locator(".plot-panel")).to_have_count(2)
    expect(page.page.locator(".demo-banner")).to_contain_text("simulated instruments")

    before = seq(page)
    page.page.wait_for_timeout(1200)
    assert seq(page) > before, "the rows don't move"
    assert demo(page, "unanswered") == []
    assert page.errors == []


def test_the_queue_shows_the_recorded_cycle(opened):
    page, _ = opened
    page.page.get_by_role("tab", name="Queue").click()

    expect(page.page.get_by_text("Ramping temperature OUTPUT_1").first).to_be_visible()
    page.page.get_by_role("tab", name="Logs").click()
    expect(page.page.get_by_text("Adding task to queue").first).to_be_visible()
    assert page.errors == []


def instrument(page, uid):
    listed = page.page.get_by_role("list", name="Instruments")
    if not listed.is_visible():  # clicking the open tab again folds the dock away
        page.page.get_by_role("tab", name="Instruments").click()
    listed.get_by_role(
        "button", name=re.compile(f"^{uid}")
    ).click()


def method(page, name):
    page.page.locator(".method-item", has_text=re.compile(f"^{name}$")).click()
    expect(page.page.locator(".call-title")).to_have_text(re.compile(f"\\.{name}$"))


def test_the_instruments_are_the_real_drivers(opened):
    page, _ = opened
    page.page.get_by_role("tab", name="Instruments").click()

    items = page.page.get_by_role("list", name="Instruments").get_by_role("button")
    expect(items).to_have_count(3)
    expect(items.nth(1)).to_contain_text("SR_830")
    expect(items.nth(2)).to_contain_text("Lakeshore_350")


def test_a_measured_query_reads_the_latest_value(opened):
    page, _ = opened
    instrument(page, "lakeshore")
    method(page, "get_temperature")

    page.page.locator(".form-field[data-field='input_channel'] select").select_option("Input A")
    page.page.get_by_role("button", name="Read", exact=True).click()

    expect(page.page.locator(".result").first.locator(".result-value")).to_have_text(NUMBER)


def test_anything_else_answers_with_the_demo_message(opened):
    page, _ = opened
    instrument(page, "lakeshore")
    method(page, "get_temperature")
    page.page.locator(".form-field[data-field='input_channel'] select").select_option("Input B")
    page.page.get_by_role("button", name="Read", exact=True).click()
    expect(page.page.locator(".result.failed").first).to_contain_text(MESSAGE)

    instrument(page, "lockin")
    method(page, "set_frequency")
    page.page.locator(".form-field[data-field='frequency'] input").fill("137.5")
    page.page.get_by_role("button", name="Send", exact=True).click()
    expect(page.page.locator(".result.failed").first).to_contain_text(MESSAGE)
    assert demo(page, "unanswered") == []


def test_pausing_the_measurements_stops_the_rows(opened):
    page, _ = opened
    page.page.get_by_role("button", name="Pause measurements").click()
    expect(page.page.locator(".rack-control")).to_have_attribute("data-paused", "true")
    paused = seq(page)
    page.page.wait_for_timeout(800)
    assert seq(page) == paused

    page.page.get_by_role("button", name="Resume measurements").click()
    page.page.wait_for_timeout(800)
    assert seq(page) > paused


def test_nothing_is_asked_of_anywhere_but_the_docs(opened, site):
    page, asked = opened
    for tab in ("Queue", "Instruments", "Logs", "Values"):
        page.page.get_by_role("tab", name=tab).click()
    assert asked and all(url.startswith(site.address) for url in asked), [
        url for url in asked if not url.startswith(site.address)
    ]


# ------------------------------------------------------------ what it answers
def requested_paths():
    """Every fixed path the interface's code asks for (the setup page aside), with
    a part made from a variable as `x`."""
    paths = set()
    for path in GUI_JS.rglob("*.js"):
        if "setup" in path.relative_to(GUI_JS).parts:
            continue
        text = path.read_text(encoding="utf-8")
        for _, url in re.findall(r"""\b(?:get|post|getBinary|fetch)\(\s*([`"])(/.*?)\1""", text):
            paths.add(re.sub(r"\$\{[^}]*\}", "x", url).split("?")[0])
    return sorted(paths)


def test_the_paths_found_in_the_interface_are_the_ones_expected():
    # A check on the search: it finds the requests this file was written against.
    found = requested_paths()
    for path in ("/history", "/managers/state", "/experiment/layout", "/rack/pause/"):
        assert path in found


def test_every_request_the_interface_makes_has_an_answer(opened):
    page, _ = opened
    unknown = [
        path
        for path in requested_paths()
        if page.page.evaluate("(path) => pyacquisitionDemo.answers(path)", path) is None
    ]
    assert unknown == [], "the stand-in (docs/demo/stand-in.js) has no answer for these"

    feed = (GUI_JS / "feed.js").read_text(encoding="utf-8")
    streams = set(re.findall(r'stream: "(/stream/[a-z]+)"', feed))
    assert streams and streams <= set(demo(page, "streams"))


def test_what_the_interface_builds_from_the_schema_is_answered_too(opened):
    page, _ = opened
    answers = {
        "/lockin/get_x": "measured",
        "/lakeshore/get_temperature": "measured",
        "/lakeshore/set_setpoint": "demo",
        "/lockin/get_sensitivity": "demo",
        "/tasks/ramp_temperature": "demo",
        "/task_manager/call/lakeshore/set_setpoint": "demo",
        "/managers/main/pause": "demo",
    }
    for path, kind in answers.items():
        assert page.page.evaluate("(path) => pyacquisitionDemo.answers(path)", path) == kind


@pytest.mark.still
def test_with_reduced_motion_the_demo_holds_still(opened):
    page, _ = opened
    expect(page.page.locator(".plot-panel")).to_have_count(2)
    before = seq(page)
    page.page.wait_for_timeout(1200)
    assert seq(page) == before
    assert page.errors == []


# ------------------------------------------------------------ the recording
def same_shape(recorded, live, where):
    """The keys of `recorded` and `live` are the same, at every depth. A list is
    compared by its first item, when both have one."""
    if recorded is None or live is None:
        return
    if isinstance(recorded, dict):
        assert isinstance(live, dict), where
        assert set(recorded) == set(live), f"{where}: {sorted(set(recorded) ^ set(live))}"
        for key in recorded:
            same_shape(recorded[key], live[key], f"{where}.{key}")
    elif isinstance(recorded, list):
        assert isinstance(live, list), where
        if recorded and live:
            same_shape(recorded[0], live[0], f"{where}[0]")


@pytest.fixture(scope="module")
def front_page_rig(tmp_path_factory):
    sys.path.insert(0, str(REPO / "examples" / "simulated_rig"))
    from front_page_rig import MyExperiment

    running = Running(MyExperiment, tmp_path_factory.mktemp("front_page_rig"))
    yield running
    running.stop()


def test_the_recording_matches_the_api(front_page_rig):
    again = "The recording is out of date: run scripts/record_demo.py. "
    for path, recorded in SESSION["responses"].items():
        live = requests.get(f"{front_page_rig.address}{path}", timeout=30).json()
        if path == "/openapi.json":
            assert set(recorded["paths"]) == set(live["paths"]), again + path
        else:
            same_shape(recorded, live, again + path)

    managers = front_page_rig.get("/managers/state").json()
    same_shape(SESSION["managers"][0][1], managers["data"], again + "/managers/state")
    entries = front_page_rig.get("/logs/history").json()["data"]["entries"]
    same_shape(SESSION["logs"][0][1], entries[-1], again + "/logs/history")
