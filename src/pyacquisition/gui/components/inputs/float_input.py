from .base_input import BaseInput
import dearpygui.dearpygui as dpg


class FloatInput(BaseInput):
    """
    Float input component.

    It is double precision, and shows up to six significant figures, so a value like
    `1e-9` is not shown, or sent, as zero.
    """

    def __init__(self, label: str, default_value: float = 0.0) -> None:
        super().__init__(label, default_value)

    def draw(self, parent: str | None = None, width: int = -1) -> None:
        """Draw the float input on the specified parent."""
        return dpg.add_input_double(
            **self._options(parent, width), step=0, format="%.6g"
        )
