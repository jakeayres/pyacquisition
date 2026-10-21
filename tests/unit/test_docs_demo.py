"""The docs' live demo (docs/demo/): the interface's own page, fed by recordings,
of the front page's experiment and of Getting Started's steps. These check that its
files agree with the package and the pages they stand in for. The demo running in
a browser is checked by tests/ui/test_demo_page.py."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from test_docs_examples import build, examples, fake_visa  # noqa: F401 (fixtures)
from test_docs_walkthroughs import content, merged, walkthrough

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


# ------------------------------------------------------------ Getting Started's
# The walkthroughs of "1. The Config File" and "2. The Python API" show the interface
# at each step, from recordings in docs/demo/sessions/ (scripts/record_getting_started.py).
GETTING_STARTED = ROOT / "docs" / "getting_started"
SESSIONS = DEMO / "sessions"


def named(page):
    """Each recording a page names, with the step that first names it."""
    found = {}
    text = page.read_text(encoding="utf-8")
    for i, attrs in enumerate(re.findall(r'<section class="gs-step"([^>]*)>', text)):
        name = re.search(r'data-demo="([^"]+)"', attrs)
        if name and name[1] not in found:
            found[name[1]] = i
    for name in re.findall(r'<div class="pa-built" data-demo="([^"]+)"', text):
        found.setdefault(name, None)
    return found


def session(name):
    return json.loads((SESSIONS / f"{name}.json").read_text(encoding="utf-8"))


ALL = {name for page in GETTING_STARTED.glob("*.md") for name in named(page)}


def test_every_recording_a_page_names_is_there():
    assert ALL, "the pages name no recordings"
    assert ALL <= {p.stem for p in SESSIONS.glob("*.json")}


@pytest.mark.parametrize("name, step", list(named(GETTING_STARTED / "config_file.md").items()))
def test_each_config_recording_ran_the_pages_file_at_its_step(name, step):
    w = walkthrough(GETTING_STARTED / "config_file.md")
    snippets = [content(block) for i, block in w.blocks_of("rig.toml") if i <= step]
    assert session(name)["config"] == (merged(snippets) if snippets else "")
    assert session(name)["responses"]["/experiment/info"]["data"]["name"] == "rig"


@pytest.mark.parametrize("name, step", list(named(GETTING_STARTED / "python_api.md").items()))
def test_each_python_recording_ran_the_steps_lab(name, step):
    w = walkthrough(GETTING_STARTED / "python_api.md")
    labs = [block.body for i, block in w.blocks_of("lab.py") if i <= step]
    recorded = session(name)
    assert f"examples/getting_started/{recorded['source']}" == labs[-1]
    assert recorded["responses"]["/experiment/info"]["data"]["name"] == "Lab"


def test_the_python_recordings_show_what_their_steps_add():
    assert session("python-2")["answers"] == {"/lockin/get_frequency": 137.0}
    assert "power" not in session("python-2")["columns"]
    assert "power" in session("python-4")["columns"]
    paths = session("python-6")["responses"]["/openapi.json"]["paths"]
    assert "/tasks/record" in paths
    files = [file for _, file in session("python-7")["files"]]
    assert files == ["03.01 run 1.data", "03.02 run 2.data", "03.03 run 3.data"]


def test_the_data_files_are_named_as_the_pages_say():
    # "after the empty file's 00.00 start.data, this one is 01.00 start.data", and
    # part 2's runs are 02, then 03 for Record's files.
    file = lambda name: session(name)["responses"]["/scribe/state"]["data"]["file"]  # noqa: E731
    assert file("config-1") == "00.00 start.data"
    assert file("config-6") == "01.00 start.data"
    assert file("python-1") == "02.00 start.data"


def test_the_recordings_hold_no_path_and_are_small():
    for path in SESSIONS.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        for leak in ("Users", "AppData", "/home/", "/tmp/", "Temp\\\\"):
            assert leak not in text, path.name
        assert path.stat().st_size < 250_000, path.name
