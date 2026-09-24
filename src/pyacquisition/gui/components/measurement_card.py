import dearpygui.dearpygui as dpg

from ..constants import MUTED_COLOR, STATE_STYLES, WHITE
from .header import CHAR_WIDTH, TEXT_HEIGHT, fit

MUTED_GREY = 95  # what a colour is drawn towards when it is muted
HEIGHT = 44  # the height of a header that has a caption
ACCENT_WIDTH = 5
LEFT = 16  # where the text starts, as in a header
RIGHT = 10  # the space at the right of the value
VALUE_ROOM = 130  # what the labels leave for the value, which is short
# The pixel font has more space above its letters than below them, so the ink of a line
# sits this far below the middle of its box. Text is placed this much higher, so that
# what is seen is level with the middle of the card.
INK_DROP = 3
# Two lines, the name and under it what it is, have descenders below the second, so the
# pair is a pixel higher again.
PRIMARY_Y, SECONDARY_Y = 6 - INK_DROP, 23 - INK_DROP


def single_line_y(height: int) -> int:
    """Where one line of text goes, so that it looks to be in the middle of a card."""
    return (height - TEXT_HEIGHT) // 2 - INK_DROP


def muted(color, amount: float = 0.75):
    """
    A colour drawn towards grey, for a measurement that is not running.

    Args:
        color: The colour, as three or four numbers from 0 to 255.
        amount (float): How far towards grey, from 0, the colour itself, to 1, grey.
    """
    return tuple(
        round(c * (1 - amount) + MUTED_GREY * amount) for c in tuple(color)[:3]
    )


class MeasurementCard:
    """
    One measurement, drawn like the header of the data file pane: a tinted strip with
    a bar at its left, in the colour of the measurement. (Something that is not a
    measurement, such as the loop time, has a darker strip and no bar.) At the left are two lines of
    text, the name in white and, under it, where it comes from in grey, and at the
    right is the latest value, in larger text and in the colour of the measurement.
    """

    def __init__(
        self,
        parent,
        width: int,
        name: str,
        color,
        source: str = "",
        font=None,
        value_size: int = 20,
        background=None,
        name_color=WHITE,
        bar: bool = True,
        height: int = HEIGHT,
        value_room: int = VALUE_ROOM,
        value_color=None,
        on_click=None,
    ) -> None:
        """
        Args:
            parent: The item to put the card in.
            width (int): The width of the card in pixels.
            name (str): The name of the measurement, as the user gave it.
            color: The colour of the bar and of the value.
            source (str): Where it comes from, such as `cryo.get_temperature`. The
                card has a single line if it is empty.
            font: The font of the value, or `None` for the default font.
            value_size (int): The height of the value's text, for placing it when the
                size of the text cannot be measured.
            background: The colour of the strip, or `None` for the header's own.
            name_color: The colour of the name.
            bar (bool): Whether there is a bar at the left, in `color`, as in a header.
            height (int): The height of the card in pixels.
            on_click: If given, the card is a button: this is called, with no arguments,
                when it is clicked.
            value_color: The colour of the value, or `None` for the colour of the bar.
            value_room (int): The width that the texts at the left leave for the value.
                A card with no value can leave none, and give them all the width.
        """
        self.width = width
        self.height = height
        self.value_room = value_room
        self.name = name
        self.source = source
        self.font = font
        self.value_size = value_size
        self.text = ""
        self.color = color
        self.value_color = value_color or color
        self.name_color = name_color
        self.muted = False

        with dpg.theme() as no_padding:
            with dpg.theme_component(dpg.mvChildWindow):
                dpg.add_theme_style(
                    dpg.mvStyleVar_WindowPadding, 0, 0, category=dpg.mvThemeCat_Core
                )
        self.container = dpg.add_child_window(
            parent=parent, width=width, height=self.height, border=False, no_scrollbar=True
        )
        dpg.bind_item_theme(self.container, no_padding)

        tint = background or STATE_STYLES["neutral"]["background"]
        self.drawlist = dpg.add_drawlist(
            width=width, height=self.height, parent=self.container
        )
        self._background = dpg.draw_rectangle(
            (0, 0), (width, self.height), color=tint, fill=tint, parent=self.drawlist
        )
        self._bar = None
        if bar:
            self._bar = dpg.draw_rectangle(
                (0, 0),
                (ACCENT_WIDTH, self.height),
                color=color,
                fill=color,
                parent=self.drawlist,
            )

        # The text is in items on top of the drawing, so that it can be read back.
        self.name_tag = dpg.add_text("", color=name_color, parent=self.container)
        self.source_tag = dpg.add_text(
            source, color=MUTED_COLOR, parent=self.container, show=bool(source)
        )
        self.value_tag = dpg.add_text("", color=self.value_color, parent=self.container)
        if font is not None:
            dpg.bind_item_font(self.value_tag, font)
        self._handlers = None
        if on_click is not None:
            self.on_click = on_click
            with dpg.item_handler_registry() as self._handlers:
                dpg.add_item_clicked_handler(
                    button=dpg.mvMouseButton_Left, callback=lambda *args: on_click()
                )
            dpg.bind_item_handler_registry(self.drawlist, self._handlers)
        self._layout()

    def set_muted(self, muted_now: bool) -> None:
        """
        Draw the card in muted colours, so that it is clear that its value is not
        being updated, or in its own colours again.

        Args:
            muted_now (bool): Whether to mute it.
        """
        self.muted = muted_now
        color = muted(self.color) if muted_now else self.color
        value = muted(self.value_color) if muted_now else self.value_color
        name = muted(self.name_color) if muted_now else self.name_color
        dpg.configure_item(self.value_tag, color=value)
        dpg.configure_item(self.name_tag, color=name)
        if self._bar is not None:
            dpg.configure_item(self._bar, color=color, fill=color)

    def set_source(self, text: str) -> None:
        """Show other grey text under the name, or none if it is empty."""
        self.source = text
        dpg.configure_item(self.source_tag, show=bool(text))
        self._layout()

    def set_value(self, text: str) -> None:
        """Show a new value, at the right."""
        self.text = text
        dpg.set_value(self.value_tag, text)
        self._place_value()

    def resize(self, width: int) -> None:
        """Make the card a different width, for example when a scroll bar appears."""
        self.width = width
        dpg.configure_item(self.container, width=width)
        dpg.configure_item(self.drawlist, width=width)
        dpg.configure_item(self._background, pmax=(width, self.height))
        self._layout()

    def _layout(self) -> None:
        """Place the texts, for the current width."""
        room = max(self.width - LEFT - RIGHT - self.value_room, 60)
        middle = single_line_y(self.height)
        dpg.set_value(self.name_tag, fit(self.name, room))
        dpg.set_item_pos(self.name_tag, (LEFT, PRIMARY_Y if self.source else middle))
        dpg.set_value(self.source_tag, fit(self.source, room))
        dpg.set_item_pos(self.source_tag, (LEFT, SECONDARY_Y))
        self._place_value()

    def _place_value(self) -> None:
        """Put the value at the right, level with the middle of the card."""
        size = dpg.get_text_size(self.text, font=self.font or 0) if self.text else None
        if size:
            w, h = size
        else:  # the text cannot be measured before it is shown
            per_character = CHAR_WIDTH if self.font is None else self.value_size * 0.6
            w, h = round(per_character * len(self.text)), self.value_size
        # The ink of the pixel font sits lower in its box than that of the large font.
        drop = INK_DROP if self.font is None else 1
        dpg.set_item_pos(
            self.value_tag,
            (max(self.width - RIGHT - w, LEFT), (self.height - h) // 2 - drop),
        )
