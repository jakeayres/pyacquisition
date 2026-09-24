import dearpygui.dearpygui as dpg

from .control_card import CONTROL_HEIGHT, ControlCard
from .measurement_card import HEIGHT, RIGHT

CHECKBOX_WIDTH = CONTROL_HEIGHT  # the box is as wide as it is tall


class CheckboxCard(ControlCard):
    """
    A card with a label and a checkbox, drawn like an input card: a tinted strip with
    the label in white and, under it, a caption in grey if there is one, and no bar at
    its left. The checkbox is at the right.

    It is generic: what it is for is up to whoever makes it. A checkbox does not need a
    button to send it, so `on_change` is called each time it is ticked or unticked, with
    whether it is ticked, and `value` says what it is at any time.
    """

    def __init__(
        self,
        parent,
        width: int,
        label: str,
        value: bool = False,
        on_change=None,
        caption: str = "",
        background=None,
        height: int = HEIGHT,
    ) -> None:
        """
        Args:
            parent: The item to put the card in.
            width (int): The width of the card in pixels.
            label (str): What ticking the box does, such as `Start a new block`.
            value (bool): Whether it starts ticked.
            on_change: Called with whether it is ticked, each time it is clicked.
            caption (str): Small grey text under the label. The card has a single line
                if it is empty.
            background: The colour of the strip, or `None` for the header's own.
            height (int): The height of the card in pixels.
        """
        super().__init__(
            parent,
            width,
            label,
            caption=caption,
            background=background,
            height=height,
            controls_width=CHECKBOX_WIDTH,
        )
        self.on_change = on_change
        self.checkbox_tag = dpg.add_checkbox(
            default_value=bool(value), callback=self._changed, parent=self.container
        )
        self._layout()

    @property
    def value(self) -> bool:
        """Whether the box is ticked."""
        return bool(dpg.get_value(self.checkbox_tag))

    def set_value(self, value: bool) -> None:
        """Tick or untick the box, without calling `on_change`."""
        dpg.set_value(self.checkbox_tag, bool(value))

    def _changed(self, sender=None, app_data=None, user_data=None) -> None:
        """The box was clicked."""
        if self.on_change:
            self.on_change(self.value)

    def _place_controls(self) -> None:
        """Place the checkbox at the right, in the middle of the card."""
        top = (self.height - CONTROL_HEIGHT) // 2
        dpg.set_item_pos(
            self.checkbox_tag, (self.width - RIGHT - CHECKBOX_WIDTH, top)
        )
