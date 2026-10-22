"""The front page's live demo (docs/demo/): the interface's own page, fed by a
recording of the front page's experiment. These check that its files agree with
the package they stand in for. The demo running in a browser is checked by
tests/ui/test_demo_page.py."""

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
from test_docs_examples import build, examples, fake_visa  # noqa: F401 (fixtures)

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "docs" / "demo"
GUI = ROOT / "src" / "pyacquisition" / "gui" / "static"
SESSION = json.loads((DEMO / "session.json").read_text(encoding="utf-8"))


class Head(HTMLParser):
    """The stylesheets, scripts, import map and base a page's head loads, in order."""

    def __init__(self, text):
        super().__init__()
        self.loads = []
        self._map = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.loads.append(("stylesheet", attrs["href"]))
        elif tag == "base":
            self.loads.append(("base", attrs["href"]))
        elif tag == "script" and attrs.get("type") == "importmap":
            self._map = ""
        elif tag == "script" and attrs.get("src"):
            self.loads.append((attrs.get("type", "script"), attrs["src"]))

    def handle_data(self, data):
        if self._map is not None:
            self._map += data

    def handle_endtag(self, tag):
        if tag == "script" and self._map is not None:
            self.loads.append(("importmap", json.loads(self._map)))
            self._map = None


def head(path):
    return Head(path.read_text(encoding="utf-8")).loads


# ------------------------------------------------------------ the page
def test_the_demo_page_loads_what_the_interfaces_page_does():
    # Everything but the demo's own: its base, and the stand-in, which runs first.
    demo = head(DEMO / "index.html")
    assert demo[0] == ("base", "app/")
    ours = [("base", "app/"), ("script", "../stand-in.js")]
    assert [load for load in demo if load not in ours] == head(GUI / "index.html")


def test_the_stand_in_runs_before_the_interface():
    demo = head(DEMO / "index.html")
    assert demo.index(("script", "../stand-in.js")) < demo.index(("module", "js/main.js"))
    first_map = next(i for i, load in enumerate(demo) if load[0] == "importmap")
    assert demo.index(("script", "../stand-in.js")) < first_map


# ------------------------------------------------------------ the recording
def test_the_recording_is_of_the_front_pages_experiment(examples, fake_visa):  # noqa: F811
    experiment = build("front_page")

    assert SESSION["columns"] == list(experiment.measurements)
    assert SESSION["responses"]["/experiment/columns"]["data"] == experiment._column_info()
    assert SESSION["responses"]["/experiment/info"]["data"]["name"] == "MyExperiment"
    assert SESSION["responses"]["/rack/list_instruments"]["instruments"] == {
        uid: type(instrument).__name__ for uid, instrument in experiment.instruments.items()
    }
    for uid, instrument in experiment.instruments.items():
        assert names(f"/{uid}/queries/") == sorted(instrument.queries)
        assert names(f"/{uid}/commands/") == sorted(instrument.commands)


def names(path):
    """The names a recorded `queries/` or `commands/` gave: a hardware instrument's
    are a list, and a software instrument's are a list in `data`."""
    answer = SESSION["responses"][path]
    return sorted(answer["data"] if isinstance(answer, dict) else answer)


def test_each_measured_query_feeds_its_column(examples, fake_visa):  # noqa: F811
    experiment = build("front_page")
    expected = {}
    for name, measurement in experiment.measurements.items():
        function = measurement._function
        expected[f"/{function.__self__._uid}/{function.__name__}"] = name
    assert {path: m["column"] for path, m in SESSION["measured"].items()} == expected


def test_the_recordings_rows_go_once_round_and_back_to_the_start():
    rows, columns = SESSION["rows"], SESSION["columns"]
    assert all(len(row) == len(columns) for row in rows)
    kelvin = columns.index("T")
    # It loops, so the end must meet the start.
    assert rows[-1][kelvin] == pytest.approx(rows[0][kelvin], abs=0.1)
    assert min(row[kelvin] for row in rows) < rows[0][kelvin] - 5  # and it went somewhere
    times = [row[columns.index("time")] for row in rows]
    assert times == sorted(times)


def test_the_layout_plots_only_the_recordings_columns():
    for panel in SESSION["layout"]["plots"]["panels"]:
        assert panel["x"] in SESSION["columns"]
        assert {s["name"] for s in panel["series"]} <= set(SESSION["columns"])


def test_the_recording_holds_no_path_on_the_machine_it_was_made_on():
    text = (DEMO / "session.json").read_text(encoding="utf-8")
    for leak in ("Users", "AppData", "/home/", "/tmp/", "Temp\\\\"):
        assert leak not in text


def test_the_recording_is_small_enough_to_load_with_the_front_page():
    assert (DEMO / "session.json").stat().st_size < 1_000_000


# ------------------------------------------------------------ building it
def test_read_the_docs_copies_the_interface_in_before_it_builds():
    text = (ROOT / ".readthedocs.yml").read_text(encoding="utf-8")
    copy = text.index("cp --recursive src/pyacquisition/gui/static docs/demo/app")
    assert text.index("pre_build:") < copy < text.index("zensical build")


def test_the_copy_is_not_committed():
    assert "docs/demo/app/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
