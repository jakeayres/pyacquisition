import dearpygui.dearpygui as dpg

from .control_card import CONTROL_HEIGHT, ControlCard
from .measurement_card import HEIGHT, RIGHT
from .styles import primary_button_theme

KINDS = ("float", "int", "text")
INPUT_WIDTH = 96
BUTTON_WIDTH = 56
GAP = 6  # between the input and the button


class InputCard(ControlCard):
    """
    A card with a label, an input and a submit button, drawn like a measurement card:
    a tinted strip, with the label in white and, under it, a caption in grey if there
    is one. It has no bar at its left, which sets it apart from a measurement. At the
    right are the input and the button that sends what was typed in it.

    It is generic: what it is for, and what happens when the button is pressed, are
    up to whoever makes it. The button is pressed with a click, and the input is read
    at that moment, so what was typed is never lost to a refresh.

    The input can be updated from outside with `set_value`, for example with what a
    server says the value is. That does not overwrite what is being typed, or what has
    been typed and not yet sent.
    """

    def __init__(
        self,
        parent,
        width: int,
        label: str,
        value=0.0,
        kind: str = "float",
        on_submit=None,
        on_change=None,
        caption: str = "",
        button_label: str | None = "Set",
        background=None,
        minimum=None,
        maximum=None,
        format: str = "%g",
        height: int = HEIGHT,
        input_width: int = INPUT_WIDTH,
        button_width: int = BUTTON_WIDTH,
    ) -> None:
        """
        Args:
            parent: The item to put the card in.
            width (int): The width of the card in pixels.
            label (str): What the input is, such as `Measurement Period`.
            value: What the input starts with.
            kind (str): What can be typed: `float`, `int` or `text`.
            on_submit: Called with the value, when the button is pressed.
            on_change: Called with the value, each time something is typed in the input.
            caption (str): Small grey text under the label, such as `seconds`. The
                card has a single line if it is empty.
            button_label (str | None): What the button says. With `None` there is
                no button, and the input is wider: use `on_change` and `value`, which
                are there whether or not there is a button.
            background: The colour of the strip, or `None` for the header's own.
            minimum: The lowest a number can be. A lower one is raised to it.
            maximum: The highest a number can be. A higher one is lowered to it.
            format (str): How a `float` is shown, as for `printf`.
            height (int): The height of the card in pixels.
            input_width (int): The width of the input in pixels.
            button_width (int): The width of the button in pixels.

        Raises:
            ValueError: If the kind is not one of `KINDS`.
        """
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}, got {kind!r}")
        super().__init__(
            parent,
            width,
            label,
            caption=caption,
            background=background,
            height=height,
            controls_width=input_width
            + (GAP + button_width if button_label is not None else 0),
        )
        self.kind = kind
        self.on_submit = on_submit
        self.on_change = on_change
        self.input_width = input_width
        self.button_width = button_width
        self.minimum = minimum
        self.maximum = maximum
        self.dirty = False  # whether something has been typed that has not been sent

        self.input_tag = self._add_input(value, format)
        self.button_tag = None
        if button_label is not None:
            self.button_tag = dpg.add_button(
                label=button_label,
                width=button_width,
                height=CONTROL_HEIGHT,
                callback=self._submit,
                parent=self.container,
            )
            dpg.bind_item_theme(self.button_tag, primary_button_theme())
        self._layout()

    def _add_input(self, value, format: str):
        """The input that fits the kind, with no step buttons, and no `on_enter`."""
        options = dict(
            width=self.input_width,
            parent=self.container,
            callback=self._edited,
        )
        if self.kind == "float":
            return dpg.add_input_float(
                default_value=float(value), step=0, step_fast=0, format=format, **options
            )
        if self.kind == "int":
            return dpg.add_input_int(
                default_value=int(value), step=0, step_fast=0, **options
            )
        return dpg.add_input_text(default_value=str(value), **options)

    @property
    def value(self):
        """What is in the input now, kept between the minimum and the maximum."""
        value = dpg.get_value(self.input_tag)
        if self.kind == "text":
            return value
        if self.minimum is not None:
            value = max(value, self.minimum)
        if self.maximum is not None:
            value = min(value, self.maximum)
        return value

    def set_value(self, value, force: bool = False) -> None:
        """
        Show a value in the input, unless something is being typed in it, or has been
        typed and not sent. Then the value is left alone, so that a refresh from the
        server does not take away what was typed.

        Args:
            value: The value to show.
            force (bool): Show it whatever is in the input.
        """
        if not force and (self.dirty or dpg.is_item_active(self.input_tag)):
            return
        if self.kind == "float":
            value = float(value)
        elif self.kind == "int":
            value = int(value)
        else:
            value = str(value)
        dpg.set_value(self.input_tag, value)

    def _edited(self, sender=None, app_data=None, user_data=None) -> None:
        """Something was typed."""
        self.dirty = True
        if self.on_change:
            self.on_change(self.value)

    def _submit(self, sender=None, app_data=None, user_data=None) -> None:
        """The button was pressed: send what is in the input."""
        value = self.value
        dpg.set_value(self.input_tag, value)  # shows it if it was raised or lowered
        self.dirty = False
        if self.on_submit:
            self.on_submit(value)

    def _place_controls(self) -> None:
        """Place the input and the button at the right."""
        top = (self.height - CONTROL_HEIGHT) // 2
        right = self.width - RIGHT
        if self.button_tag is not None:
            dpg.set_item_pos(self.button_tag, (right - self.button_width, top))
            right -= self.button_width + GAP
        dpg.set_item_pos(self.input_tag, (right - self.input_width, top))
