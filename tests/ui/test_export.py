"""Exporting a plot as an image, or the data in view as CSV (milestone 16)."""

import base64
import csv
import io
import math

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from test_values import Rig
from ui_helpers import Page, Running


@pytest.fixture
def rig(tmp_path):
    running = Running(Rig, tmp_path, measurement_period=0.05)
    yield running
    running.stop()


def open_page(context, rig, rows=40):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function(
        f"window.pyacquisition?.plot && window.pyacquisition.store.current.rows > {rows}",
        timeout=15000,
    )
    # Units are known before anything is exported.
    page.page.wait_for_function(
        "window.pyacquisition.plot.axes[0].label === 'time (s)'", timeout=15000
    )
    return page


def hold_still(rig, page):
    """Pauses the measurements, and waits for the last row to be drawn."""
    rig.get("/rack/pause/")
    page.page.wait_for_timeout(600)


def export(page, item):
    page.page.get_by_role("button", name="Export").click()
    with page.page.expect_download() as download:
        page.page.get_by_role("menuitem", name=item).click()
    return download.value


def downloaded_bytes(download):
    with open(download.path(), "rb") as file:
        return file.read()


# -------------------------------------------------------------- the image
def test_the_image_is_the_plot_as_drawn_under_a_legend(context, rig):
    page = open_page(context, rig)
    hold_still(rig, page)

    download = export(page, "Image of the plot (PNG)")

    assert download.suggested_filename.endswith(" - wave vs time.png")
    data = base64.b64encode(downloaded_bytes(download)).decode()
    # Decoded in the page, and compared with the plot's own canvas, pixel for pixel.
    result = page.page.evaluate(
        """async (data) => {
            const image = new Image();
            image.src = "data:image/png;base64," + data;
            await image.decode();
            const plot = window.pyacquisition.plot.ctx.canvas;
            const canvas = document.createElement("canvas");
            canvas.width = image.width;
            canvas.height = image.height;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(image, 0, 0);
            const legend = image.height - plot.height;
            const exported = ctx.getImageData(0, legend, plot.width, plot.height).data;
            // The plot's canvas is see-through where nothing is drawn, so it is
            // put on the same background to compare.
            const back = document.createElement("canvas");
            back.width = plot.width;
            back.height = plot.height;
            const b = back.getContext("2d");
            b.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--bg");
            b.fillRect(0, 0, back.width, back.height);
            b.drawImage(plot, 0, 0);
            const live = b.getImageData(0, 0, plot.width, plot.height).data;
            let different = 0;
            for (let i = 0; i < live.length; i += 4) {
                if (Math.abs(live[i] - exported[i]) > 2 || Math.abs(live[i + 1] - exported[i + 1]) > 2
                    || Math.abs(live[i + 2] - exported[i + 2]) > 2) different += 1;
            }
            // The legend has the colour of the plotted quantity in it.
            const colour = getComputedStyle(document.documentElement).getPropertyValue("--series-1").trim();
            const want = [1, 3, 5].map((i) => parseInt(colour.slice(i, i + 2), 16));
            const strip = ctx.getImageData(0, 0, image.width, legend).data;
            let keyed = 0;
            for (let i = 0; i < strip.length; i += 4) {
                if (want.every((v, k) => Math.abs(strip[i + k] - v) < 8)) keyed += 1;
            }
            return {width: image.width, plotWidth: plot.width, legend, different, keyed};
        }""",
        data,
    )
    assert result["width"] == result["plotWidth"]
    assert result["legend"] > 0
    assert result["different"] == 0
    assert result["keyed"] > 10
    assert page.errors == []


# -------------------------------------------------------------- the data
def fix_x(page, low, high):
    page.page.get_by_role("button", name="Axis settings").click()
    menu = page.page.get_by_role("dialog", name="Axis settings")
    row = menu.locator(".axes-row").first
    row.get_by_label("Auto").uncheck()
    menu.get_by_label("X minimum").fill(str(low))
    menu.get_by_label("X maximum").fill(str(high))
    menu.get_by_role("button", name="Apply").click()


def history(rig):
    return rig.get("/history").json()["data"]["segments"]


def test_the_data_in_view_is_every_row_on_the_x_axis(context, rig):
    page = open_page(context, rig, rows=60)
    hold_still(rig, page)
    (segment,) = history(rig)
    times = segment["columns"]["time"]
    low, high = times[10], times[30]
    fix_x(page, low, high)
    page.page.wait_for_function(f"window.pyacquisition.plot.scales.x.min === {low}")

    download = export(page, "Data in view (CSV)")

    assert download.suggested_filename.endswith(" - wave vs time.csv")
    rows = list(csv.reader(io.StringIO(downloaded_bytes(download).decode("utf-8"))))
    assert rows[0] == ["time (s)", "wave"]  # x first, with units
    expected = [
        [repr_number(t), repr_number(w)]
        for t, w in zip(times, segment["columns"]["wave"])
        if low <= t <= high
    ]
    assert rows[1:] == expected
    assert len(expected) == 21


def repr_number(value):
    """A number as JavaScript writes it (String(value)), for the comparison."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = repr(float(value))
    return text[:-2] if text.endswith(".0") else text


def test_hidden_series_are_left_out_and_added_ones_come_in(context, rig):
    page = open_page(context, rig)
    page.page.locator(".series-add").select_option("double")
    expect(page.page.locator(".series-chip")).to_have_count(2)
    page.page.locator(".series-chip").filter(has_text="wave").locator(".series-toggle").click()
    hold_still(rig, page)

    download = export(page, "Data in view (CSV)")

    header = downloaded_bytes(download).decode("utf-8").splitlines()[0]
    assert header == "time (s),double (s)"


def test_with_the_previous_file_shown_its_rows_come_first_and_are_named(context, rig):
    page = open_page(context, rig, rows=20)
    rig.get("/scribe/next_file", title="second")
    page.page.wait_for_function("window.pyacquisition.store.current.rows > 10")
    hold_still(rig, page)

    download = export(page, "Data in view (CSV)")

    rows = list(csv.reader(io.StringIO(downloaded_bytes(download).decode("utf-8"))))
    assert rows[0] == ["file", "time (s)", "wave"]
    files = [row[0] for row in rows[1:]]
    assert files[0] == "00.00 start.data" and files[-1] == "00.01 second.data"
    assert files == sorted(files)  # the previous file's rows, then the current's


def test_a_failed_export_says_so(context, rig):
    page = open_page(context, rig)
    # A canvas that can't be turned into an image (the export draws its own).
    page.page.evaluate("() => { HTMLCanvasElement.prototype.toBlob = (done) => done(null); }")

    page.page.get_by_role("button", name="Export").click()
    page.page.get_by_role("menuitem", name="Image of the plot (PNG)").click()

    expect(page.page.locator(".export-message")).to_contain_text("Couldn't export")
