"""A plot as a matplotlib script (core/plot_script.py, and the experiment's
/experiment/plot_script): the scripts are written beside small data files, run
headless, and the figure they draw is looked at."""

import ast
import runpy
from datetime import datetime

import pandas as pd
import pytest
from fastapi.testclient import TestClient

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from pyacquisition import Experiment, Measurement  # noqa: E402
from pyacquisition.core.plot_script import (  # noqa: E402
    PlotRequest,
    PlotScriptError,
    plot_script,
)

NOW = datetime(2026, 9, 27, 14, 3)
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1f9e5a"

CURRENT = "00.01 sweep.data"
PREVIOUS = "00.00 start.data"
UNITS = {"time": "s", "T": "K", "R": "V"}


@pytest.fixture(autouse=True)
def no_windows(monkeypatch):
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)
    yield
    plt.close("all")


def write_data(folder, name, columns, delimiter=","):
    """A data file as the scribe writes it (with pandas): an empty cell for a
    missing value."""
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns).to_csv(folder / name, index=False, sep=delimiter)


def request(**settings):
    body = {"x": "time", "series": [{"name": "T", "colour": BLUE}, {"name": "R", "colour": ORANGE}]}
    body.update(settings)
    return PlotRequest(**body)


def script_for(req, folder, *, previous_file=PREVIOUS, delimiter=",", units=UNITS, columns=None):
    return plot_script(
        req,
        folder=str(folder),
        current_file=CURRENT,
        previous_file=previous_file,
        delimiter=delimiter,
        units=units,
        columns=columns if columns is not None else {},
        now=NOW,
    )


def run(script, where):
    """Runs the script from a file in `where`, and gives the axes it drew."""
    where.mkdir(parents=True, exist_ok=True)
    path = where / "plot.py"
    path.write_text(script, encoding="utf-8")
    runpy.run_path(str(path), run_name="__main__")
    (ax,) = plt.gcf().axes
    return ax


@pytest.fixture
def data(tmp_path):
    folder = tmp_path / "data"
    write_data(folder, CURRENT, {"time": [10.0, 11.0, 12.0], "T": [4.0, 5.0, 6.0], "R": [1.0, 2.0, None]})
    write_data(folder, PREVIOUS, {"time": [1.0, 2.0], "T": [300.0, 290.0], "R": [7.0, 8.0]})
    return folder


def drawn(line):
    return list(line.get_xdata()), [float(v) for v in line.get_ydata()]


# ------------------------------------------------------------ the series
def test_a_line_for_each_series_with_its_colour_label_and_data(data, tmp_path):
    ax = run(script_for(request(), data), tmp_path / "scripts")

    t, r = ax.get_lines()
    assert (t.get_color(), t.get_label()) == (BLUE, "T (K)")
    assert (r.get_color(), r.get_label()) == (ORANGE, "R (V)")
    assert drawn(t) == ([10.0, 11.0, 12.0], [4.0, 5.0, 6.0])
    x, y = drawn(r)
    assert x == [10.0, 11.0, 12.0] and y[:2] == [1.0, 2.0] and y[2] != y[2]  # NaN: a gap
    assert [text.get_text() for text in ax.get_legend().get_texts()] == ["T (K)", "R (V)"]


def test_the_script_is_plain_and_says_what_it_draws(data):
    script = script_for(request(previous=True), data)

    module = ast.parse(script)
    assert ast.get_docstring(module).startswith(
        "A plot exported from pyacquisition on 2026-09-27 at 14:03: T, R against time."
    )
    assert "pip install pandas matplotlib" in script
    assert [n.name for n in module.body if isinstance(n, ast.FunctionDef)] == ["read"]
    assert not any(isinstance(n, (ast.For, ast.While)) for n in module.body)
    assert f"FOLDER = Path(r\"{data}\")" in script
    assert 'FILE = "00.01 sweep.data"' in script
    assert 'PREVIOUS_FILE = "00.00 start.data"  # None to leave it out' in script
    assert (
        'ax.plot(data["time"], data["T"], "-", color="#2a78d6", linewidth=1.5, label="T (K)")'
        in script
    )


# ------------------------------------------------------------ the previous file
def test_the_previous_file_is_drawn_fainter_thinner_and_behind(data, tmp_path):
    ax = run(script_for(request(previous=True), data), tmp_path / "scripts")

    lines = ax.get_lines()
    assert len(lines) == 4
    old_t, old_r, t, r = lines  # drawn first, so behind
    assert drawn(old_t) == ([1.0, 2.0], [300.0, 290.0])
    assert (old_t.get_color(), old_r.get_color()) == (BLUE, ORANGE)
    assert old_t.get_alpha() == 0.35 and t.get_alpha() is None
    assert old_t.get_linewidth() < t.get_linewidth()
    assert old_t.get_label().startswith("_")  # not in the legend
    assert len(ax.get_legend().get_texts()) == 2


def test_the_previous_file_is_left_out_unless_asked_for(data, tmp_path):
    script = script_for(request(), data)

    assert "PREVIOUS_FILE" not in script and "previous[" not in script
    assert len(run(script, tmp_path / "scripts").get_lines()) == 2


def test_the_previous_file_is_left_out_when_there_is_none(data, tmp_path):
    script = script_for(request(previous=True), data, previous_file=None)

    assert "PREVIOUS_FILE" not in script
    assert len(run(script, tmp_path / "scripts").get_lines()) == 2


def test_setting_previous_file_to_none_leaves_it_out(data, tmp_path):
    script = script_for(request(previous=True), data).replace(
        'PREVIOUS_FILE = "00.00 start.data"', "PREVIOUS_FILE = None"
    )

    assert len(run(script, tmp_path / "scripts").get_lines()) == 2


def test_a_series_the_previous_file_lacks_is_drawn_from_the_current_one_only(data, tmp_path):
    write_data(data, PREVIOUS, {"time": [1.0, 2.0], "T": [300.0, 290.0]})
    columns = {CURRENT: {"time", "T", "R"}, PREVIOUS: {"time", "T"}}

    ax = run(script_for(request(previous=True), data, columns=columns), tmp_path / "scripts")

    old_t, t, r = ax.get_lines()
    assert old_t.get_alpha() == 0.35 and drawn(old_t)[1] == [300.0, 290.0]
    assert (t.get_label(), r.get_label()) == ("T (K)", "R (V)")


def test_a_previous_file_without_x_draws_nothing(data, tmp_path):
    write_data(data, PREVIOUS, {"T": [300.0, 290.0]})
    columns = {CURRENT: {"time", "T", "R"}, PREVIOUS: {"T"}}

    script = script_for(request(previous=True), data, columns=columns)

    assert "PREVIOUS_FILE" not in script
    assert len(run(script, tmp_path / "scripts").get_lines()) == 2


# ------------------------------------------------------------ the axes
def test_the_axis_labels_have_units_where_there_are_some(data, tmp_path):
    ax = run(script_for(request(), data, units={"T": "K"}), tmp_path / "scripts")

    assert ax.get_xlabel() == "time"
    assert ax.get_ylabel() == "T (K), R"
    assert [line.get_label() for line in ax.get_lines()] == ["T (K)", "R"]


def test_log_axes(data, tmp_path):
    ax = run(script_for(request(log_x=True, log_y=True), data), tmp_path / "scripts")

    assert (ax.get_xscale(), ax.get_yscale()) == ("log", "log")


def test_linear_axes_by_default(data, tmp_path):
    script = script_for(request(), data)

    assert "set_xscale" not in script and "set_yscale" not in script
    ax = run(script, tmp_path / "scripts")
    assert (ax.get_xscale(), ax.get_yscale()) == ("linear", "linear")


def test_limits_are_set_exactly_when_given(data, tmp_path):
    x_limits, y_limits = [10.1, 11.9], [0.1 + 0.2, 5.5]

    script = script_for(request(x_limits=x_limits, y_limits=y_limits), data)
    ax = run(script, tmp_path / "scripts")

    assert list(ax.get_xlim()) == x_limits
    assert list(ax.get_ylim()) == y_limits
    assert "# as the plot showed it; delete for all the data" in script


def test_limits_are_left_to_matplotlib_when_not_given(data, tmp_path):
    script = script_for(request(), data)

    assert "set_xlim" not in script and "set_ylim" not in script
    low, high = run(script, tmp_path / "scripts").get_xlim()
    assert low <= 10.0 and high >= 12.0


def test_log_scales_are_set_before_the_limits(data):
    script = script_for(request(log_y=True, y_limits=[1.0, 10.0]), data)

    assert script.index('ax.set_yscale("log")') < script.index("ax.set_ylim(1.0, 10.0)")


# ------------------------------------------------------------ marks
@pytest.mark.parametrize(
    "marks, linestyle, marker, markersize",
    [("lines", "-", "None", None), ("points", "None", "o", 3), ("both", "-", "o", 3)],
)
def test_lines_points_and_both(data, tmp_path, marks, linestyle, marker, markersize):
    ax = run(script_for(request(marks=marks, previous=True), data), tmp_path / "scripts")

    old, _, current, _ = ax.get_lines()
    assert (current.get_linestyle(), current.get_marker()) == (linestyle, marker)
    if markersize:
        assert current.get_markersize() == markersize
        assert old.get_markersize() == 2.5


# ------------------------------------------------------------ files
@pytest.mark.parametrize("delimiter", [";", "\t"])
def test_another_delimiter(tmp_path, delimiter):
    folder = tmp_path / "data"
    write_data(folder, CURRENT, {"time": [1.0, 2.0], "T": [3.0, 4.0], "R": [5.0, 6.0]}, delimiter)

    ax = run(script_for(request(), folder, delimiter=delimiter), tmp_path / "scripts")

    assert drawn(ax.get_lines()[0]) == ([1.0, 2.0], [3.0, 4.0])


def test_the_files_are_looked_for_beside_the_script_when_not_in_the_folder(data, tmp_path):
    script = script_for(request(previous=True), tmp_path / "moved away")

    ax = run(script, data)  # the script saved in the data folder

    assert len(ax.get_lines()) == 4


def test_a_file_in_neither_place_is_an_error_naming_both(tmp_path):
    folder = tmp_path / "nowhere"
    script = script_for(request(), folder)

    with pytest.raises(FileNotFoundError) as error:
        run(script, tmp_path / "scripts")

    assert CURRENT in str(error.value) and str(folder) in str(error.value)
    assert "this script's folder" in str(error.value)


# ------------------------------------------------------------ names
AWKWARD = ['it\'s "quoted"', "back\\slash", "with space", '"); import os; ("', "\\"]


def test_awkward_names_are_drawn_as_they_are(tmp_path):
    folder = tmp_path / "the lab's data"  # Windows allows no " or \ in a name
    current = "o'clock run, 1.data"
    columns = {"x axis": [1.0, 2.0]} | {name: [float(i), float(i + 1)] for i, name in enumerate(AWKWARD)}
    write_data(folder, current, columns)
    series = [{"name": name, "colour": BLUE} for name in AWKWARD]
    units = {AWKWARD[0]: 'µ"V\\'}

    script = plot_script(
        PlotRequest(x="x axis", series=series),
        folder=str(folder),
        current_file=current,
        previous_file=None,
        delimiter=",",
        units=units,
        columns={current: set(columns)},
        now=NOW,
    )
    ax = run(script, tmp_path / "scripts")

    imported = [
        a.name for n in ast.walk(ast.parse(script)) if isinstance(n, ast.Import) for a in n.names
    ]
    assert "os" not in imported
    lines = ax.get_lines()
    assert [line.get_label() for line in lines] == [f'{AWKWARD[0]} (µ"V\\)'] + AWKWARD[1:]
    assert [drawn(line)[1] for line in lines] == [[float(i), float(i + 1)] for i in range(len(AWKWARD))]
    assert ax.get_xlabel() == "x axis"
    assert ", ".join(AWKWARD[1:]) in ax.get_ylabel()
    docstring = ast.get_docstring(ast.parse(script))
    assert docstring.startswith(f"A plot exported from pyacquisition on 2026-09-27 at 14:03: {AWKWARD[0]}")


@pytest.mark.parametrize(
    "folder, raw",
    [
        (r"D:\lab\my data", True),
        (r"D:\lab's data", True),
        ('/home/lab/the "good" data', False),
        ("D:\\lab\\", False),
        ("D:\\lab\\\ttab", False),
    ],
)
def test_a_folder_is_written_so_it_reads_back(folder, raw):
    script = script_for(request(), folder)

    literal = script.split("FOLDER = Path(", 1)[1].split(")\n", 1)[0]
    assert ast.literal_eval(literal) == folder
    assert literal.startswith('r"') == raw


# ------------------------------------------------------------ refusing
@pytest.mark.parametrize(
    "settings, message",
    [
        ({"series": []}, "no series"),
        ({"series": [{"name": "T", "colour": BLUE}] * 9}, "at most 8"),
        ({"series": [{"name": "T", "colour": "blue"}]}, "not #rrggbb"),
        ({"series": [{"name": "T", "colour": "#12345"}]}, "not #rrggbb"),
        ({"x_limits": [2.0, 1.0]}, "smaller first"),
        ({"y_limits": [1.0, 1.0]}, "smaller first"),
        ({"x_limits": [1.0, float("inf")]}, "two finite numbers"),
        ({"y_limits": [float("nan"), 1.0]}, "two finite numbers"),
        ({"x_limits": [1.0, 2.0, 3.0]}, "two finite numbers"),
        ({"log_x": True, "x_limits": [0.0, 1.0]}, "above 0"),
        ({"log_y": True, "y_limits": [-1.0, 1.0]}, "above 0"),
        ({"x": "B"}, "'B' isn't a column"),
        ({"series": [{"name": "B", "colour": BLUE}]}, "'B' isn't a column"),
    ],
)
def test_a_request_that_cant_be_drawn_is_refused(data, settings, message):
    columns = {CURRENT: {"time", "T", "R"}}

    with pytest.raises(PlotScriptError, match=message):
        script_for(request(**settings), data, columns=columns)


def test_a_column_in_the_previous_file_only_is_one_when_it_is_drawn(data):
    columns = {CURRENT: {"time", "T"}, PREVIOUS: {"time", "T", "R"}}

    script_for(request(previous=True), data, columns=columns)
    with pytest.raises(PlotScriptError, match="'R' isn't a column"):
        script_for(request(), data, columns=columns)


def test_a_plot_with_nothing_to_draw_from_any_file_is_refused(data):
    columns = {CURRENT: {"T"}, PREVIOUS: {"time"}}

    with pytest.raises(PlotScriptError, match="No data file has both 'time' and"):
        script_for(request(previous=True, series=[{"name": "T", "colour": BLUE}]), data, columns=columns)


# ------------------------------------------------------------ the endpoint
@pytest.fixture
def experiment(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    experiment.add_measurement(Measurement("time", lambda: 0.0, unit="s"))
    experiment.add_measurement(Measurement("T", lambda: 0.0, unit="K"))
    experiment.add_measurement(Measurement("R", lambda: 0.0))
    experiment._register_endpoints(experiment._api_server)
    return experiment


def start_file(experiment, rows):
    """A data file, as the scribe starts and writes it, and the history keeps
    it."""
    scribe, history = experiment._scribe, experiment._history
    history.new_file(scribe.current_file())
    folder = scribe.root_path
    if rows:
        write_data(folder, scribe.current_file(), {k: [r[k] for r in rows] for k in rows[0]})
    for row in rows:
        history.add_row(row)


def post(experiment, **settings):
    body = {"x": "time", "series": [{"name": "T", "colour": BLUE}, {"name": "R", "colour": ORANGE}]}
    body.update(settings)
    return TestClient(experiment._api_server.app).post("/experiment/plot_script", json=body)


ROWS = [{"time": 1.0, "T": 4.0, "R": 7.0}, {"time": 2.0, "T": 5.0, "R": 8.0}]


def test_the_endpoint_gives_a_script_that_draws_the_plot(experiment, tmp_path):
    start_file(experiment, ROWS)

    response = post(experiment)

    assert response.status_code == 200
    script = response.json()["data"]
    assert f"FILE = {experiment._scribe.current_file()!r}".replace("'", '"') in script
    ax = run(script, tmp_path / "scripts")
    t, r = ax.get_lines()
    assert (t.get_label(), r.get_label()) == ("T (K)", "R")
    assert drawn(t) == ([1.0, 2.0], [4.0, 5.0])
    assert ax.get_xlabel() == "time (s)"


def test_the_endpoint_draws_the_previous_file_when_asked(experiment, tmp_path):
    start_file(experiment, ROWS)
    first = experiment._scribe.current_file()
    experiment._scribe.next_file("sweep")
    start_file(experiment, [{"time": 3.0, "T": 6.0, "R": 9.0}])

    script = post(experiment, previous=True).json()["data"]

    assert f'PREVIOUS_FILE = "{first}"' in script
    ax = run(script, tmp_path / "scripts")
    assert [line.get_alpha() for line in ax.get_lines()] == [0.35, 0.35, None, None]


def test_the_endpoint_leaves_out_a_previous_file_it_no_longer_holds(experiment):
    start_file(experiment, ROWS)

    script = post(experiment, previous=True).json()["data"]

    assert "PREVIOUS_FILE" not in script


def test_the_endpoint_writes_the_folder_and_delimiter(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False, data_delimiter=";")
    experiment.add_measurement(Measurement("time", lambda: 0.0))
    experiment.add_measurement(Measurement("T", lambda: 0.0))
    experiment.add_measurement(Measurement("R", lambda: 0.0))
    experiment._register_endpoints(experiment._api_server)
    experiment._history.new_file(experiment._scribe.current_file())
    experiment._history.add_row(ROWS[0])

    script = post(experiment).json()["data"]

    assert 'DELIMITER = ";"' in script
    assert f'FOLDER = Path(r"{experiment._scribe.current_directory()}")' in script


@pytest.mark.parametrize(
    "settings, message",
    [
        ({"x": "B"}, "'B' isn't a column"),
        ({"series": [{"name": "T", "colour": "red"}]}, "not #rrggbb"),
        ({"series": []}, "no series"),
        ({"series": [{"name": "T", "colour": BLUE}] * 9}, "at most 8"),
        ({"x_limits": [2.0, 1.0]}, "smaller first"),
        ({"log_y": True, "y_limits": [0.0, 1.0]}, "above 0"),
    ],
)
def test_the_endpoint_refuses_a_plot_it_cant_draw(experiment, settings, message):
    start_file(experiment, ROWS)

    response = post(experiment, **settings)

    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_the_endpoint_refuses_a_body_of_the_wrong_shape(experiment):
    start_file(experiment, ROWS)

    assert post(experiment, marks="dashes").status_code == 422
    assert post(experiment, x_limits="all").status_code == 422


def test_the_endpoint_refuses_while_nothing_is_written(experiment):
    experiment._history.new_file(experiment._scribe.current_file())

    response = post(experiment)

    assert response.status_code == 409
    assert "nothing to plot" in response.json()["detail"]
