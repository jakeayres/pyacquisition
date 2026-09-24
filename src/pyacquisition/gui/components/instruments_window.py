import dearpygui.dearpygui as dpg

from ..constants import (
    PANE_X,
    TOP_Y,
    VALUE_COLORS,
    WHITE,
    page_width,
)
from .fonts import add_font
from .header import TEXT_HEIGHT, PaneHeader
from .measurement_card import MeasurementCard
from .pane import frame_theme

FONT_SIZE = 20  # the title of the header, as in the other panes
ENDPOINT_INDENT = 4  # spaces before the name of an endpoint
ENDPOINT_HEIGHT = 24
MINIMUM_WIDTH = 360


class InstrumentsWindow:
    """
    The Instruments page: a header, and a card for each instrument, with its name in
    white and, under it, what it is in grey. At the right of the card is how many
    endpoints it has. Clicking a card opens its list, under it: each of its queries and
    commands is a line, and clicking one calls `on_pick` with it, which opens the window
    that asks for its inputs and sends the request. Clicking the card again closes the list.

    It fills the left part of the window, beside the menu, and is as tall as it.
    """

    def __init__(self, on_pick=None):
        """
        Args:
            on_pick: Called with the name of an instrument and the endpoint that was
                picked from its list.
        """
        self.on_pick = on_pick
        self.width = MINIMUM_WIDTH + 200  # until it is laid out
        self.cards = {}  # the card of each instrument, by its name
        self.lists = {}  # the group that holds the endpoints of each, by its name
        self.open = set()  # the instruments whose lists are open
        self.window_tag = dpg.generate_uuid()
        self._large_font = add_font(FONT_SIZE)

        with dpg.window(
            label="Instruments",
            pos=[PANE_X, TOP_Y],
            width=self.width,
            height=600,
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
                self.width - 16,
                title="Instruments",
                flat=True,
                title_font=self._large_font,
                title_size=FONT_SIZE,
            )
            self.body_tag = dpg.add_child_window(
                parent=self.frame_tag, width=-1, auto_resize_y=True, border=False
            )
            self.empty_tag = dpg.add_text(
                "No instruments", color=(130, 130, 130), parent=self.body_tag, indent=16
            )

    def set_instruments(self, instruments: dict, endpoints: dict) -> None:
        """
        Show the instruments, instead of any that were shown.

        Args:
            instruments (dict): What each is, by its name.
            endpoints (dict): The endpoints of each, as the paths of the API, by its
                name. An instrument with none is still shown.
        """
        dpg.delete_item(self.body_tag, children_only=True)
        self.cards, self.lists, self.open = {}, {}, set()
        self.empty_tag = None
        if not instruments:
            self.empty_tag = dpg.add_text(
                "No instruments", color=(130, 130, 130), parent=self.body_tag, indent=16
            )
            return

        for index, (name, kind) in enumerate(instruments.items()):
            paths = endpoints.get(name, [])
            card = MeasurementCard(
                self.body_tag,
                self.header.width,
                name=name,
                source=str(kind),
                color=VALUE_COLORS[index % len(VALUE_COLORS)],
                value_color=WHITE,
                value_size=TEXT_HEIGHT,
                on_click=lambda name=name: self.toggle(name),
            )
            card.set_value(f"{len(paths)} endpoint{'' if len(paths) == 1 else 's'}")
            self.cards[name] = card
            with dpg.group(parent=self.body_tag, show=False) as group:
                for path in paths:
                    dpg.add_selectable(
                        label=" " * ENDPOINT_INDENT + str(path.get.summary),
                        height=ENDPOINT_HEIGHT,
                        callback=self._picked,
                        user_data=(name, path),
                    )
            self.lists[name] = group

    def toggle(self, name: str) -> None:
        """Open the list of an instrument, or close it if it is open."""
        if name not in self.lists:
            return
        if name in self.open:
            self.open.discard(name)
        else:
            self.open.add(name)
        dpg.configure_item(self.lists[name], show=name in self.open)

    def _picked(self, sender=None, app_data=None, user_data=None) -> None:
        """An endpoint was picked from a list."""
        dpg.set_value(sender, False)  # it does something, and is not a choice
        if self.on_pick:
            name, path = user_data
            self.on_pick(name, path)

    def update_layout(self) -> None:
        """
        Keep the window in the left part of the viewport, beside the menu, and as tall
        as it, with the header and the cards as wide as it.
        """
        viewport_width = dpg.get_viewport_client_width()
        viewport_height = dpg.get_viewport_client_height()
        width = max(page_width(viewport_width), MINIMUM_WIDTH)
        dpg.configure_item(
            self.window_tag,
            pos=[PANE_X, TOP_Y],
            width=width,
            height=max(viewport_height - TOP_Y - 20, 100),
        )
        self.header.fit_to(self.window_tag)
        for card in self.cards.values():
            if card.width != self.header.width:
                card.resize(self.header.width)
        self.width = width
