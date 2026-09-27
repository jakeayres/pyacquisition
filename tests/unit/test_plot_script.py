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
    Scale,
    axis_scale,
    figure_scales,
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


# ------------------------------------------------------------ the APS figure
@pytest.mark.parametrize(
    "largest, unit, scale",
    [
        (1.2e-5, "V", Scale(-6, "µV")),
        (3.4e-8, "A", Scale(-9, "nA")),
        (5e-12, "A", Scale(-12, "pA")),
        (2.5e-3, "K", Scale(-3, "mK")),
        (4.2, "K", Scale(0, "K")),
        (999.9, "V", Scale(0, "V")),
        (1.0, "V", Scale(0, "V")),
        (1000.0, "V", Scale(3, "kV")),
        (7.5e6, "Hz", Scale(6, "MHz")),
        (2e9, "Hz", Scale(9, "GHz")),
        (1e-15, "A", Scale(-12, "pA")),  # no prefix below p
        (0.5, "Ω", Scale(-3, "mΩ")),
        (0.5, "Ohm", Scale(-3, "mOhm")),
        (0.5, "mV", Scale(-3, "10$^{-3}$ mV")),  # already prefixed
        (0.5, "Ω cm", Scale(-3, "10$^{-3}$ Ω cm")),  # compound
        (5e3, None, Scale(3, "10$^{3}$")),
        (5.0, None, Scale(0, None)),
    ],
)
def test_an_axis_is_scaled_by_a_power_of_1000_into_its_unit(largest, unit, scale):
    assert axis_scale(largest, largest, unit) == scale


def test_an_axis_of_zeros_or_offset_values_is_not_scaled():
    assert axis_scale(0.0, 0.0, "V") == Scale(0, "V")
    assert axis_scale(1.79e9, 3600.0, "s") == Scale(0, "s")  # Unix time
    assert axis_scale(float("nan"), 0.0, "V") == Scale(0, "V")
    assert axis_scale(2e-3, 1e-3, "V") == Scale(-3, "mV")


def test_a_dollar_in_a_unit_is_escaped():
    assert axis_scale(5.0, 1.0, "a$b") == Scale(0, "a\\$b")


def test_the_scales_come_from_the_values_or_the_limits():
    req = request(series=[{"name": "x", "colour": BLUE}], style="aps")
    values = {"time": [0.0, 10.0, 20.0], "x": [1e-6, float("nan"), -1.2e-5]}

    assert figure_scales(req, values, {"time": "s", "x": "V"}) == {
        "x": Scale(0, "s"),
        "y": Scale(-6, "µV"),
    }
    held = request(
        series=[{"name": "x", "colour": BLUE}], x_limits=[1000.0, 5000.0], y_limits=[0.0, 0.2]
    )
    assert figure_scales(held, values, {"time": "s", "x": "V"}) == {
        "x": Scale(3, "ks"),
        "y": Scale(-3, "mV"),
    }


def test_the_y_axis_of_series_in_different_units_is_not_scaled():
    values = {"time": [1.0, 2.0], "T": [1e-3, 2e-3], "R": [1e-3, 2e-3]}

    assert "y" not in figure_scales(request(style="aps"), values, UNITS)


APS_UNITS = {"time": "s", "x": "V", "y": "V"}


@pytest.fixture
def lockin(tmp_path):
    folder = tmp_path / "data"
    write_data(
        folder,
        CURRENT,
        {"time": [1.0, 2.0, 3.0], "x": [1e-6, 5e-6, 1.2e-5], "y": [2e-6, 3e-6, 4e-6]},
    )
    write_data(folder, PREVIOUS, {"time": [0.0, 0.5], "x": [7e-6, 8e-6], "y": [1e-6, 1e-6]})
    return folder


def aps(folder, *, series=("x",), units=APS_UNITS, previous_file=PREVIOUS, **settings):
    """An APS figure's script, scaled from the current file's values."""
    colours = [BLUE, ORANGE, GREEN]
    req = request(
        series=[{"name": n, "colour": c} for n, c in zip(series, colours, strict=False)],
        style="aps",
        **settings,
    )
    values = pd.read_csv(folder / CURRENT).to_dict("list")
    return plot_script(
        req,
        folder=str(folder),
        current_file=CURRENT,
        previous_file=previous_file,
        delimiter=",",
        units=units,
        columns={},
        now=NOW,
        scales=figure_scales(req, values, units),
    )


def run_figure(script, where):
    """Runs a figure's script from a file in `where`, with matplotlib's settings
    put back after, and gives its figure, axes, the settings it made, and the
    script's path."""
    where.mkdir(parents=True, exist_ok=True)
    path = where / "figure.py"
    path.write_text(script, encoding="utf-8")
    with matplotlib.rc_context():
        runpy.run_path(str(path), run_name="__main__")
        params = dict(plt.rcParams)
    fig = plt.gcf()
    (ax,) = fig.axes
    return fig, ax, params, path


def test_the_figure_is_one_aps_column_square_in_the_journal_style(lockin, tmp_path):
    fig, ax, params, _ = run_figure(aps(lockin), tmp_path / "scripts")

    assert list(fig.get_size_inches()) == [3.375, 3.375]
    assert params["font.family"] == ["STIXGeneral"] and params["mathtext.fontset"] == "stix"
    assert (params["font.size"], params["xtick.labelsize"], params["legend.fontsize"]) == (9, 8, 8)
    assert (params["xtick.direction"], params["ytick.direction"]) == ("in", "in")
    assert params["xtick.top"] and params["ytick.right"]
    assert params["xtick.minor.visible"] and params["ytick.minor.visible"]
    assert params["axes.formatter.use_mathtext"] and not params["legend.frameon"]
    assert params["pdf.fonttype"] == 42
    tick = ax.xaxis.get_major_ticks()[0]
    assert tick.tick2line.get_visible()  # a tick on the top too


def test_the_figure_is_scaled_for_tidy_numbers(lockin, tmp_path):
    script = aps(lockin)

    assert "Y_SCALE = 1e6  # V to µV" in script
    assert "X_SCALE" not in script  # 1 to 3 s: as it is
    _, ax, _, _ = run_figure(script, tmp_path / "scripts")
    (line,) = ax.get_lines()
    assert list(line.get_xdata()) == [1.0, 2.0, 3.0]
    assert [round(v, 9) for v in line.get_ydata()] == [1.0, 5.0, 12.0]
    assert (ax.get_xlabel(), ax.get_ylabel()) == ("time (s)", "x (µV)")


def test_limits_on_a_scaled_axis_are_written_times_its_scale(lockin, tmp_path):
    script = aps(lockin, x_limits=[1.5, 2.5], y_limits=[2e-6, 1e-5])

    assert "ax.set_ylim(2e-06 * Y_SCALE, 1e-05 * Y_SCALE)" in script
    assert "ax.set_xlim(1.5, 2.5)  # as the plot showed it" in script
    _, ax, _, _ = run_figure(script, tmp_path / "scripts")
    assert ax.get_ylim() == (2e-06 * 1e6, 1e-05 * 1e6)
    assert ax.get_xlim() == (1.5, 2.5)


def test_a_unit_that_cant_take_a_prefix_is_scaled_by_a_power_of_ten(lockin, tmp_path):
    script = aps(lockin, units={"time": "s", "x": "mV"})

    assert "Y_SCALE = 1e6  # in units of 10^-6" in script
    _, ax, _, _ = run_figure(script, tmp_path / "scripts")
    assert ax.get_ylabel() == "x (10$^{-6}$ mV)"


def test_several_series_share_the_label_and_have_a_legend(lockin, tmp_path):
    _, ax, _, _ = run_figure(aps(lockin, series=("x", "y")), tmp_path / "scripts")

    assert ax.get_ylabel() == "x, y (µV)"
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["x", "y"]


def test_one_series_has_no_legend(lockin, tmp_path):
    _, ax, _, _ = run_figure(aps(lockin), tmp_path / "scripts")

    assert ax.get_legend() is None


def test_series_in_different_units_keep_theirs(lockin, tmp_path):
    units = {"time": "s", "x": "V", "y": "K"}

    script = aps(lockin, series=("x", "y"), units=units)

    assert "Y_SCALE" not in script
    _, ax, _, _ = run_figure(script, tmp_path / "scripts")
    assert ax.get_ylabel() == "x (V), y (K)"
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["x (V)", "y (K)"]


def test_the_previous_file_is_offered_but_not_drawn(lockin, tmp_path):
    script = aps(lockin, previous=True)

    assert 'PREVIOUS_FILE = None  # "00.00 start.data" to draw it too, fainter' in script
    _, ax, _, _ = run_figure(script, tmp_path / "scripts")
    assert len(ax.get_lines()) == 1
    plt.close("all")

    drawn_too = script.replace(
        'PREVIOUS_FILE = None  # "00.00 start.data"', 'PREVIOUS_FILE = "00.00 start.data"  #'
    )
    _, ax, _, _ = run_figure(drawn_too, tmp_path / "again")
    old, _ = ax.get_lines()
    assert old.get_alpha() == 0.35 and [round(v, 9) for v in old.get_ydata()] == [7.0, 8.0]


def test_the_previous_file_isnt_mentioned_unless_it_was_shown(lockin):
    assert "PREVIOUS_FILE" not in aps(lockin)


def test_marks_take_their_sizes_from_the_style(lockin, tmp_path):
    script = aps(lockin, marks="both")

    plots = [line for line in script.splitlines() if line.startswith("ax.plot(")]
    assert plots and not any("markersize" in p or "linewidth" in p for p in plots)
    _, ax, _, _ = run_figure(script, tmp_path / "scripts")
    (line,) = ax.get_lines()
    assert (line.get_linestyle(), line.get_marker()) == ("-", "o")
    assert line.get_markersize() == 3 and line.get_linewidth() == 1.0


def test_a_dollar_in_a_name_is_shown_as_it_is(tmp_path):
    folder = tmp_path / "data"
    write_data(folder, CURRENT, {"time": [1.0, 2.0], "cost $": [1.0, 2.0], "gain $x$": [3.0, 4.0]})

    script = aps(folder, series=("cost $", "gain $x$"), units={}, previous_file=None)
    fig, ax, _, _ = run_figure(script, tmp_path / "scripts")
    fig.canvas.draw()  # would fail on bad maths

    assert ax.get_ylabel() == r"cost \$, gain \$x\$"


def test_a_linear_axis_has_about_five_numbered_ticks(lockin, tmp_path):
    assert "ax.locator_params(nbins=5)" in aps(lockin)
    assert 'ax.locator_params(axis="x", nbins=5)' in aps(lockin, log_y=True)
    assert "locator_params" not in aps(lockin, log_x=True, log_y=True)

    _, ax, _, _ = run_figure(aps(lockin, log_y=True), tmp_path / "scripts")
    assert len(ax.get_xticks()) <= 7
    assert ax.get_yscale() == "log"


def test_the_figure_is_saved_as_a_pdf_beside_the_script(lockin, tmp_path):
    _, _, _, path = run_figure(aps(lockin, log_y=True), tmp_path / "scripts")

    assert path.with_suffix(".pdf").read_bytes().startswith(b"%PDF")


def test_the_figure_says_what_it_is(lockin):
    script = aps(lockin)

    module = ast.parse(script)
    assert ast.get_docstring(module).startswith(
        "A figure exported from pyacquisition on 2026-09-27 at 14:03: x against time."
    )
    assert "APS journal" in ast.get_docstring(module)
    assert [n.name for n in module.body if isinstance(n, ast.FunctionDef)] == ["read"]


# ------------------------------------------------------------ the figure's endpoint
def test_a_request_without_a_style_gets_the_screen_script(experiment):
    start_file(experiment, ROWS)

    plain = post(experiment).json()["data"]
    screen = post(experiment, style="screen").json()["data"]

    assert plain.split("\n", 1)[1] == screen.split("\n", 1)[1]  # past the time in the docstring
    assert "rcParams" not in plain


def test_the_endpoint_scales_a_figure_from_the_historys_values(experiment, tmp_path):
    start_file(
        experiment, [{"time": 1.0, "T": 4.0, "R": 7e-6}, {"time": 2.0, "T": 5.0, "R": 9e-6}]
    )

    script = post(experiment, series=[{"name": "R", "colour": BLUE}], style="aps").json()["data"]

    assert "Y_SCALE = 1e6  # in units of 10^-6" in script  # R has no unit
    _, ax, _, _ = run_figure(script, tmp_path / "scripts")
    assert ax.get_ylabel() == "R (10$^{-6}$)" and ax.get_xlabel() == "time (s)"


def test_the_endpoint_scales_a_held_axis_from_its_limits(experiment):
    start_file(experiment, ROWS)

    script = post(
        experiment, series=[{"name": "T", "colour": BLUE}], x_limits=[1000.0, 4000.0], style="aps"
    ).json()["data"]

    assert "X_SCALE = 1e-3  # s to ks" in script
    assert "ax.set_xlim(1000.0 * X_SCALE, 4000.0 * X_SCALE)" in script


def test_the_endpoint_refuses_an_unknown_style(experiment):
    start_file(experiment, ROWS)

    assert post(experiment, style="nature").status_code == 422
