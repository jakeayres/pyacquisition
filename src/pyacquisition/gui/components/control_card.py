import dearpygui.dearpygui as dpg

from ..constants import MUTED_COLOR, STATE_STYLES, WHITE
from .header import TEXT_HEIGHT, fit
from .measurement_card import (
    HEIGHT,
    LEFT,
    PRIMARY_Y,
    RIGHT,
    SECONDARY_Y,
    single_line_y,
)

CONTROL_HEIGHT = 26  # the height of an input, a button or a checkbox in a card
# The texts of a card with controls sit lower than those of a measurement card, for the
# same position, because of the padding of the controls beside them.
TEXT_LIFT = 3


class ControlCard:
    """
    The card that the cards with controls are made from: a tinted strip with the label
    in white and, under it, a caption in grey if there is one. It has no bar at its
    left, which sets it apart from a measurement. The controls are at the right, and
    the subclass adds them and places them.

    Nothing is drawn in it, because a drawing takes the mouse from whatever is over it,
    so that a control on it could never be clicked. The tint is the fill of the card.
    """

    def __init__(
        self,
        parent,
        width: int,
        label: str,
        caption: str = "",
        background=None,
        height: int = HEIGHT,
        controls_width: int = 0,
    ) -> None:
        """
        Args:
            parent: The item to put the card in.
            width (int): The width of the card in pixels.
            label (str): What the card is for.
            caption (str): Small grey text under the label. The card has a single line
                if it is empty.
            background: The colour of the strip, or `None` for the header's own.
            height (int): The height of the card in pixels.
            controls_width (int): How much of the width the controls take, at the right.
        """
        self.width = width
        self.height = height
        self.label = label
        self.caption = caption
        self.controls_width = controls_width

        tint = background or STATE_STYLES["neutral"]["background"]
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvChildWindow):
                dpg.add_theme_style(
                    dpg.mvStyleVar_WindowPadding, 0, 0, category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_color(
                    dpg.mvThemeCol_ChildBg, tint, category=dpg.mvThemeCat_Core
                )
            with dpg.theme_component(dpg.mvAll):
                # So that an input is as tall as a button beside it.
                dpg.add_theme_style(
                    dpg.mvStyleVar_FramePadding,
                    6,
                    (CONTROL_HEIGHT - TEXT_HEIGHT) / 2,
                    category=dpg.mvThemeCat_Core,
                )
                dpg.add_theme_style(
                    dpg.mvStyleVar_FrameRounding, 3, category=dpg.mvThemeCat_Core
                )
        self.container = dpg.add_child_window(
            parent=parent, width=width, height=height, border=False, no_scrollbar=True
        )
        dpg.bind_item_theme(self.container, theme)

        self.label_tag = dpg.add_text("", color=WHITE, parent=self.container)
        self.caption_tag = dpg.add_text(
            caption, color=MUTED_COLOR, parent=self.container, show=bool(caption)
        )

    def resize(self, width: int) -> None:
        """Make the card a different width, for example when a scroll bar appears."""
        self.width = width
        dpg.configure_item(self.container, width=width)
        self._layout()

    def set_caption(self, text: str) -> None:
        """Show other grey text under the label, or none if it is empty."""
        self.caption = text
        dpg.configure_item(self.caption_tag, show=bool(text))
        self._layout()

    def _layout(self) -> None:
        """Place the texts, and then the controls, for the current width."""
        room = max(self.width - LEFT - RIGHT - self.controls_width - 10, 40)
        first = PRIMARY_Y if self.caption else single_line_y(self.height)
        dpg.set_value(self.label_tag, fit(self.label, room))
        dpg.set_item_pos(self.label_tag, (LEFT, first - TEXT_LIFT))
        dpg.set_value(self.caption_tag, fit(self.caption, room))
        dpg.set_item_pos(self.caption_tag, (LEFT, SECONDARY_Y - TEXT_LIFT))
        self._place_controls()

    def _place_controls(self) -> None:
        """Place the controls at the right. The subclass does this."""
