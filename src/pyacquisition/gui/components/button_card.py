import dearpygui.dearpygui as dpg

from .control_card import CONTROL_HEIGHT, ControlCard
from .styles import primary_button_theme

HEIGHT = 44  # the height of a card of this kind
MARGIN = 10  # between the button and the edges of the card


class ButtonCard(ControlCard):
    """
    A card that is only a button: a tinted strip with no bar at its left, and a button
    that fills it, with a margin around it. The label is the text of the button.

    It is generic: what it is for is up to whoever makes it, and `on_click` is called,
    with no arguments, each time it is pressed. It reads nothing itself, so whatever it
    acts on is read by the callback, at the moment of the click.
    """

    def __init__(
        self,
        parent,
        width: int,
        label: str,
        on_click=None,
        background=None,
        height: int = HEIGHT,
        enabled: bool = True,
    ) -> None:
        """
        Args:
            parent: The item to put the card in.
            width (int): The width of the card in pixels.
            label (str): What the button says.
            on_click: Called, with no arguments, when the button is pressed.
            background: The colour of the strip, or `None` for the header's own.
            height (int): The height of the card in pixels.
            enabled (bool): Whether the button can be pressed.
        """
        # There is no label or caption of its own: the text is the button's.
        super().__init__(parent, width, "", background=background, height=height)
        self.button_label = label
        self.on_click = on_click
        self.button_tag = dpg.add_button(
            label=label,
            width=width - 2 * MARGIN,
            height=CONTROL_HEIGHT,
            callback=self._clicked,
            enabled=enabled,
            parent=self.container,
        )
        dpg.bind_item_theme(self.button_tag, primary_button_theme())
        self._layout()

    def set_enabled(self, enabled: bool) -> None:
        """Let the button be pressed, or not."""
        dpg.configure_item(self.button_tag, enabled=enabled)

    def _clicked(self, sender=None, app_data=None, user_data=None) -> None:
        """The button was pressed."""
        if self.on_click:
            self.on_click()

    def _place_controls(self) -> None:
        """Make the button fill the card, less its margin, and put it in the middle."""
        dpg.configure_item(self.button_tag, width=max(self.width - 2 * MARGIN, 20))
        dpg.set_item_pos(
            self.button_tag, (MARGIN, (self.height - CONTROL_HEIGHT) // 2)
        )
