import re

import dearpygui.dearpygui as dpg

from ..constants import (
    FILE_PANE_HEIGHT,
    DEFAULT_PAGE_WIDTH,
    PANE_X,
    SECONDARY_COLOR,
    STATE_STYLES,
    TOP_Y,
    WHITE,
)
from .button_card import ButtonCard
from .checkbox_card import CheckboxCard
from .fonts import add_font
from .header import CHAR_WIDTH, TEXT_HEIGHT, PaneHeader, fit_start
from .input_card import InputCard
from .measurement_card import LEFT, RIGHT, MeasurementCard
from .pane import add_rule, color_rules, fit_rules, fit_to_page, frame_theme

WINDOW_WIDTH = DEFAULT_PAGE_WIDTH  # until it is laid out
HEADER_WIDTH = WINDOW_WIDTH - 16  # the width of the window, less its padding
FONT_SIZE = 20  # the title of the header, as in Live Data
INPUT_BACKGROUND = (16, 18, 22)  # darker than a card that shows something
INPUT_BOX_WIDTH = 170
VALUE_LABEL_WIDTH = 14 * CHAR_WIDTH  # what the name of a card takes from the file name
CHECKBOX_HEIGHT = 30  # a card with only a label and a box

# A file is `block.step title.extension`, such as `05.01 sweep.data`.
FILE_NAME = re.compile(
    r"^(?P<block>\d+)\.(?P<step>\d+) (?P<title>.*?)(?:\.(?P<extension>[^.]*))?$"
)


def split_file_name(name: str):
    """
    A file name as its block, step, title and extension, or `None` if it is not one
    that the scribe made.

    Args:
        name (str): The name, such as `05.01 sweep.data`.
    """
    match = FILE_NAME.match(name)
    if not match:
        return None
    return match["block"], match["step"], match["title"], match["extension"] or ""


def next_file_name(current: str, title: str, next_block: bool = False) -> str:
    """
    The name of the file that the next file button starts: the step after the current
    one, or step 00 of the next block, and the title that was typed. The extension is
    the current file's.

    Args:
        current (str): The name of the current file.
        title (str): The title that was typed.
        next_block (bool): Whether it starts a new block, and not the next step.

    Returns:
        str: The name, or the title alone if there is no current file to follow.
    """
    parts = split_file_name(current)
    if parts is None:
        return title
    block, step, _, extension = parts
    if next_block:
        name = f"{int(block) + 1:0{max(len(block), 2)}d}.00 {title}"
    else:
        name = f"{block}.{int(step) + 1:0{len(step)}d} {title}"
    return f"{name}.{extension}" if extension else name


class FileWindow:
    """
    The pane that shows the file that data is being saved to, and its folder, and starts
    the next file.

    It is drawn like the Live Data window: a header with a one pixel underline and
    cards under it. The current file, the name that the next file would get, and the
    directory are cards with a blue bar. Under them, in darker cards with no bar, are an
    input for the name of the next file, a checkbox that makes it start a new block, and
    a card that is only a button, which starts it. The name of the next file follows
    what is typed.
    """

    def __init__(self, on_next_file=None):
        """
        Args:
            on_next_file: Called with the title that was typed, and whether to start a
                new block, when the next file button is pressed. Without it there are
                no controls.
        """
        self.window_tag = dpg.generate_uuid()
        self.on_next_file = on_next_file
        self.current_file = ""
        self.directory = ""
        self._rules = []
        self._titled = False  # whether the input has been given a title to start with
        # The font for large text. It is loaded here, because a font can only be added
        # before the window is first shown.
        self._large_font = add_font(FONT_SIZE)

        with dpg.window(
            label="Current File",
            width=WINDOW_WIDTH,
            height=FILE_PANE_HEIGHT + 24,  # and the padding of the window
            no_scrollbar=True,
            pos=[PANE_X, TOP_Y],
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
            self.frame_tag = dpg.add_child_window(
                width=-1, auto_resize_y=True, border=False
            )
            self._frame_theme = frame_theme()
            dpg.bind_item_theme(self.frame_tag, self._frame_theme)
            self.header = PaneHeader(
                self.frame_tag,
                HEADER_WIDTH,
                title="Data File",
                flat=True,
                title_font=self._large_font,
                title_size=FONT_SIZE,
            )
            self.card_tag = dpg.add_child_window(
                parent=self.frame_tag, width=-1, auto_resize_y=True, border=False
            )

            self.file_card = MeasurementCard(
                self.card_tag,
                HEADER_WIDTH,
                name="Current File",
                color=STATE_STYLES["neutral"]["border"],
                value_color=WHITE,
                value_size=TEXT_HEIGHT,
            )
            self.next_file_card = None
            if on_next_file:
                self.next_file_card = MeasurementCard(
                    self.card_tag,
                    HEADER_WIDTH,
                    name="Next File",
                    color=STATE_STYLES["neutral"]["border"],
                    value_color=WHITE,
                    value_size=TEXT_HEIGHT,
                )
            self.directory_card = MeasurementCard(
                self.card_tag,
                HEADER_WIDTH,
                name="Directory",
                color=SECONDARY_COLOR,
                value_room=0,  # there is no value, so the path has all the width
            )
            self.directory_uuid = self.directory_card.source_tag

            self.next_card = None
            self.block_card = None
            self.start_card = None
            if on_next_file:
                add_rule(self.card_tag, HEADER_WIDTH, self._rules)
                self.next_card = InputCard(
                    self.card_tag,
                    HEADER_WIDTH,
                    label="Next File Name",
                    value="",
                    kind="text",
                    on_change=lambda title: self._show_next_name(),
                    button_label=None,  # the button is a card of its own
                    background=INPUT_BACKGROUND,
                    input_width=INPUT_BOX_WIDTH,
                )
                self.block_card = CheckboxCard(
                    self.card_tag,
                    HEADER_WIDTH,
                    label="Increment Block",
                    on_change=lambda ticked: self._show_next_name(),
                    background=INPUT_BACKGROUND,
                    height=CHECKBOX_HEIGHT,
                )
                self.start_card = ButtonCard(
                    self.card_tag,
                    HEADER_WIDTH,
                    label="Next File",
                    on_click=self._start_next_file,
                    background=INPUT_BACKGROUND,
                )
                add_rule(self.card_tag, HEADER_WIDTH, self._rules)
            color_rules(self._rules, STATE_STYLES["idle"]["border"])
            self._show_file("")
            self._show_next_name()

    # --- what it shows ---

    def update_file(self, file_path: str) -> None:
        """
        Show the current file, and the name that the next one would get. The input for
        the next file is given the current file's title if nothing has been typed in it.

        Args:
            file_path (str): The name of the current datafile.
        """
        self.current_file = file_path
        self._show_file(file_path)
        parts = split_file_name(file_path)
        if self.next_card is not None and parts and not self._titled:
            self.next_card.set_value(parts[2])
            self._titled = True
        self._show_next_name()

    def update_directory(self, directory_path: str) -> None:
        """
        Show the current directory, which is cut short at its start if it is long, so
        that the folder that matters is still shown.

        Args:
            directory_path (str): The path of the current directory.
        """
        self.directory = directory_path
        room = self.directory_card.width - LEFT - RIGHT
        self.directory_card.set_source(fit_start(directory_path, room))

    def _show_file(self, name: str) -> None:
        """Show the name of the current file at the right of its card."""
        self.file_card.set_value(self._fit_name(name or "-", self.file_card))

    def _fit_name(self, name: str, card: MeasurementCard) -> str:
        """A file name, cut short with `...` if the card has no room for all of it."""
        room = card.width - LEFT - RIGHT - VALUE_LABEL_WIDTH
        characters = max(room // CHAR_WIDTH, 4)
        return name if len(name) <= characters else name[: characters - 3] + "..."

    def _show_next_name(self) -> None:
        """Show the name that the next file would get, in the card for it."""
        if self.next_card is None:
            return
        title = self.next_card.value.strip()
        if not title:
            self.next_file_card.set_value("-")
            return
        name = next_file_name(self.current_file, title, self.block_card.value)
        self.next_file_card.set_value(self._fit_name(name, self.next_file_card))

    def _start_next_file(self) -> None:
        """
        The next file button was pressed: start the file with the title that is typed, in
        a new block if that is ticked. Nothing is started without a title. The box is
        unticked afterwards, because starting a new block is not something that is
        meant to happen with every file.
        """
        title = self.next_card.value.strip()
        if not title:
            return
        next_block = self.block_card.value
        self.block_card.set_value(False)
        self._show_next_name()
        self.on_next_file(title, next_block)

    def fit(self) -> None:
        """
        Keep the window as wide as a page, and the header, the cards and the lines as wide
        as it.
        """
        fit_to_page(self.window_tag)
        self.header.fit_to(self.window_tag)
        width = self.header.width
        cards = (
            self.file_card,
            self.next_file_card,
            self.directory_card,
            self.next_card,
            self.block_card,
            self.start_card,
        )
        for card in filter(None, cards):
            if card.width != width:
                card.resize(width)
        fit_rules(self._rules, width)
        self._show_file(self.current_file)
        self._show_next_name()
        self.update_directory(self.directory)
