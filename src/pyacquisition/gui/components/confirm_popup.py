import math

import dearpygui.dearpygui as dpg

from ...core.logging import logger
from ..constants import TEXT_COLOR

DANGER_BUTTON = {
    "normal": (150, 50, 50),
    "hovered": (190, 65, 65),
    "active": (215, 85, 85),
}


class ConfirmPopup:
    """
    A popup that asks for confirmation before something is done.

    It is modal, so nothing else in the interface can be used until it is answered.
    Nothing happens until **Confirm** is pressed. **Cancel**, or the Escape key,
    closes it without calling `on_confirm`.

    Use it in front of anything that is hard to undo:

        ConfirmPopup(
            title="Clear all tasks?",
            message="Every task waiting in the queue is removed.",
            on_confirm=lambda: clear_the_queue(),
            confirm_label="Clear",
            danger=True,
        ).show()

    or, more briefly, with `confirm(...)`.
    """

    WIDTH = 380

    def __init__(
        self,
        title: str,
        message: str,
        on_confirm,
        on_cancel=None,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        danger: bool = False,
    ) -> None:
        """
        Args:
            title (str): The title of the popup.
            message (str): What is about to happen, and what it will do.
            on_confirm: Called with no arguments when the action is confirmed.
            on_cancel: Called with no arguments when it is cancelled. Optional.
            confirm_label (str): The text of the button that confirms.
            cancel_label (str): The text of the button that cancels.
            danger (bool): Show the confirm button in red, for actions that cannot
                be undone.
        """
        self.title = title
        self.message = message
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.confirm_label = confirm_label
        self.cancel_label = cancel_label
        self.danger = danger

        self.tag = dpg.generate_uuid()
        self.confirm_tag = None
        self.cancel_tag = None
        self._keys = None

    @property
    def is_open(self) -> bool:
        """Whether the popup is showing."""
        return dpg.does_item_exist(self.tag)

    def show(self) -> "ConfirmPopup":
        """
        Show the popup, in the middle of the window. Does nothing if it is already
        showing.

        Returns:
            ConfirmPopup: The popup.
        """
        if self.is_open:
            return self

        # Enough lines for the message at the width of the text.
        lines = sum(
            max(1, math.ceil(len(line) / 46)) for line in self.message.split("\n")
        )
        height = 110 + 17 * lines
        x = (dpg.get_viewport_client_width() - self.WIDTH) // 2
        y = (dpg.get_viewport_client_height() - height) // 3

        with dpg.window(
            label=self.title,
            modal=True,
            no_close=True,
            no_resize=True,
            no_collapse=True,
            width=self.WIDTH,
            height=height,
            pos=[max(x, 0), max(y, 0)],
            tag=self.tag,
        ):
            dpg.add_text(self.message, wrap=self.WIDTH - 40, color=TEXT_COLOR)
            dpg.add_spacer(height=10)
            with dpg.group(horizontal=True, indent=(self.WIDTH - 240) // 2):
                self.confirm_tag = dpg.add_button(
                    label=self.confirm_label, width=110, callback=self._confirm
                )
                self.cancel_tag = dpg.add_button(
                    label=self.cancel_label, width=110, callback=self._cancel
                )

        if self.danger:
            self._make_danger(self.confirm_tag)

        with dpg.handler_registry() as self._keys:
            dpg.add_key_press_handler(dpg.mvKey_Escape, callback=self._cancel)
        return self

    def _make_danger(self, button) -> None:
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvButton):
                for column, colour in (
                    (dpg.mvThemeCol_Button, DANGER_BUTTON["normal"]),
                    (dpg.mvThemeCol_ButtonHovered, DANGER_BUTTON["hovered"]),
                    (dpg.mvThemeCol_ButtonActive, DANGER_BUTTON["active"]),
                ):
                    dpg.add_theme_color(column, colour, category=dpg.mvThemeCat_Core)
        dpg.bind_item_theme(button, theme)

    def close(self) -> None:
        """Close the popup without doing anything."""
        if self._keys is not None and dpg.does_item_exist(self._keys):
            dpg.delete_item(self._keys)
        self._keys = None
        if self.is_open:
            dpg.delete_item(self.tag)

    def _finish(self, callback) -> None:
        """Close the popup, and then call the callback, once."""
        if not self.is_open:
            return  # already answered
        self.close()  # first, so that a failing callback cannot leave it open
        if callback is None:
            return
        try:
            callback()
        except Exception as e:
            logger.error(f"[GUI] Error after confirming '{self.title}': {e}")

    def _confirm(self, sender=None, app_data=None, user_data=None) -> None:
        self._finish(self.on_confirm)

    def _cancel(self, sender=None, app_data=None, user_data=None) -> None:
        self._finish(self.on_cancel)


def confirm(title: str, message: str, on_confirm, **options) -> ConfirmPopup:
    """
    Ask for confirmation before something is done, and do it only if it is given.

    Args:
        title (str): The title of the popup.
        message (str): What is about to happen.
        on_confirm: Called with no arguments if the action is confirmed.
        **options: `on_cancel`, `confirm_label`, `cancel_label` and `danger`. See
            `ConfirmPopup`.

    Returns:
        ConfirmPopup: The popup that is showing.

    Example:
        confirm("Abort the sweep?", "It stops at its next step.", stop, danger=True)
    """
    return ConfirmPopup(title, message, on_confirm, **options).show()
