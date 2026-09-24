import time
from collections import deque

import dearpygui.dearpygui as dpg

from ..constants import (
    EMPHASIS_COLOR,
    DEFAULT_PAGE_WIDTH,
    FILE_PANE_HEIGHT,
    PANE_X,
    STATE_STYLES,
    TOP_Y,
    VALUE_COLORS,
    WHITE,
)
from .fonts import add_font
from .header import CHAR_WIDTH, TEXT_HEIGHT, PaneHeader, fit
from .input_card import InputCard
from .measurement_card import MeasurementCard
from .numbers import format_number, is_number
from .pane import add_rule, color_rules, fit_rules, fit_to_page, frame_theme

# How the header shows whether data is arriving: a badge, if the data needs attention,
# and the colour of its bar and underline. While data arrives it is plain grey.
FEED = {
    "waiting": ("WAITING", "idle"),
    "live": (None, "idle"),
    "stale": ("STALE", "paused"),
    "paused": ("PAUSED", "paused"),
}

WINDOW_WIDTH = DEFAULT_PAGE_WIDTH  # until it is laid out
HEADER_WIDTH = WINDOW_WIDTH - 16  # the window's width, less its padding
TIME_BACKGROUND = (16, 18, 22)  # darker than a measurement's card
LOOP_TIME_AVERAGE = 5  # how many of the latest loops the loop time averages
TIME_HEIGHT = 30  # two thirds of the height of a card
MINIMUM_PERIOD = 0.001  # the shortest time between measurements that can be set, in seconds

# A value is at most VALUE_CHARS characters, so that it fits beside the name.
VALUE_CHARS = 12
VALUE_WIDTH = VALUE_CHARS * CHAR_WIDTH + 4  # only for cutting text short
VALUE_FONT_SIZE = 20


def format_value(value) -> str:
    """A value as text for its column: a number is shortened to fit, and other text is
    cut short with `...`."""
    if is_number(value):
        return format_number(value, VALUE_CHARS)
    return fit(str(value), VALUE_WIDTH)


class LiveDataWindow:
    """
    The pane that shows the latest value of every measurement.

    The loop time is the average of the latest few loops, so that it is steady enough
    to read.

    The pane is a header with a one pixel underline as wide as the measurements
    under it, and no frame or tint. The header is grey while rows keep arriving. It
    turns amber, and says `STALE`, if none has arrived for a while, and it says
    `WAITING`, in grey, before the first row. It has an icon that pauses the
    measurements, or resumes them.

    Each measurement is a card, like the header of the file pane: a tinted strip with
    a bar at its left, the name in white with where it comes from under it in grey,
    and the value at the right in larger text. The bar and the value are the colour of
    the measurement, which is muted while the measurements are paused. Under the
    cards is the loop time, in a darker card.

    The colour of each measurement is also the colour of its line in the plot.
    """

    STALE_AFTER = 3.0  # seconds without a row

    def __init__(
        self,
        clock=time.monotonic,
        sources: dict | None = None,
        on_toggle=None,
        on_period=None,
    ):
        """
        Args:
            clock: Returns the time in seconds, for telling when data stops
                arriving. Defaults to `time.monotonic`.
            sources (dict | None): Where each measurement comes from, as
                `instrument.method`, by name. It is shown under the name. A
                measurement with none has a single line.
            on_toggle: Called, with whether the measurements are paused now, when the
                play or pause icon of the header is clicked. Without it there is no
                icon.
            on_period: Called with the number of seconds between measurements, when
                one is typed into the card for it and sent. Without it there is no
                card.
        """
        self._clock = clock
        self.sources = sources or {}
        self.on_toggle = on_toggle
        self.paused = False
        self._last_row = None
        self.feed = None
        self.window_tag = dpg.generate_uuid()
        self.cards_tag = dpg.generate_uuid()
        self.key_tags = {}
        self.value_tags = {}
        self.latest = {}  # the latest value of each measurement, in the order seen
        self.colors = {}  # the colour of each measurement
        self.cards = {}  # the card of each measurement
        self._last_update = None
        self._loops = deque(maxlen=LOOP_TIME_AVERAGE)  # the times of the latest loops
        # The font for large text. It is loaded here, and not when it is first wanted,
        # because a font can only be added before the window is first shown.
        self._large_font = add_font(VALUE_FONT_SIZE)

        with dpg.window(
            label="Live Data",
            pos=[PANE_X, TOP_Y + FILE_PANE_HEIGHT + 20],
            width=WINDOW_WIDTH,
            height=750,
            no_title_bar=True,  # the header is the title
            no_close=True,
            no_collapse=True,
            no_background=True,
            no_resize=True,
            no_move=True,
            no_bring_to_front_on_focus=True,
            no_focus_on_appearing=True,
            tag=self.window_tag,
        ):
            # A frame with no border, so it has no padding, and the header and the
            # cards are as wide as it is.
            self.frame_tag = dpg.add_child_window(
                width=-1, auto_resize_y=True, border=False
            )
            self._frame_theme = frame_theme()
            dpg.bind_item_theme(self.frame_tag, self._frame_theme)
            self.header = PaneHeader(
                self.frame_tag,
                HEADER_WIDTH,
                title="Live Data",
                flat=True,
                title_font=self._large_font,
                title_size=VALUE_FONT_SIZE,
                on_action=self._clicked if on_toggle else None,
            )

            # The values are under the header.
            self.card_tag = dpg.add_child_window(
                parent=self.frame_tag, width=-1, auto_resize_y=True, border=False
            )
            # The cards, which are added as the measurements first arrive.
            dpg.add_group(tag=self.cards_tag, parent=self.card_tag)

            # The time between measurements, which can be set, in a card of its own.
            self._rules = []
            self.period_card = None
            if on_period:
                self._add_rule()  # between the last measurement and the card
                self.period_card = InputCard(
                    self.card_tag,
                    HEADER_WIDTH,
                    label="Measurement Period",
                    caption="seconds",
                    value=1.0,
                    on_submit=on_period,
                    minimum=MINIMUM_PERIOD,
                    background=TIME_BACKGROUND,
                    format="%g",
                    input_width=80,  # so that the label has room in a narrow pane
                )

            # A line above the loop time, like the one under the header.
            self._add_rule()

            # The loop time is a card too, but darker, with orange text and no bar, so
            # that it is not taken for a measurement.
            self.time_card = MeasurementCard(
                self.card_tag,
                HEADER_WIDTH,
                name="Loop Time",
                color=WHITE,
                value_size=TEXT_HEIGHT,  # in the small font, like its name
                background=TIME_BACKGROUND,
                name_color=EMPHASIS_COLOR,
                bar=False,
                height=TIME_HEIGHT,
            )
            self.time_card.set_value("0.000 s")
            self.time_group_tag = self.time_card.container
            self.time_tag = self.time_card.value_tag

            # And one under it, closing the pane.
            self._add_rule()
            self._show_feed("waiting")

    def _add_rule(self) -> None:
        """Add a line across the pane, like the one under the header."""
        add_rule(self.card_tag, HEADER_WIDTH, self._rules)

    def _clicked(self) -> None:
        """The icon in the header was clicked."""
        self.on_toggle(self.paused)

    def set_paused(self, paused: bool) -> None:
        """
        Show whether the measurements are paused. While they are, the header and its
        lines are amber, the measurements are in muted colours so that it is clear
        that they are not being updated, and the icon is a play button, to resume.

        Args:
            paused (bool): Whether they are paused.
        """
        if paused == self.paused:
            return
        self.paused = paused
        # The time from the last row before the pause, to the first after it, is not a
        # loop, so it is not counted.
        self._loops.clear()
        self._last_update = None
        self.header.set_action("play" if paused else "pause")
        self._show_feed(self._feed_now())
        for card in self.cards.values():
            card.set_muted(paused)

    def set_period(self, seconds: float) -> None:
        """
        Show the time between measurements that the experiment has, unless a new one
        is being typed or has not been sent.

        Args:
            seconds (float): The time between measurements.
        """
        if self.period_card is not None:
            self.period_card.set_value(seconds)

    def _feed_now(self) -> str:
        """What the header should show, for whether it is paused or has had a row."""
        if self.paused:
            return "paused"
        return "waiting" if self._last_row is None else "live"

    def _show_feed(self, feed: str) -> None:
        """Show whether data is arriving, if that has changed."""
        if feed == self.feed:
            return
        self.feed = feed
        badge, style = FEED[feed]
        self.header.update(title="Live Data", badge=badge, style=style)
        color_rules(self._rules, STATE_STYLES[style]["border"])

    def _fit(self) -> None:
        """
        Keep the window as wide as a page, and the header, the cards and the lines as
        wide as it, which is narrower when a scroll bar takes some of the window.
        """
        fit_to_page(self.window_tag)
        self.header.fit_to(self.window_tag)
        width = self.header.width
        cards = (*self.cards.values(), self.time_card, self.period_card)
        for card in filter(None, cards):
            if card.width != width:
                card.resize(width)
        fit_rules(self._rules, width)

    def tick(self) -> None:
        """
        Call this often, such as once a frame. It notices when the data stops
        arriving, which no incoming row could tell it, and when the window changes
        width.
        """
        self._fit()

        if self._last_row is None:
            return
        stale = self._clock() - self._last_row > self.STALE_AFTER
        self._show_feed("paused" if self.paused else "stale" if stale else "live")

    def _add_card(self, key: str) -> None:
        """
        Add a card for a measurement, like the header of the file pane: its name in
        white, where it comes from under it in grey, and its value at the right, in
        larger text, in the colour of the measurement.
        """
        card = MeasurementCard(
            self.cards_tag,
            self.header.width,
            name=key,
            color=self.colors[key],
            source=self.sources.get(key, ""),
            font=self._large_font,
            value_size=VALUE_FONT_SIZE,
        )
        card.set_value(format_value(self.latest[key]))
        card.set_muted(self.paused)
        self.cards[key] = card
        self.key_tags[key] = card.name_tag
        self.value_tags[key] = card.value_tag

    def update(self, data: dict):
        """
        Update the window with a new row of data.
        """
        now = time.time()
        self._last_row = self._clock()
        self._show_feed("paused" if self.paused else "live")
        self._fit()  # the rows may have brought a scroll bar

        for key, value in data.items():
            self.latest[key] = value
            if key not in self.key_tags:
                self.colors.setdefault(
                    key, VALUE_COLORS[len(self.colors) % len(VALUE_COLORS)]
                )
                self._add_card(key)
            else:
                self.cards[key].set_value(format_value(value))

        if self._last_update is not None:
            self._loops.append(now - self._last_update)
            average = sum(self._loops) / len(self._loops)
            self.time_card.set_value(f"{average:.3f} s")
        self._last_update = now
