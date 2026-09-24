from collections import deque
from datetime import datetime

import dearpygui.dearpygui as dpg

from ..constants import (
    EMPHASIS_COLOR,
    ERROR_COLOR,
    MUTED_COLOR,
    SECONDARY_COLOR,
    PANE_X,
    TEXT_COLOR,
    TOP_Y,
    WHITE,
    page_width,
)
from .choice_card import ChoiceCard
from .fonts import add_font
from .header import CHAR_WIDTH, PaneHeader, fit
from .pane import frame_theme

# The levels that can be chosen to show, lowest first, and how each is shown: a short
# tag, and the colour of the tag. A message of a level that is not here is an `info`.
LEVELS = ("debug", "info", "warning", "error")
TAGS = {"trace": "TRC", "debug": "DBG", "info": "INF", "warning": "WRN", "error": "ERR"}
COLORS = {
    "trace": MUTED_COLOR,
    "debug": MUTED_COLOR,
    "info": SECONDARY_COLOR,
    "warning": EMPHASIS_COLOR,
    "error": ERROR_COLOR,
}
MESSAGE_COLORS = {"trace": MUTED_COLOR, "debug": (150, 150, 150)}
# What a level is worth, for showing it or not: `trace` is below `debug`, and an
# `exception` is as bad as an `error`.
RANKS = {"trace": 0, "debug": 1, "info": 2, "warning": 3, "error": 4, "exception": 4}
DEFAULT_LEVEL = "info"  # so that a long run does not fill the window with debug lines

MAX_LOGS = 500  # how many messages are kept, and so how many can be shown
FONT_SIZE = 20
LINE_GAP = 0  # between one line and the next, so that many fit
PREFIX_CHARS = len("12:03:44 WRN")  # the time and the tag, before each message
LEVEL_BACKGROUND = (16, 18, 22)
LOG_BACKGROUND = (12, 13, 17)
SCROLL_BAR = 14
STICK_WITHIN = 6  # pixels from the bottom that still count as being at the bottom


def rank(level: str) -> int:
    """How bad a level is, so that levels can be compared. An unknown one is an `info`."""
    return RANKS.get(level, RANKS["info"])


class LiveLogWindow:
    """
    The pane that shows the log, drawn like the other panes: a header with a one pixel
    underline, a card to choose the level that is shown, and under them the messages.

    The messages are packed close, one line each, so that many fit: the time, a
    three-letter tag for the level in its colour, and the message, which is cut short
    with `...` if it is too long for the line, and shown in full when the mouse is over
    it. The window keeps the latest few hundred messages, and choosing another level
    draws them again, so that a lower level can be looked at after it was hidden.

    It fills the left part of the window, beside the menu, when it is shown as a page.
    It follows the log as it grows, unless it has been scrolled up to read.
    """

    MINIMUM_WIDTH = 360

    def __init__(self, level: str = DEFAULT_LEVEL):
        """
        Args:
            level (str): The lowest level that is shown to start with.
        """
        if level not in LEVELS:
            raise ValueError(f"level must be one of {', '.join(LEVELS)}, got {level!r}")
        self.level = level
        self.width = self.MINIMUM_WIDTH + 240  # until it is laid out
        self.entries = deque()  # the messages kept, each with the line that shows it
        self.hidden = 0  # how many of them the level leaves out
        self._stick = True  # whether to keep the latest message in view
        self.window_tag = dpg.generate_uuid()
        self.log_tag = dpg.generate_uuid()
        self._large_font = add_font(FONT_SIZE)

        with dpg.window(
            label="Logs",
            width=self.width,
            no_title_bar=True,  # the header is the title
            no_close=True,
            no_collapse=True,
            no_background=True,
            no_resize=True,
            no_move=True,
            no_bring_to_front_on_focus=True,
            no_focus_on_appearing=True,
            no_scrollbar=True,  # the messages scroll, and not the header
            tag=self.window_tag,
        ):
            self.frame_tag = dpg.add_child_window(width=-1, height=-1, border=False)
            self._frame_theme = frame_theme()
            dpg.bind_item_theme(self.frame_tag, self._frame_theme)
            self.header = PaneHeader(
                self.frame_tag,
                self.width - 16,
                title="Log",
                flat=True,
                title_font=self._large_font,
                title_size=FONT_SIZE,
            )
            self.level_card = ChoiceCard(
                self.frame_tag,
                self.width - 16,
                label="Level",
                options=[(name, name.capitalize()) for name in LEVELS],
                value=level,
                on_change=self.set_level,
                background=LEVEL_BACKGROUND,
                option_width=68,
            )
            with dpg.theme() as self._log_theme:
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_style(
                        dpg.mvStyleVar_CellPadding,
                        CHAR_WIDTH,
                        LINE_GAP,
                        category=dpg.mvThemeCat_Core,
                    )
                    dpg.add_theme_style(
                        dpg.mvStyleVar_ItemSpacing, 0, 0, category=dpg.mvThemeCat_Core
                    )
                    # A line is as tall as its text and no more: the padding of a frame
                    # is added to a line of text in a table, top and bottom.
                    dpg.add_theme_style(
                        dpg.mvStyleVar_FramePadding, 0, 0, category=dpg.mvThemeCat_Core
                    )
                    dpg.add_theme_style(
                        dpg.mvStyleVar_WindowPadding, 4, 4, category=dpg.mvThemeCat_Core
                    )
                with dpg.theme_component(dpg.mvChildWindow):
                    dpg.add_theme_color(
                        dpg.mvThemeCol_ChildBg, LOG_BACKGROUND, category=dpg.mvThemeCat_Core
                    )
                    dpg.add_theme_color(
                        dpg.mvThemeCol_Border, (0, 0, 0, 0), category=dpg.mvThemeCat_Core
                    )
            self.log_area = dpg.add_child_window(
                tag=self.log_tag,
                parent=self.frame_tag,
                width=-1,
                height=-1,
                border=True,
            )
            dpg.bind_item_theme(self.log_area, self._log_theme)
            # A table, so that the lines are as close as their text is tall: the time and
            # tag in one column, and the message in the other.
            self.table_tag = dpg.add_table(
                parent=self.log_area,
                header_row=False,
                policy=dpg.mvTable_SizingFixedFit,
                borders_innerH=False,
                borders_innerV=False,
                borders_outerH=False,
                borders_outerV=False,
                pad_outerX=False,
            )
            dpg.add_table_column(
                parent=self.table_tag,
                width_fixed=True,
                init_width_or_weight=PREFIX_CHARS * CHAR_WIDTH + CHAR_WIDTH,
            )
            dpg.add_table_column(parent=self.table_tag, width_fixed=True)
            dpg.bind_item_theme(self.table_tag, self._log_theme)  # for the space of its cells

        self.update_layout()
        self._badge = "unset"
        self._update_badge()

    # --- the window ---

    def update_layout(self) -> None:
        """
        Keep the window in the left part of the viewport, beside the menu, and as tall
        as it. If that changes its width the messages are drawn again to fit it.
        """
        viewport_width = dpg.get_viewport_client_width()
        viewport_height = dpg.get_viewport_client_height()
        width = max(page_width(viewport_width), self.MINIMUM_WIDTH)
        dpg.configure_item(
            self.window_tag,
            pos=[PANE_X, TOP_Y],
            width=width,
            height=max(viewport_height - TOP_Y - 20, 100),
        )
        if width != self.width:
            self.width = width
            self.header.resize(width - 16)
            self.level_card.resize(width - 16)
            self._redraw()

    def tick(self) -> None:
        """
        Call this often, such as once a frame: keep the latest message in view if it was
        when the last one arrived, and note whether the messages have been scrolled up.
        """
        area = self.log_area
        top, bottom = dpg.get_y_scroll(area), dpg.get_y_scroll_max(area)
        if self._stick:
            if top < bottom:
                dpg.set_y_scroll(area, bottom)
        else:
            self._stick = bottom - top <= STICK_WITHIN

    # --- the level ---

    def set_level(self, level: str) -> None:
        """
        Show the messages of a level and above, and draw the messages that are kept again
        for it. Nothing is lost by choosing a higher level: the lower ones are shown
        again when a lower one is chosen.

        Args:
            level (str): One of `LEVELS`.

        Raises:
            ValueError: If it is not one of them.
        """
        if level not in LEVELS:
            raise ValueError(f"level must be one of {', '.join(LEVELS)}, got {level!r}")
        self.level = level
        self.level_card.set_value(level)
        self._redraw()
        self._stick = True
        self.hidden = sum(1 for entry in self.entries if not self._shown(entry["level"]))
        self._update_badge()

    def _redraw(self) -> None:
        """Draw the messages that are shown again, in the order they came."""
        dpg.delete_item(self.table_tag, children_only=True, slot=1)  # keep its columns
        for entry in self.entries:
            entry["row"] = None
            if self._shown(entry["level"]):
                self._draw(entry)

    def _shown(self, level: str) -> bool:
        """Whether a message of a level is shown, at the level that is chosen."""
        return rank(level) >= RANKS[self.level]

    def _update_badge(self) -> None:
        """Say in the header how many messages the level is leaving out, if any."""
        badge = f"{self.hidden} HIDDEN" if self.hidden else None
        if badge != self._badge:
            self._badge = badge
            self.header.update(title="Log", badge=badge, style="idle")

    # --- the messages ---

    def add_log(self, log: dict) -> None:
        """
        Add a message to the log. It is kept, and it is shown if its level is.

        Args:
            log (dict): Its `time`, `level` and `message`.
        """
        entry = {
            "time": log["time"],
            "level": log["level"],
            "message": str(log["message"]),
            "row": None,
        }
        if len(self.entries) >= MAX_LOGS:
            oldest = self.entries.popleft()
            if oldest["row"] is not None:
                dpg.delete_item(oldest["row"])
            elif not self._shown(oldest["level"]):
                self.hidden -= 1
        self.entries.append(entry)
        if self._shown(entry["level"]):
            self._draw(entry)
        else:
            self.hidden += 1
        self._update_badge()

    def _draw(self, entry: dict) -> None:
        """
        Add the line for a message: its time and level tag, and its message, on a single
        line. A message that is too long is cut short, and shown in full when the mouse
        is over it.
        """
        level = entry["level"]
        stamp = datetime.fromtimestamp(entry["time"]).strftime("%H:%M:%S")
        tag = TAGS.get(level, level[:3].upper())
        room = self.width - 16 - 8 - SCROLL_BAR - 3 * CHAR_WIDTH
        room -= (PREFIX_CHARS + 1) * CHAR_WIDTH
        message = " ".join(entry["message"].split())  # one line, however it was written
        shown = fit(message, room)
        with dpg.table_row(parent=self.table_tag) as row:
            dpg.add_text(f"{stamp} {tag}", color=COLORS.get(level, COLORS["info"]))
            text = dpg.add_text(shown, color=MESSAGE_COLORS.get(level, WHITE))
            if shown != message:
                with dpg.tooltip(text):
                    dpg.add_text(entry["message"], color=TEXT_COLOR, wrap=520)
        entry["row"] = row
