import dearpygui.dearpygui as dpg

from .control_card import CONTROL_HEIGHT, ControlCard
from .measurement_card import RIGHT
from .styles import primary_button_theme

OPTION_WIDTH = 58
GAP = 2  # between one option and the next


def _plain_button_theme():
    """The look of an option that is not the chosen one: grey, and quiet."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            for column, colour in (
                (dpg.mvThemeCol_Button, (40, 44, 54)),
                (dpg.mvThemeCol_ButtonHovered, (58, 64, 80)),
                (dpg.mvThemeCol_ButtonActive, (74, 82, 102)),
                (dpg.mvThemeCol_Text, (185, 190, 200)),
            ):
                dpg.add_theme_color(column, colour, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(
                dpg.mvStyleVar_FrameRounding, 3, category=dpg.mvThemeCat_Core
            )
    return theme


class ChoiceCard(ControlCard):
    """
    A card with a label and a row of options, one of which is chosen, like the levels of
    a log: the chosen one is blue and the others grey. It is drawn like an input card, a
    tinted strip with the label in white and no bar at its left.

    It is generic: what it is for is up to whoever makes it. Clicking an option chooses
    it and calls `on_change` with its value, and `value` says which is chosen at any time.
    """

    def __init__(
        self,
        parent,
        width: int,
        label: str,
        options,
        value=None,
        on_change=None,
        caption: str = "",
        background=None,
        height: int = 30,
        option_width: int = OPTION_WIDTH,
    ) -> None:
        """
        Args:
            parent: The item to put the card in.
            width (int): The width of the card in pixels.
            label (str): What is being chosen, such as `Level`.
            options: What can be chosen, as values, or as `(value, text)` pairs when the
                text on the button is not the value.
            value: The one that is chosen to start with. The first if not given.
            on_change: Called with the value of an option, when it is clicked.
            caption (str): Small grey text under the label.
            background: The colour of the strip, or `None` for the header's own.
            height (int): The height of the card in pixels.
            option_width (int): The width of each option in pixels.

        Raises:
            ValueError: If there are no options, or the value is not one of them.
        """
        pairs = [o if isinstance(o, tuple) else (o, str(o)) for o in options]
        if not pairs:
            raise ValueError("a choice needs at least one option")
        values = [v for v, _ in pairs]
        if value is not None and value not in values:
            raise ValueError(f"value must be one of {values}, got {value!r}")
        super().__init__(
            parent,
            width,
            label,
            caption=caption,
            background=background,
            height=height,
            controls_width=len(pairs) * option_width + (len(pairs) - 1) * GAP,
        )
        self.on_change = on_change
        self.option_width = option_width
        self.options = values
        self._chosen = value if value is not None else values[0]
        self._chosen_theme = primary_button_theme()
        self._plain_theme = _plain_button_theme()
        self.option_tags = {}
        for option, text in pairs:
            self.option_tags[option] = dpg.add_button(
                label=text,
                width=option_width,
                height=CONTROL_HEIGHT,
                callback=self._clicked,
                user_data=option,
                parent=self.container,
            )
        self._show()
        self._layout()

    @property
    def value(self):
        """The option that is chosen."""
        return self._chosen

    def set_value(self, value) -> None:
        """
        Choose an option, without calling `on_change`.

        Raises:
            ValueError: If it is not one of the options.
        """
        if value not in self.options:
            raise ValueError(f"value must be one of {self.options}, got {value!r}")
        self._chosen = value
        self._show()

    def _show(self) -> None:
        """Colour the chosen option blue, and the others grey."""
        for option, tag in self.option_tags.items():
            theme = self._chosen_theme if option == self._chosen else self._plain_theme
            dpg.bind_item_theme(tag, theme)

    def _clicked(self, sender=None, app_data=None, user_data=None) -> None:
        """An option was clicked: choose it, and say so."""
        self._chosen = user_data
        self._show()
        if self.on_change:
            self.on_change(user_data)

    def _place_controls(self) -> None:
        """Put the options in a row at the right."""
        top = (self.height - CONTROL_HEIGHT) // 2
        x = self.width - RIGHT - self.controls_width
        for tag in self.option_tags.values():
            dpg.set_item_pos(tag, (x, top))
            x += self.option_width + GAP
