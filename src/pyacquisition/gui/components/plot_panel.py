import math
import time
from collections import deque

import dearpygui.dearpygui as dpg

from ...core.logging import logger
from ..constants import STATE_STYLES, VALUE_COLORS, plot_x
from .header import CHAR_WIDTH
from .numbers import is_number

PREFERRED_X = "time"  # the measurement that is the x axis, if there is one, to start with
AUTOFIT_MARGIN = 0.05  # of the range of the data, added at each side by autofit
MAX_POINTS = 5000  # rows that are kept, and so drawn
MARKER_SIZE = 3
MARGIN = 24  # between the plot and the edges of the window

# The legend is a column of small pills, stacked to the right of the plot, one for each
# measurement, in its colour: the size and shape of the badges in the headers.
PILL_HEIGHT = 20
PILL_PADDING = 10  # at each side of the name, inside the pill
PILL_GAP = 6  # between one pill and the next
PILL_TEXT = (12, 14, 20)  # dark, so that it reads on every colour of the palette
PILL_DIM = 0.28  # how much of its colour a pill keeps while its points are hidden
LEGEND_GAP = 12  # between the plot and the pills
MINIMUM_LEGEND = 170  # wide enough for the choices above the pills

# The plot blends into the rest of the app: the same black behind it as the pages have,
# the area inside its axes the colour of the cards, no border, and a grid and text that
# are quiet against it.
BACKGROUND = (0, 0, 0)
CLEAR = (0, 0, 0, 0)
PLOT_BACKGROUND = STATE_STYLES["neutral"]["background"]  # the colour of the cards
GRID = (50, 58, 74)
AXIS_TEXT = (150, 156, 170)

WHEEL_WINDOW = 0.3  # seconds that the scroll wheel counts as being used, after it turns


class PlotPanel:
    """
    The right seven twelfths of the window: a plot of every numeric measurement, as points, one
    colour each: the colour of its card in the Live Data window. It is the same
    whichever page is shown in the left part.

    It is the plot that dearpygui gives, on the black of the rest of the app, with the
    area inside its axes the colour of the cards, no border, and a moderate margin
    around it, so everything that the plot offers on a right click is there: fitting
    the axes, the scales, the grid, and copying. The legend is a column of small
    coloured pills to the right of the plot: click one to hide or show the points of its
    measurement.

    The choices are in the same column, above the pills. They are the ones that the
    floating plot window had: **Clear** to forget the points, and the **x-axis**, which
    is one of the measurements: nothing else is offered, so if the time is wanted it is
    a measurement of the experiment, and it is the x axis to start with if there is one
    called `time`, or else the first measurement. A measurement that is the x axis is
    not also plotted against itself. There is also **Normalise**, which draws each
    measurement from 0 to 1 of its own range, for measurements of very different sizes.

    **Autofit** keeps the axes fitted to the data as it arrives, with a margin of 5% of
    the range of the data added at each side, so that the extreme points are not on the
    edges of the plot. It is ticked to start
    with, and unticks itself as soon as the plot is used, by dragging it or scrolling it
    with the mouse over it or over its axes, so that it stays where it was put to be
    zoomed and read. Tick it again to fit the axes again.
    """

    def __init__(self, colors=None, clock=time.monotonic):
        """
        Args:
            colors: Given the name of a measurement, returns its colour, or `None` if it
                has none. It is how its points take the colour of its card.
            clock: Returns the time in seconds, for telling that the wheel has turned.
        """
        self._colors = colors or (lambda key: None)
        self._clock = clock
        self.rows = deque(maxlen=MAX_POINTS)  # the numbers of each row
        self.series = {}  # the points of each measurement
        self.colors = {}  # the colour of each
        self.hidden = set()  # the measurements whose points are not shown
        self.pills = {}  # the pill of each, which is its legend
        self.x_key = None  # the measurement that is the x axis
        self.normalise = False
        self.auto = True
        self._dirty = False
        self._wheel_at = None  # when the wheel last turned over the plot
        self._width = None
        self.window_tag = dpg.generate_uuid()

        with dpg.window(
            label="Plot",
            pos=[0, 0],
            width=400,
            height=600,
            no_title_bar=True,
            no_close=True,
            no_collapse=True,
            no_resize=True,
            no_move=True,
            no_bring_to_front_on_focus=True,
            no_focus_on_appearing=True,
            tag=self.window_tag,
        ):
            # The plot, and beside it a column with the choices for it and the legend.
            with dpg.group(horizontal=True):
                self.plot = dpg.add_plot(label="Live Data Plot", width=-1, height=-1)
                self.x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="x", parent=self.plot)
                self.y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="value", parent=self.plot)
                self.legend_tag = dpg.add_child_window(
                    width=MINIMUM_LEGEND, height=-1, border=False
                )
            column = self.legend_tag
            self.clear_tag = dpg.add_button(
                label="Clear", width=-1, callback=self.clear, parent=column
            )
            dpg.add_text("x-axis", color=AXIS_TEXT, parent=column)
            self.x_axis_choice = dpg.add_combo(
                [],
                default_value="",
                width=-1,
                callback=self._x_key_chosen,
                parent=column,
            )
            self.normalise_tag = dpg.add_checkbox(
                label="Normalise", callback=self._normalise_changed, parent=column
            )
            self.auto_tag = dpg.add_checkbox(
                label="Autofit",
                default_value=True,
                callback=self._auto_changed,
                parent=column,
            )
            dpg.add_separator(parent=column)
            self.pills_tag = dpg.add_group(parent=column)  # the legend, under the choices
        with dpg.handler_registry() as self._handlers:
            dpg.add_mouse_wheel_handler(callback=self._wheel)
        self._theme = self._make_theme()
        dpg.bind_item_theme(self.window_tag, self._theme)
        self.update_layout()

    @staticmethod
    def _make_theme():
        """Black behind the plot, as behind the pages, with a margin around it."""
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvWindowAppItem):
                dpg.add_theme_color(
                    dpg.mvThemeCol_WindowBg, BACKGROUND, category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_Border, CLEAR, category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ChildBg, CLEAR, category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_style(
                    dpg.mvStyleVar_WindowPadding, MARGIN, MARGIN, category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_style(
                    dpg.mvStyleVar_WindowBorderSize, 0, category=dpg.mvThemeCat_Core
                )
            with dpg.theme_component(dpg.mvPlot):
                for column, colour in (
                    (dpg.mvPlotCol_FrameBg, CLEAR),
                    (dpg.mvPlotCol_PlotBg, PLOT_BACKGROUND),
                    (dpg.mvPlotCol_PlotBorder, CLEAR),
                    (dpg.mvPlotCol_AxisGrid, GRID),
                    (dpg.mvPlotCol_AxisText, AXIS_TEXT),
                ):
                    dpg.add_theme_color(column, colour, category=dpg.mvThemeCat_Plots)
        return theme

    # --- the window ---

    def update_layout(self) -> None:
        """
        Keep the panel over the right seven twelfths of the window, top to bottom, with the plot
        as wide as what is left of it when the legend has its share.
        """
        viewport_width = dpg.get_viewport_client_width()
        viewport_height = dpg.get_viewport_client_height()
        x = plot_x(viewport_width)
        width = max(viewport_width - x, 200)
        dpg.configure_item(
            self.window_tag,
            pos=[x, 0],
            width=width,
            height=max(viewport_height, 100),
        )
        legend = self._legend_width()
        if width != self._width or legend != dpg.get_item_configuration(self.legend_tag)["width"]:
            self._width = width
            dpg.configure_item(self.legend_tag, width=legend)
            dpg.configure_item(
                self.plot, width=max(width - 2 * MARGIN - legend - LEGEND_GAP, 100)
            )

    def _legend_width(self) -> int:
        """How wide the column of pills is: as wide as the widest pill, and no less than a
        minimum, so that the plot does not jump about as measurements come."""
        widest = max(
            (self._pill_width(key) for key in self.series if key != self.x_key), default=0
        )
        return max(widest + 2 * PILL_GAP, MINIMUM_LEGEND)

    # --- the data ---

    def update(self, row: dict) -> None:
        """
        Add a row of data: a point for each measurement in it that is a finite number.
        Anything else, such as text, is not plotted.

        Args:
            row (dict): The measurements, by name.
        """
        numbers = {
            key: float(value)
            for key, value in row.items()
            if is_number(value) and math.isfinite(value)
        }
        if not numbers:
            return
        self.rows.append(numbers)
        new = [key for key in numbers if key not in self.series]
        for key in new:
            self._add_series(key)
        if new:
            dpg.configure_item(self.x_axis_choice, items=list(self.series))
            if self.x_key is None:
                self._choose_x(PREFERRED_X if PREFERRED_X in self.series else next(iter(self.series)))
            self._layout_legend()
            self.update_layout()
        self._dirty = True

    def _add_series(self, key: str) -> None:
        """Add the points of a measurement, in the colour of its card."""
        color = self._colors(key)
        if color is None:
            color = VALUE_COLORS[len(self.series) % len(VALUE_COLORS)]
        series = dpg.add_scatter_series([], [], label=key, parent=self.y_axis)
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvScatterSeries):
                for column in (dpg.mvPlotCol_MarkerFill, dpg.mvPlotCol_MarkerOutline):
                    dpg.add_theme_color(
                        column, tuple(color)[:3], category=dpg.mvThemeCat_Plots
                    )
                dpg.add_theme_style(
                    dpg.mvPlotStyleVar_MarkerSize,
                    MARKER_SIZE,
                    category=dpg.mvThemeCat_Plots,
                )
        dpg.bind_item_theme(series, theme)
        self.series[key] = series
        self.colors[key] = tuple(color)[:3]

    # --- the legend ---

    def _pill_width(self, key: str) -> int:
        """How wide the pill of a measurement is: its name, and room at each side."""
        return len(key) * CHAR_WIDTH + 2 * PILL_PADDING

    def _layout_legend(self) -> None:
        """
        Draw the pills again, one under another, for each measurement that is plotted:
        not the one that is the x axis.
        """
        dpg.delete_item(self.pills_tag, children_only=True)
        self.pills = {key: self._add_pill(key) for key in self.series if key != self.x_key}

    def _add_pill(self, key: str):
        """A pill: a small rounded button in the colour of a measurement, with its name."""
        shown = key not in self.hidden
        colour = self.colors[key]
        if not shown:
            colour = tuple(round(c * PILL_DIM) for c in colour)
        pill = dpg.add_button(
            label=key,
            width=self._pill_width(key),
            height=PILL_HEIGHT,
            callback=self._pill_clicked,
            user_data=key,
            parent=self.pills_tag,
        )
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvButton):
                for column, base in (
                    (dpg.mvThemeCol_Button, colour),
                    (dpg.mvThemeCol_ButtonHovered, tuple(min(c + 30, 255) for c in colour)),
                    (dpg.mvThemeCol_ButtonActive, tuple(min(c + 50, 255) for c in colour)),
                ):
                    dpg.add_theme_color(column, base, category=dpg.mvThemeCat_Core)
                text = PILL_TEXT if shown else tuple(self.colors[key])
                dpg.add_theme_color(dpg.mvThemeCol_Text, text, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(
                    dpg.mvStyleVar_FrameRounding, PILL_HEIGHT / 2, category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_style(
                    dpg.mvStyleVar_ItemSpacing, PILL_GAP, PILL_GAP, category=dpg.mvThemeCat_Core
                )
        dpg.bind_item_theme(pill, theme)
        return pill

    def set_shown(self, key: str, shown: bool) -> None:
        """
        Show or hide the points of a measurement, and light or dim its pill.

        Args:
            key (str): A measurement that has been plotted.
            shown (bool): Whether its points are shown.
        """
        if key not in self.series:
            return
        if shown:
            self.hidden.discard(key)
        else:
            self.hidden.add(key)
        dpg.configure_item(self.series[key], show=shown)
        self._layout_legend()
        if self.auto:
            self._fit()

    def _pill_clicked(self, sender=None, app_data=None, user_data=None) -> None:
        """A pill was clicked: hide the points of its measurement, or show them."""
        self.set_shown(user_data, user_data in self.hidden)

    # --- drawing ---

    def _points(self, key: str):
        """
        The points of a measurement: the x and y of each row that has a value for it and
        for the measurement that is the x axis. The y values are from 0 to 1 of their own
        range if they are normalised. The x measurement itself has none.
        """
        xs, ys = [], []
        if key == self.x_key or self.x_key is None:
            return xs, ys
        for numbers in self.rows:
            if key in numbers and self.x_key in numbers:
                xs.append(numbers[self.x_key])
                ys.append(numbers[key])
        if self.normalise and ys:
            low, high = min(ys), max(ys)
            span = high - low
            ys = [(y - low) / span if span else 0.5 for y in ys]
        return xs, ys

    def tick(self) -> None:
        """
        Call this often, such as once a frame: notice that the plot is being used, and
        stop fitting the axes to the data if it is, and draw the points that are new,
        fitting the axes to them if that is still on.
        """
        if self.auto and self._being_used():
            self.set_auto(False)
        if not self._dirty:
            return
        self._dirty = False
        self._draw()
        if self.auto:
            self._fit()

    def _draw(self) -> None:
        """Draw the points of every measurement, and hide the one that is the x axis."""
        for key, series in self.series.items():
            dpg.set_value(series, list(self._points(key)))
            dpg.configure_item(
                series, show=key not in self.hidden and key != self.x_key
            )

    @staticmethod
    def limits(values):
        """
        The limits of an axis that fits some values with a margin: the range of the
        values, `dx = max - min`, with 5% of it added at each side, so that the extreme
        points are not on the edges. Values that are all the same have no range, so the
        margin is 5% of their size instead, or 5% of 1 if that is nothing.

        Args:
            values: The values that the axis is to fit.

        Returns:
            tuple: The lower and the upper limit.
        """
        low, high = min(values), max(values)
        dx = high - low
        margin = AUTOFIT_MARGIN * (dx if dx else (abs(high) or 1.0))
        return low - margin, high + margin

    def _fit(self) -> None:
        """
        Fit both axes to the points that are shown, with a margin of 5% of the range of
        the data at each side. If there are no points there is nothing to fit, and the
        axes are left as they are.
        """
        xs, ys = [], []
        for key in self.series:
            if key in self.hidden or key == self.x_key:
                continue
            x, y = self._points(key)
            xs.extend(x)
            ys.extend(y)
        if not xs:
            return
        dpg.set_axis_limits(self.x_axis, *self.limits(xs))
        dpg.set_axis_limits(self.y_axis, *self.limits(ys))

    def _release_axes(self) -> None:
        """Let the axes be dragged and zoomed again, where they are."""
        dpg.set_axis_limits_auto(self.x_axis)
        dpg.set_axis_limits_auto(self.y_axis)

    # --- fitting the axes, and leaving them alone while the plot is used ---

    def _over_plot(self) -> bool:
        """Whether the mouse is over the plot, its axes included."""
        x, y = dpg.get_mouse_pos(local=False)
        (left, top), (right, bottom) = dpg.get_item_rect_min(self.plot), dpg.get_item_rect_max(self.plot)
        return left <= x <= right and top <= y <= bottom

    def _being_used(self) -> bool:
        """
        Whether the plot is being dragged, or scrolled, with the mouse over it or its
        axes. Hovering is not using it.
        """
        if not self._over_plot():
            return False
        dragging = dpg.is_mouse_button_down(dpg.mvMouseButton_Left) or dpg.is_mouse_button_down(
            dpg.mvMouseButton_Middle
        )
        scrolled = (
            self._wheel_at is not None and self._clock() - self._wheel_at < WHEEL_WINDOW
        )
        return dragging or scrolled

    def _wheel(self, sender=None, app_data=None, user_data=None) -> None:
        """The scroll wheel turned: it counts as using the plot if the mouse is over it."""
        if self._over_plot():
            self._wheel_at = self._clock()

    def set_auto(self, auto: bool) -> None:
        """
        Fit the axes to the data as it arrives, or leave them where they are.

        Args:
            auto (bool): Whether to fit them. Turning it on fits them now.
        """
        self.auto = auto
        dpg.set_value(self.auto_tag, auto)
        if auto:
            self._fit()
        else:
            self._release_axes()

    def _auto_changed(self, sender=None, app_data=None, user_data=None) -> None:
        """The box for fitting the axes was ticked or unticked."""
        self.set_auto(bool(app_data))

    # --- the choices above the plot ---

    def set_x_key(self, key: str) -> None:
        """
        Choose the measurement that is the x axis. It is not also plotted against itself.

        Args:
            key (str): A measurement that has been plotted.
        """
        if key not in self.series:
            logger.error(f"Key {key} not found in data.")
            return
        self._choose_x(key)
        self._layout_legend()
        self.update_layout()
        self._draw()
        self._dirty = False
        if self.auto:
            self._fit()

    def _choose_x(self, key: str) -> None:
        """Make a measurement the x axis, without drawing anything again."""
        self.x_key = key
        dpg.set_value(self.x_axis_choice, key)
        dpg.configure_item(self.x_axis, label=key)

    def _x_key_chosen(self, sender=None, app_data=None, user_data=None) -> None:
        """A choice was made in the list for the x axis."""
        self.set_x_key(app_data)

    def _normalise_changed(self, sender=None, app_data=None, user_data=None) -> None:
        """The box was ticked or unticked: draw the points again."""
        self.normalise = bool(app_data)
        dpg.configure_item(self.y_axis, label="normalised" if self.normalise else "value")
        self._draw()
        self._dirty = False
        if self.auto:
            self._fit()

    def clear(self, sender=None, app_data=None, user_data=None) -> None:
        """Forget every point. The series stay, empty."""
        self.rows.clear()
        for series in self.series.values():
            dpg.set_value(series, [[], []])
        self._dirty = False
