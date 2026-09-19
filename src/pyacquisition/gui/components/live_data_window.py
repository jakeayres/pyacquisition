import dearpygui.dearpygui as dpg
import time
from .header import PaneHeader
from .styles import card_themes
from ..constants import EMPHASIS_COLOR, SECONDARY_COLOR, WHITE

# How the pane shows whether data is arriving: a badge, if the data needs attention,
# and the colour of the header and of the border of the card around the values.
# While data arrives the green border says so, and there is no badge.
FEED = {
    "waiting": ("WAITING", "idle"),
    "live": (None, "running"),
    "stale": ("STALE", "paused"),
}

WINDOW_WIDTH = 300
HEADER_WIDTH = WINDOW_WIDTH - 16  # the width of the window, less its padding


class LiveDataWindow:
    """
    The pane that shows the latest value of every measurement, in a card.

    The card has a green border while rows keep arriving, like the card of a running
    task. It turns amber, and the header says `STALE`, if none has arrived for a
    while, and it is grey, with `WAITING`, before the first row.
    """

    STALE_AFTER = 3.0  # seconds without a row

    def __init__(self, clock=time.monotonic):
        """
        Args:
            clock: Returns the time in seconds, for telling when data stops
                arriving. Defaults to `time.monotonic`.
        """
        self._clock = clock
        self._last_row = None
        self.feed = None
        self.card_style = None
        self.window_tag = dpg.generate_uuid()
        self.time_group_tag = dpg.generate_uuid()
        self.time_tag = dpg.generate_uuid()
        self.key_tags = {}
        self.value_tags = {}
        self._last_update = None

        with dpg.window(
            label="Live Data",
            pos=[20, 140],
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
            self.header = PaneHeader(self.window_tag, HEADER_WIDTH, title="LIVE DATA")
            dpg.add_spacer(height=4)

            # The values are in a card that fits them, with a border coloured by
            # whether data is arriving.
            self._themes = card_themes()
            self.card_tag = dpg.add_child_window(
                width=-1, auto_resize_y=True, border=True
            )
            self._show_feed("waiting")

            with dpg.group(
                horizontal=True, tag=self.time_group_tag, parent=self.card_tag
            ):
                dpg.add_text("Loop Time      ", color=EMPHASIS_COLOR)
                dpg.add_text("0.000 s", tag=self.time_tag, color=WHITE)

    def _show_feed(self, feed: str) -> None:
        """Show whether data is arriving, if that has changed."""
        if feed == self.feed:
            return
        self.feed = feed
        badge, style = FEED[feed]
        self.header.update(title="LIVE DATA", badge=badge, style=style)
        dpg.bind_item_theme(self.card_tag, self._themes[style])
        self.card_style = style

    def tick(self) -> None:
        """
        Call this often, such as once a frame. It notices when the data stops
        arriving, which no incoming row could tell it.
        """
        if self._last_row is None:
            return
        stale = self._clock() - self._last_row > self.STALE_AFTER
        self._show_feed("stale" if stale else "live")

    def _add_row(self, key: str, value):
        """
        Add a row for a key, above the loop time row.
        """
        with dpg.group(
            horizontal=True, parent=self.card_tag, before=self.time_group_tag
        ):
            tag = dpg.generate_uuid()
            self.key_tags[key] = tag
            dpg.add_text(f"{key:{' '}<{15}}", tag=tag, color=SECONDARY_COLOR)

            tag = dpg.generate_uuid()
            self.value_tags[key] = tag
            dpg.add_text(f"{value:{' '}<{15}}", tag=tag)

    def update(self, data: dict):
        """
        Update the window with a new row of data.
        """
        now = time.time()
        self._last_row = self._clock()
        self._show_feed("live")
        self.header.fit_to(self.window_tag)  # the rows may have brought a scroll bar

        for key, value in data.items():
            if key not in self.key_tags:
                self._add_row(key, value)
            else:
                dpg.set_value(self.value_tags[key], f"{value:{' '}<{15}}")

        if self._last_update is not None:
            dpg.set_value(self.time_tag, f"{now - self._last_update:.3f} s")
        self._last_update = now
