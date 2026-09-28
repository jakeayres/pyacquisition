"""The data store, the feed and the Values tab (milestone 3)."""

import math
import re

import pytest

pytest.importorskip("playwright")

from ui_helpers import Page, Running
from playwright.sync_api import expect

from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock


class Rig(Experiment):
    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)
        self.add_measurement(Measurement("time", clock.time, unit="s"))
        self.add_measurement(Measurement("wave", lambda: math.sin(clock.time())))
        self.add_calculation(
            lambda row: {"double": 2 * row["time"], "label": "ok"},
            units={"double": "s"},
        )


@pytest.fixture
def rig(tmp_path):
    running = Running(Rig, tmp_path, measurement_period=0.05)
    yield running
    running.stop()


def open_page(context, address):
    page = Page(context.new_page())
    page.page.goto(f"{address}/")
    wait_live(page.page)
    return page


def wait_live(page):
    page.wait_for_function(
        "window.pyacquisition?.store?.status === 'live'", timeout=15000
    )


def store(page, expression):
    """Something about the page's store, worked out in the page."""
    return page.evaluate(
        f"(() => {{ const s = window.pyacquisition.store; return {expression}; }})()"
    )


# -------------------------------------------------------------- the Values tab
def test_a_tile_shows_each_column_with_its_unit_and_source(context, rig):
    page = open_page(context, rig.address)

    tiles = page.page.locator(".value-tile")
    expect(tiles).to_have_count(4)
    time_tile = page.page.locator(".value-tile[data-column='time']")
    expect(time_tile.locator(".value-unit")).to_have_text("s")
    expect(time_tile.locator(".value-source")).to_have_text("clock.time")
    expect(
        page.page.locator(".value-tile[data-column='double'] .value-unit")
    ).to_have_text("s")
    expect(
        page.page.locator(".value-tile[data-column='wave'] .value-unit")
    ).to_have_count(0)
    expect(
        page.page.locator(".value-tile[data-column='label'] .value-number")
    ).to_have_text("ok")
    assert page.errors == []


def test_the_values_update_live(context, rig):
    page = open_page(context, rig.address)
    reading = page.page.locator(".value-tile[data-column='time'] .value-number")
    first = reading.inner_text()

    expect(reading).not_to_have_text(first)


def test_each_numeric_tile_has_a_graph_of_the_current_file(context, rig):
    page = open_page(context, rig.address)
    page.page.wait_for_function("window.pyacquisition.store.current.rows > 5")

    path = page.page.locator(".value-tile[data-column='wave'] .spark path")
    expect(path).to_have_attribute(
        "d", re.compile(r"^M[\d.]+ [\d.]+(L[\d.]+ [\d.]+)+$")
    )


# -------------------------------------------------------------- the store
def test_the_store_matches_the_server_row_for_row(context, rig):
    page = open_page(context, rig.address)
    page.page.wait_for_function("window.pyacquisition.store.current.rows > 20")

    server = rig.get("/history").json()["data"]
    page.page.wait_for_function(f"window.pyacquisition.store.seq >= {server['seq']}")
    (segment,) = server["segments"]
    rows = segment["rows"]
    for name, values in segment["columns"].items():
        mine = store(
            page.page, f"Array.from(s.current.column({name!r}).slice(0, {rows}))"
        )
        assert [None if v is None or math.isnan(v) else v for v in mine] == values, name


def test_history_from_before_the_page_opened_is_there_at_once(context, rig):
    page = open_page(context, rig.address)
    page.page.wait_for_function("window.pyacquisition.store.current.rows > 30")

    page.page.reload()
    wait_live(page.page)

    assert store(page.page, "s.current.rows") > 30


def test_a_new_file_moves_the_data_to_the_previous_segment(context, rig):
    page = open_page(context, rig.address)
    page.page.wait_for_function("window.pyacquisition.store.current.rows > 5")

    rig.get("/scribe/next_file", title="sweep")

    page.page.wait_for_function(
        "window.pyacquisition.store.current.file === '00.01 sweep.data'"
    )
    assert store(page.page, "s.previous.file") == "00.00 start.data"
    assert store(page.page, "s.previous.rows") > 5
    server = rig.get("/history/info").json()["data"]["segments"]
    assert [s["file"] for s in server] == ["00.00 start.data", "00.01 sweep.data"]


def test_the_store_keeps_within_the_limit_as_the_server_does(context, tmp_path):
    running = Running(Rig, tmp_path, measurement_period=0.01, history_points=100)
    try:
        page = open_page(context, running.address)
        page.page.wait_for_function("window.pyacquisition.store.seq > 300")

        assert store(page.page, "s.current.rows") <= 100
        server = running.get("/history").json()["data"]
        page.page.wait_for_function(
            f"window.pyacquisition.store.seq >= {server['seq']}"
        )
        # The last row the server has is in the store too, in the same place
        # relative to the end of what the server had then.
        last = server["segments"][-1]["columns"]["time"][-1]
        assert last in store(page.page, "Array.from(s.current.column('time'))")
    finally:
        running.stop()


# -------------------------------------------------------------- reconnecting
def test_it_reconnects_by_itself_when_the_experiment_restarts(context, tmp_path):
    first = Running(Rig, tmp_path, measurement_period=0.05)
    page = open_page(context, first.address)
    assert store(page.page, "s.current.file") == "00.00 start.data"

    first.stop()
    page.page.wait_for_function(
        "window.pyacquisition.store.status === 'reconnecting'", timeout=15000
    )

    second = Running(Rig, tmp_path, port=first.port, measurement_period=0.05)
    try:
        wait_live(page.page)
        # The new run starts a new block, and the store has the new run's data.
        page.page.wait_for_function(
            "window.pyacquisition.store.current.file === '01.00 start.data'"
        )
        expect(page.page.locator(".value-tile")).to_have_count(4)
    finally:
        second.stop()


# -------------------------------------------------------------- formatting
@pytest.mark.parametrize(
    "value, text",
    [
        (20.004532285, "20.0045"),
        (1.290211e-05, "1.2902e-5"),
        (1234567.0, "1.2346e+6"),
        (0, "0.00000"),
        (None, "—"),
        ("overload", "overload"),
        (True, "true"),
    ],
)
def test_values_are_formatted_for_reading(page, value, text):
    import json

    formatted = page.page.evaluate(
        f"import('/ui/js/format.js').then(m => m.formatValue({json.dumps(value)}))"
    )
    assert formatted == text


def test_a_nan_is_formatted_as_a_dash(page):
    assert (
        page.page.evaluate("import('/ui/js/format.js').then(m => m.formatValue(NaN))")
        == "—"
    )


# -------------------------------------------------------------- a sparse column
def values_module(page, expression):
    return page.page.evaluate(f"import('/ui/js/dock/values.js').then((v) => {expression})")


def test_an_age_is_said_in_the_largest_unit_that_fits(page):
    ages = values_module(page, "[5.9, 125, 7200, 3 * 86400 + 1, NaN].map(v.formatAge)")
    assert ages == ["5 s ago", "2 min ago", "2 h ago", "3 d ago", "earlier"]


def test_the_last_value_is_found_in_the_file_before_if_need_be(page):
    found = values_module(
        page,
        """(() => {
            const segment = (columns, dropped = 0) => ({
                dropped, column: (name) => columns[name] ?? null });
            const store = {
                current: segment({ m: new Float64Array([NaN, NaN]), time: new Float64Array([8, 9]) }),
                previous: segment({ m: new Float64Array([1, 2, NaN]), time: new Float64Array([5, 6, 7]) }),
            };
            const first = v.lastValue(store, 'm');
            store.current = segment({ m: new Float64Array([NaN, 4, NaN]), time: new Float64Array([8, 9, 10]) });
            return [first, v.lastValue(store, 'm'), v.lastValue(store, 'nothing')];
        })()""",
    )
    assert found == [{"value": 2, "time": 6}, {"value": 4, "time": 9}, None]
