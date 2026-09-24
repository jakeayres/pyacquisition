"""The plot on the right seven twelfths of the window, in the default look of dearpygui."""

import math

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui.components import plot_panel as module
from pyacquisition.gui.components.plot_panel import AUTOFIT_MARGIN, PlotPanel
from pyacquisition.gui.constants import STATE_STYLES, VALUE_COLORS, plot_x


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


@pytest.fixture
def context(monkeypatch):
    dpg.create_context()
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1920)
    monkeypatch.setattr(dpg, "get_viewport_client_height", lambda: 900)
    yield
    dpg.destroy_context()


def make(**options):
    clock = Clock()
    return PlotPanel(clock=clock, **options), clock


def points(panel, key):
    xs, ys = dpg.get_value(panel.series[key])[:2]
    return list(xs), list(ys)


def feed(panel, rows):
    for row in rows:
        panel.update(row)
    panel.tick()


def limits_set(monkeypatch):
    """Record the limits that are set on the axes, by axis."""
    found = {}
    monkeypatch.setattr(dpg, "set_axis_limits", lambda axis, low, high: found.__setitem__(axis, (low, high)))
    return found


# --- the panel ---


def test_it_is_the_whole_right_seven_twelfths_of_the_window_top_to_bottom(context):
    panel, _ = make()

    assert dpg.get_item_pos(panel.window_tag) == [1920 * 5 // 12, 0]
    config = dpg.get_item_configuration(panel.window_tag)
    assert config["width"] == 1920 - 1920 * 5 // 12 and config["height"] == 900
    assert 0.55 < config["width"] / 1920 < 0.62, "Between a half and two thirds of the window."
    assert plot_x(1920) == 800


def test_it_follows_the_size_of_the_window(context, monkeypatch):
    panel, _ = make()
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1000)
    monkeypatch.setattr(dpg, "get_viewport_client_height", lambda: 700)

    panel.update_layout()

    assert dpg.get_item_pos(panel.window_tag) == [1000 * 5 // 12, 0]
    assert dpg.get_item_configuration(panel.window_tag)["width"] == 1000 - 1000 * 5 // 12
    assert dpg.get_item_configuration(panel.window_tag)["height"] == 700


def test_it_has_no_title_bar_and_cannot_be_moved(context):
    panel, _ = make()

    config = dpg.get_item_configuration(panel.window_tag)
    assert config["no_title_bar"] and config["no_move"] and config["no_resize"]


def theme_values(theme, kind):
    found = {}
    for component in dpg.get_item_children(theme, 1):
        for item in dpg.get_item_children(component, 1):
            if dpg.get_item_type(item).endswith(kind):
                found[dpg.get_item_configuration(item)["target"]] = dpg.get_value(item)
    return found


def scaled(colour):
    scale = 255 if max(colour) <= 1 else 1
    return tuple(round(c * scale) for c in colour)


def test_the_window_is_the_black_of_the_pages_and_has_a_margin(context):
    panel, _ = make()

    assert dpg.get_item_theme(panel.window_tag) == panel._theme
    colours = theme_values(panel._theme, "mvThemeColor")
    styles = theme_values(panel._theme, "mvThemeStyle")
    assert scaled(colours[dpg.mvThemeCol_WindowBg])[:3] == (0, 0, 0)
    assert scaled(colours[dpg.mvThemeCol_Border])[3] == 0, "No border."
    assert list(styles[dpg.mvStyleVar_WindowPadding])[:2] == [module.MARGIN, module.MARGIN]
    assert 16 <= module.MARGIN <= 40, "A moderate margin."
    assert styles[dpg.mvStyleVar_WindowBorderSize][0] == 0


def test_the_plot_has_no_border_and_the_area_inside_its_axes_is_the_colour_of_the_cards(context):
    panel, _ = make()
    plot_colours = {}
    for component in dpg.get_item_children(panel._theme, 1):
        for item in dpg.get_item_children(component, 1):
            plot_colours[dpg.get_item_configuration(item)["target"]] = scaled(dpg.get_value(item))

    assert plot_colours[dpg.mvPlotCol_FrameBg][3] == 0
    assert plot_colours[dpg.mvPlotCol_PlotBorder][3] == 0
    assert plot_colours[dpg.mvPlotCol_PlotBg][:3] == STATE_STYLES["neutral"]["background"]
    assert plot_colours[dpg.mvPlotCol_PlotBg][:3] == module.PLOT_BACKGROUND
    grid = plot_colours[dpg.mvPlotCol_AxisGrid][:3]
    assert max(grid) < 90, "A quiet grid."
    assert sum(grid) > sum(module.PLOT_BACKGROUND), "But one that shows against the cards' colour."


def test_the_plot_itself_is_not_themed_apart_from_the_panel(context):
    """Everything the plot offers on a right click is left alone."""
    panel, _ = make()
    panel.update({"x": 1.0})

    for item in (panel.plot, panel.x_axis, panel.y_axis):
        assert dpg.get_item_theme(item) in (None, 0), item


def test_the_plot_keeps_the_options_of_a_right_click(context):
    """The plot is made as the floating plot window made it, with none turned off."""
    panel, _ = make()

    config = dpg.get_item_configuration(panel.plot)
    assert not config["no_menus"], "The menu of a right click is there."
    assert not config["no_box_select"] and not config["no_mouse_pos"]
    assert dpg.get_item_label(panel.plot) == "Live Data Plot"


# --- the measurements ---


def test_every_numeric_measurement_gets_points_named_for_it(context):
    panel, _ = make()

    feed(panel, [{"T": 4.2, "V": 0.001, "count": 3}])

    assert list(panel.series) == ["T", "V", "count"]
    assert [dpg.get_item_label(s) for s in panel.series.values()] == ["T", "V", "count"]
    assert all(dpg.get_item_parent(s) == panel.y_axis for s in panel.series.values())


def test_the_measurements_are_points_and_not_lines(context):
    panel, _ = make()

    feed(panel, [{"T": 4.2, "V": 0.001}])

    for series in panel.series.values():
        assert dpg.get_item_type(series).endswith("mvScatterSeries")
    assert not any(dpg.get_item_type(i).endswith("mvLineSeries") for i in dpg.get_all_items())


def marker_colour(panel, key):
    theme = dpg.get_item_theme(panel.series[key])
    component = dpg.get_item_children(theme, 1)[0]
    colours = {
        dpg.get_item_configuration(i)["target"]: dpg.get_value(i)
        for i in dpg.get_item_children(component, 1)
        if dpg.get_item_type(i).endswith("mvThemeColor")
    }
    return [scaled(colours[c])[:3] for c in (dpg.mvPlotCol_MarkerFill, dpg.mvPlotCol_MarkerOutline)]


def test_the_points_are_in_the_colour_of_their_card_in_the_live_data_window(context):
    panel, _ = make(colors=lambda key: {"a": (10, 20, 30), "b": (200, 100, 50)}.get(key))

    feed(panel, [{"a": 1.0, "b": 2.0}])

    assert marker_colour(panel, "a") == [(10, 20, 30), (10, 20, 30)], "Fill and outline."
    assert marker_colour(panel, "b") == [(200, 100, 50)] * 2


def test_a_measurement_with_no_card_colour_takes_the_next_of_the_palette(context):
    panel, _ = make(colors=lambda key: None)

    feed(panel, [{"a": 1.0, "b": 2.0}])

    assert marker_colour(panel, "a") == [tuple(VALUE_COLORS[0][:3])] * 2
    assert marker_colour(panel, "b") == [tuple(VALUE_COLORS[1][:3])] * 2


def test_the_plot_takes_the_colours_of_the_live_data_window(context):
    from pyacquisition.gui.components.live_data_window import LiveDataWindow

    live = LiveDataWindow()
    panel, _ = make(colors=lambda key: live.colors.get(key))
    row = {"T": 1.0, "V": 2.0, "count": 3.0}

    live.update(row)  # the cards take their colours first, as the Gui does
    feed(panel, [row])

    for key in row:
        assert marker_colour(panel, key) == [tuple(live.colors[key][:3])] * 2


def test_text_booleans_and_missing_values_are_not_plotted(context):
    panel, _ = make()

    feed(panel, [{"a": "ok", "b": True, "c": None, "d": math.nan, "e": math.inf, "f": 1.0}])

    assert list(panel.series) == ["f"]


def test_a_row_with_nothing_to_plot_is_ignored(context):
    panel, _ = make()

    feed(panel, [{"a": "ok"}])

    assert panel.series == {} and len(panel.rows) == 0 and panel.x_key is None


def test_only_the_latest_rows_are_kept(context, monkeypatch):
    monkeypatch.setattr(module, "MAX_POINTS", 5)
    panel = PlotPanel(clock=Clock())

    feed(panel, [{"time": float(i), "x": float(i) * 10} for i in range(9)])

    assert points(panel, "x") == ([4.0, 5.0, 6.0, 7.0, 8.0], [40.0, 50.0, 60.0, 70.0, 80.0])


def test_points_are_only_drawn_when_there_is_something_new(context):
    panel, _ = make()
    feed(panel, [{"time": 0.0, "x": 1.0}])

    dpg.set_value(panel.series["x"], [[9.0], [9.0]])  # what a redraw would replace
    panel.tick()
    assert points(panel, "x") == ([9.0], [9.0]), "Nothing new, so nothing redrawn."

    feed(panel, [{"time": 1.0, "x": 2.0}])
    assert points(panel, "x") == ([0.0, 1.0], [1.0, 2.0])


# --- the x axis is a measurement, and there is no time of its own ---


def test_there_is_no_time_of_its_own_only_the_measurements_are_offered(context):
    panel, _ = make()
    assert dpg.get_item_configuration(panel.x_axis_choice)["items"] == []

    feed(panel, [{"T": 4.0, "V": 1.0}])
    feed(panel, [{"count": 2}])

    assert dpg.get_item_configuration(panel.x_axis_choice)["items"] == ["T", "V", "count"]
    assert not hasattr(module, "TIME")


def test_time_is_the_x_axis_when_the_experiment_measures_it(context):
    panel, _ = make()

    feed(panel, [{"T": 4.0, "time": 10.0}, {"T": 5.0, "time": 11.0}])

    assert panel.x_key == "time"
    assert dpg.get_value(panel.x_axis_choice) == "time"
    assert dpg.get_item_label(panel.x_axis) == "time"
    assert points(panel, "T") == ([10.0, 11.0], [4.0, 5.0])


def test_otherwise_the_first_measurement_is_the_x_axis(context):
    panel, _ = make()

    feed(panel, [{"T": 4.0, "V": 1.0}, {"T": 5.0, "V": 2.0}])

    assert panel.x_key == "T"
    assert points(panel, "V") == ([4.0, 5.0], [1.0, 2.0])


def test_the_x_measurement_is_not_plotted_against_itself(context):
    panel, _ = make()

    feed(panel, [{"time": 1.0, "T": 4.0}, {"time": 2.0, "T": 5.0}])

    assert points(panel, "time") == ([], [])
    assert dpg.get_item_configuration(panel.series["time"])["show"] is False
    assert "time" not in panel.pills, "And it has no pill."
    assert list(panel.pills) == ["T"]


def test_the_x_axis_can_be_another_measurement(context):
    panel, _ = make()
    feed(panel, [{"time": 0.0, "T": 4.0, "V": 1.0}, {"time": 1.0, "T": 5.0, "V": 2.0}])

    panel.set_x_key("T")

    assert points(panel, "V") == ([4.0, 5.0], [1.0, 2.0])
    assert points(panel, "time") == ([4.0, 5.0], [0.0, 1.0]), "Time is a measurement like the others."
    assert points(panel, "T") == ([], [])
    assert dpg.get_item_label(panel.x_axis) == "T"
    assert dpg.get_value(panel.x_axis_choice) == "T"
    assert list(panel.pills) == ["time", "V"], "The pill of the x measurement goes, and time's comes."


def test_choosing_from_the_list_sets_the_x_axis(context):
    panel, _ = make()
    feed(panel, [{"time": 0.0, "T": 4.0, "V": 1.0}])

    dpg.get_item_callback(panel.x_axis_choice)(panel.x_axis_choice, "V", None)

    assert panel.x_key == "V"


def test_an_unknown_x_axis_is_refused_and_leaves_it_as_it_was(context):
    panel, _ = make()
    feed(panel, [{"T": 4.0}])

    panel.set_x_key("nothing")

    assert panel.x_key == "T"


def test_rows_without_the_x_measurement_are_left_out(context):
    panel, _ = make()
    feed(panel, [{"T": 4.0, "V": 1.0}, {"V": 2.0}, {"T": 6.0, "V": 3.0}])

    assert points(panel, "V") == ([4.0, 6.0], [1.0, 3.0])


def test_a_measurement_that_stops_being_a_number_keeps_its_points(context):
    panel, _ = make()

    feed(panel, [{"time": 0.0, "x": 1.0}, {"time": 1.0, "x": "error"}, {"time": 2.0, "x": 3.0}])

    assert points(panel, "x") == ([0.0, 2.0], [1.0, 3.0])


def test_clear_forgets_the_points_and_keeps_the_series(context):
    panel, _ = make()
    feed(panel, [{"time": 0.0, "x": 1.0}, {"time": 1.0, "x": 2.0}])

    dpg.get_item_callback(panel.clear_tag)(panel.clear_tag, None, None)

    assert points(panel, "x") == ([], []) and "x" in panel.series
    assert len(panel.rows) == 0 and panel.x_key == "time"
    feed(panel, [{"time": 5.0, "x": 5.0}])
    assert points(panel, "x") == ([5.0], [5.0])


# --- autofit, with a margin ---


def test_the_limits_add_five_percent_of_the_range_at_each_side():
    low, high = PlotPanel.limits([10.0, 20.0, 15.0])

    assert AUTOFIT_MARGIN == 0.05
    assert low == pytest.approx(10.0 - 0.05 * 10.0)
    assert high == pytest.approx(20.0 + 0.05 * 10.0)


@pytest.mark.parametrize(
    "values",
    [[0.0, 1.0], [1e-9, 3e-9], [-500.0, 500.0], [1e6, 1e6 + 2.0], [3.0, 8.0, 5.5]],
)
def test_the_margin_is_relative_to_the_range_of_the_data(values):
    low, high = PlotPanel.limits(values)
    dx = max(values) - min(values)

    assert min(values) - low == pytest.approx(0.05 * dx)
    assert high - max(values) == pytest.approx(0.05 * dx)
    assert (high - low) == pytest.approx(1.1 * dx), "The data is 10/11 of the axis."


def test_data_that_never_changes_gets_a_margin_of_five_percent_of_its_size():
    low, high = PlotPanel.limits([200.0, 200.0])
    assert (low, high) == pytest.approx((190.0, 210.0))
    low, high = PlotPanel.limits([-40.0])
    assert (low, high) == pytest.approx((-42.0, -38.0))


def test_data_that_is_all_zero_still_gets_a_range():
    low, high = PlotPanel.limits([0.0, 0.0])
    assert low < 0 < high


def test_autofit_sets_the_limits_of_both_axes_with_the_margin(context, monkeypatch):
    panel, _ = make()
    found = limits_set(monkeypatch)

    feed(panel, [{"time": 0.0, "T": 10.0}, {"time": 100.0, "T": 20.0}])

    assert found[panel.x_axis] == pytest.approx((-5.0, 105.0)), "5% of 100 at each side."
    assert found[panel.y_axis] == pytest.approx((9.5, 20.5)), "5% of 10 at each side."


def test_the_extreme_points_are_not_on_the_edges(context, monkeypatch):
    panel, _ = make()
    found = limits_set(monkeypatch)
    rows = [{"time": float(i), "T": float(i * i)} for i in range(11)]

    feed(panel, rows)

    (x_low, x_high), (y_low, y_high) = found[panel.x_axis], found[panel.y_axis]
    assert x_low < 0 and x_high > 10 and y_low < 0 and y_high > 100
    assert (0 - x_low) / (x_high - x_low) > 0.04


def test_the_fit_covers_every_measurement_that_is_shown_and_not_the_hidden_ones(context, monkeypatch):
    panel, _ = make()
    found = limits_set(monkeypatch)
    feed(panel, [{"time": 0.0, "a": 1.0, "b": 1000.0}, {"time": 1.0, "a": 2.0, "b": 2000.0}])
    assert found[panel.y_axis][1] > 2000

    panel.set_shown("b", False)

    assert found[panel.y_axis] == pytest.approx((0.95, 2.05)), "Only `a` is left to fit."


def test_normalised_data_is_fitted_with_the_margin_too(context, monkeypatch):
    panel, _ = make()
    found = limits_set(monkeypatch)
    feed(panel, [{"time": 0.0, "a": 5.0}, {"time": 1.0, "a": 15.0}])

    panel._normalise_changed(None, True)

    assert found[panel.y_axis] == pytest.approx((-0.05, 1.05))


def test_the_x_axis_is_fitted_to_the_new_measurement_when_it_is_changed(context, monkeypatch):
    panel, _ = make()
    found = limits_set(monkeypatch)
    feed(panel, [{"time": 0.0, "T": 4.0, "V": 1.0}, {"time": 10.0, "T": 8.0, "V": 2.0}])

    panel.set_x_key("T")

    assert found[panel.x_axis] == pytest.approx((3.8, 8.2))


def test_nothing_is_fitted_when_there_is_nothing_to_fit(context, monkeypatch):
    panel, _ = make()
    found = limits_set(monkeypatch)

    panel.tick()
    feed(panel, [{"only": 1.0}])  # one measurement: it is the x axis, and there is nothing under it

    assert found == {}


def fitted_axes(monkeypatch):
    calls = {"limits": 0, "released": 0}
    monkeypatch.setattr(dpg, "set_axis_limits", lambda axis, low, high: calls.__setitem__("limits", calls["limits"] + 1))
    monkeypatch.setattr(dpg, "set_axis_limits_auto", lambda axis: calls.__setitem__("released", calls["released"] + 1))
    return calls


def mouse(monkeypatch, over=True, down=False):
    monkeypatch.setattr(dpg, "get_item_rect_min", lambda item: (0, 0))
    monkeypatch.setattr(dpg, "get_item_rect_max", lambda item: (500, 400))
    monkeypatch.setattr(dpg, "get_mouse_pos", lambda local=True: (250, 200) if over else (900, 900))
    monkeypatch.setattr(dpg, "is_mouse_button_down", lambda button: down)


def test_the_axes_fit_the_data_as_it_arrives_to_start_with(context, monkeypatch):
    panel, _ = make()
    calls = fitted_axes(monkeypatch)
    mouse(monkeypatch, over=False)

    assert panel.auto is True and dpg.get_value(panel.auto_tag) is True
    feed(panel, [{"time": 0.0, "x": 1.0}])

    assert calls["limits"] == 2


def test_merely_hovering_over_the_plot_or_its_axes_does_not_stop_the_fitting(context, monkeypatch):
    panel, _ = make()
    calls = fitted_axes(monkeypatch)
    mouse(monkeypatch, over=True, down=False)

    feed(panel, [{"time": 0.0, "x": 1.0}])
    feed(panel, [{"time": 1.0, "x": 2.0}])

    assert panel.auto is True and calls["released"] == 0
    assert calls["limits"] == 4, "Only when there was new data."


def test_dragging_the_plot_or_its_axes_stops_the_fitting_and_frees_the_axes(context, monkeypatch):
    panel, _ = make()
    calls = fitted_axes(monkeypatch)
    mouse(monkeypatch, over=True, down=True)
    panel.update({"time": 0.0, "x": 1.0})

    panel.tick()

    assert panel.auto is False and dpg.get_value(panel.auto_tag) is False
    assert calls["limits"] == 0, "It was being used, so it is left where it is put."
    assert calls["released"] == 2, "The limits are taken off, so that it can be dragged."

    panel.update({"time": 1.0, "x": 2.0})
    mouse(monkeypatch, over=False)
    panel.tick()
    assert calls["limits"] == 0, "And it stays put, whatever the mouse does after."


def test_a_drag_that_starts_off_the_plot_does_not_stop_the_fitting(context, monkeypatch):
    panel, _ = make()
    mouse(monkeypatch, over=False, down=True)

    feed(panel, [{"time": 0.0, "x": 1.0}])

    assert panel.auto is True


def test_scrolling_over_the_plot_stops_the_fitting(context, monkeypatch):
    panel, _ = make()
    calls = fitted_axes(monkeypatch)
    mouse(monkeypatch, over=True, down=False)

    panel._wheel(None, 1)
    panel.update({"time": 0.0, "x": 1.0})
    panel.tick()

    assert panel.auto is False and calls["limits"] == 0


def test_scrolling_elsewhere_does_not(context, monkeypatch):
    panel, _ = make()
    mouse(monkeypatch, over=False)

    panel._wheel(None, 1)
    feed(panel, [{"time": 0.0, "x": 1.0}])

    assert panel.auto is True


def test_a_scroll_stops_counting_after_a_moment(context, monkeypatch):
    clock = Clock()
    panel = PlotPanel(clock=clock)
    mouse(monkeypatch, over=True)
    panel._wheel(None, 1)

    clock.now += module.WHEEL_WINDOW + 0.1
    panel.set_auto(True)
    feed(panel, [{"time": 0.0, "x": 1.0}])

    assert panel.auto is True, "The wheel has not turned for a while."


def test_ticking_autofit_again_fits_the_axes_now(context, monkeypatch):
    panel, _ = make()
    feed(panel, [{"time": 0.0, "x": 1.0}, {"time": 1.0, "x": 3.0}])
    panel.set_auto(False)
    calls = fitted_axes(monkeypatch)

    dpg.get_item_callback(panel.auto_tag)(panel.auto_tag, True, None)

    assert panel.auto is True and calls["limits"] == 2


def test_unticking_autofit_leaves_the_axes_where_they_are_and_frees_them(context, monkeypatch):
    panel, _ = make()
    calls = fitted_axes(monkeypatch)
    mouse(monkeypatch, over=False)

    dpg.get_item_callback(panel.auto_tag)(panel.auto_tag, False, None)
    feed(panel, [{"time": 0.0, "x": 1.0}])

    assert panel.auto is False and calls["limits"] == 0 and calls["released"] == 2


# --- normalise ---


def test_normalising_draws_each_measurement_from_zero_to_one(context):
    panel, _ = make()
    feed(panel, [
        {"time": 0.0, "small": 0.0, "big": 100.0},
        {"time": 1.0, "small": 5.0, "big": 300.0},
        {"time": 2.0, "small": 10.0, "big": 200.0},
    ])
    assert points(panel, "big")[1] == [100.0, 300.0, 200.0]

    panel._normalise_changed(None, True)

    assert points(panel, "small")[1] == [0.0, 0.5, 1.0]
    assert points(panel, "big")[1] == [0.0, 1.0, 0.5]
    assert points(panel, "big")[0] == [0.0, 1.0, 2.0], "The x values are as they were."
    assert dpg.get_item_label(panel.y_axis) == "normalised"

    panel._normalise_changed(None, False)
    assert points(panel, "big")[1] == [100.0, 300.0, 200.0]
    assert dpg.get_item_label(panel.y_axis) == "value"


def test_a_measurement_that_never_changes_is_drawn_in_the_middle_when_normalised(context):
    panel, _ = make()
    feed(panel, [{"time": float(i), "flat": 7.0} for i in range(3)])

    panel._normalise_changed(None, True)

    assert points(panel, "flat")[1] == [0.5, 0.5, 0.5]


def test_the_checkbox_normalises(context):
    panel, _ = make()
    feed(panel, [{"time": 0.0, "x": 1.0}])

    dpg.get_item_callback(panel.normalise_tag)(panel.normalise_tag, True, None)

    assert panel.normalise is True


# --- the legend: a column of small coloured pills ---


def pill_colour(panel, key):
    theme = dpg.get_item_theme(panel.pills[key])
    component = dpg.get_item_children(theme, 1)[0]
    colours = {
        dpg.get_item_configuration(i)["target"]: dpg.get_value(i)
        for i in dpg.get_item_children(component, 1)
        if dpg.get_item_type(i).endswith("mvThemeColor")
    }
    return scaled(colours[dpg.mvThemeCol_Button])[:3], scaled(colours[dpg.mvThemeCol_Text])[:3]


def test_the_legend_is_a_pill_for_each_plotted_measurement_and_not_the_plots_own(context):
    panel, _ = make()

    feed(panel, [{"time": 0.0, "T": 4.0, "V": 1.0, "count": 2.0}])

    assert list(panel.pills) == ["T", "V", "count"]
    assert [dpg.get_item_label(p) for p in panel.pills.values()] == ["T", "V", "count"]
    assert not any(dpg.get_item_type(i).endswith("mvPlotLegend") for i in dpg.get_all_items())


def test_a_pill_is_in_the_colour_of_its_points_with_dark_text(context):
    panel, _ = make(colors=lambda key: {"a": (10, 200, 30)}.get(key))

    feed(panel, [{"time": 0.0, "a": 1.0}])

    button, text = pill_colour(panel, "a")
    assert button == (10, 200, 30)
    assert max(text) < 40, "Dark, so that it reads on every colour."


def test_a_pill_is_rounded_all_the_way_and_as_small_as_the_badges_in_the_headers(context):
    from pyacquisition.gui.components.header import PaneHeader

    panel, _ = make()
    feed(panel, [{"time": 0.0, "a": 1.0}])
    pill = panel.pills["a"]
    styles = theme_values(dpg.get_item_theme(pill), "mvThemeStyle")

    height = dpg.get_item_configuration(pill)["height"]
    assert height == PaneHeader.BADGE_HEIGHT == module.PILL_HEIGHT, "The size of a badge."
    assert styles[dpg.mvStyleVar_FrameRounding][0] >= height / 2, "A pill, and not a box."


def test_the_pills_are_stacked_in_a_column_to_the_right_of_the_plot(context):
    panel, _ = make()

    feed(panel, [{"time": 0.0, "T": 4.0, "V": 1.0, "count": 2.0}])

    assert {dpg.get_item_parent(p) for p in panel.pills.values()} == {panel.pills_tag}
    children = dpg.get_item_children(dpg.get_item_parent(panel.plot), 1)
    assert children.index(panel.plot) < children.index(panel.legend_tag), "After the plot."
    assert list(dpg.get_item_children(panel.pills_tag, 1)) == list(panel.pills.values())


def test_the_plot_is_as_wide_as_what_the_legend_leaves(context):
    panel, _ = make()
    feed(panel, [{"time": 0.0, "a_rather_long_measurement_name": 1.0}])
    panel.update_layout()

    legend = dpg.get_item_configuration(panel.legend_tag)["width"]
    plot = dpg.get_item_configuration(panel.plot)["width"]
    width = dpg.get_item_configuration(panel.window_tag)["width"]
    assert legend >= panel._pill_width("a_rather_long_measurement_name")
    assert plot + legend + module.LEGEND_GAP + 2 * module.MARGIN <= width


def test_the_legend_is_never_narrower_than_a_minimum(context):
    panel, _ = make()

    assert dpg.get_item_configuration(panel.legend_tag)["width"] == module.MINIMUM_LEGEND


def test_clicking_a_pill_hides_the_points_and_dims_the_pill(context):
    panel, _ = make(colors=lambda key: (200, 100, 50))
    feed(panel, [{"time": 0.0, "a": 1.0, "b": 2.0}])

    pill = panel.pills["a"]
    dpg.get_item_callback(pill)(pill, None, dpg.get_item_user_data(pill))

    assert dpg.get_item_configuration(panel.series["a"])["show"] is False
    assert dpg.get_item_configuration(panel.series["b"])["show"] is True
    assert panel.hidden == {"a"}
    dim, text = pill_colour(panel, "a")
    assert max(dim) < 80, "Dimmed."
    assert text == (200, 100, 50), "The name is in its colour, on the dim pill."
    assert pill_colour(panel, "b")[0] == (200, 100, 50)


def test_clicking_a_dimmed_pill_shows_the_points_again(context):
    panel, _ = make(colors=lambda key: (200, 100, 50))
    feed(panel, [{"time": 0.0, "a": 1.0}])
    panel.set_shown("a", False)

    pill = panel.pills["a"]
    dpg.get_item_callback(pill)(pill, None, dpg.get_item_user_data(pill))

    assert dpg.get_item_configuration(panel.series["a"])["show"] is True
    assert panel.hidden == set()
    assert pill_colour(panel, "a")[0] == (200, 100, 50)


def test_hiding_an_unknown_measurement_does_nothing(context):
    panel, _ = make()

    panel.set_shown("nothing", False)

    assert panel.hidden == set()


def test_many_pills_stay_in_the_one_column_and_it_scrolls(context):
    panel, _ = make()

    feed(panel, [{"time": 0.0, **{f"measurement_{i}": float(i) for i in range(30)}}])

    assert len(panel.pills) == 30
    assert {dpg.get_item_parent(p) for p in panel.pills.values()} == {panel.pills_tag}
    assert dpg.get_item_configuration(panel.legend_tag)["height"] == -1, "The column scrolls."


def test_the_hidden_state_survives_the_pills_being_drawn_again(context):
    panel, _ = make(colors=lambda key: (200, 100, 50))
    feed(panel, [{"time": 0.0, "a": 1.0, "b": 2.0}])
    panel.set_shown("a", False)

    feed(panel, [{"time": 1.0, "a": 1.0, "b": 2.0, "c": 3.0}])  # a new one redraws them all

    assert pill_colour(panel, "a")[0] != (200, 100, 50) and "a" in panel.hidden
    assert pill_colour(panel, "c")[0] == (200, 100, 50)


def test_a_hidden_measurement_stays_hidden_when_the_points_are_drawn_again(context):
    panel, _ = make()
    feed(panel, [{"time": 0.0, "a": 1.0, "b": 2.0}])
    panel.set_shown("a", False)

    feed(panel, [{"time": 1.0, "a": 1.5, "b": 2.5}])

    assert dpg.get_item_configuration(panel.series["a"])["show"] is False


# --- the choices are in the column to the right of the plot, above the pills ---


def test_the_choices_are_in_the_column_beside_the_plot_and_not_above_it(context):
    panel, _ = make()

    for tag in (panel.clear_tag, panel.x_axis_choice, panel.normalise_tag, panel.auto_tag):
        assert dpg.get_item_parent(tag) == panel.legend_tag, tag
    children = dpg.get_item_children(panel.window_tag, 1)
    assert len(children) == 1, "Only the plot and its column are in the window."
    assert dpg.get_item_children(children[0], 1)[0] == panel.plot, "The plot starts at the top."


def test_the_choices_are_above_the_pills_in_the_column(context):
    panel, _ = make()
    feed(panel, [{"time": 0.0, "a": 1.0}])

    column = dpg.get_item_children(panel.legend_tag, 1)
    order = [panel.clear_tag, panel.x_axis_choice, panel.normalise_tag, panel.auto_tag, panel.pills_tag]
    positions = [column.index(item) for item in order]
    assert positions == sorted(positions)
    assert dpg.get_item_parent(panel.pills["a"]) == panel.pills_tag


def test_the_choices_fill_the_width_of_the_column(context):
    panel, _ = make()

    assert dpg.get_item_configuration(panel.clear_tag)["width"] == -1
    assert dpg.get_item_configuration(panel.x_axis_choice)["width"] == -1


def test_the_column_is_wide_enough_for_the_choices(context):
    assert module.MINIMUM_LEGEND >= 150
    panel, _ = make()
    assert dpg.get_item_configuration(panel.legend_tag)["width"] >= module.MINIMUM_LEGEND


def test_the_plot_fills_the_height_of_the_window(context):
    panel, _ = make()

    assert dpg.get_item_configuration(panel.plot)["height"] == -1
